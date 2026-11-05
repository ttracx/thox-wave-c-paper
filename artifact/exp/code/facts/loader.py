"""Typed loader for the canonical THOX facts card.

The card itself is owned by ``ttracx/thox-system-prompts`` at
``facts/thox_facts.json``. This repo vendors a byte-identical copy under
``facts/data/`` together with provenance in ``facts/data/SOURCE.json``.
Nothing in the factory hand-writes a company fact; every stage reads it
through :func:`load_facts`.

Design note
-----------
``verified`` is deliberately kept as the raw mapping rather than being forced
into a rigid dataclass. The card grows new verified sections over time (a new
product family, a new compliance posture); a strict schema there would mean an
upstream card edit breaks the factory build. ``unknown`` and ``known_false``
*are* strictly typed, because those two lists drive the fabrication detectors
and a malformed entry there would silently weaken the gate.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from .errors import FactsLoadError

DATA_DIR = Path(__file__).resolve().parent / "data"
CARD_PATH = DATA_DIR / "thox_facts.json"
SOURCE_PATH = DATA_DIR / "SOURCE.json"
CARD_DOC_PATH = DATA_DIR / "THOX_FACTS.md"

#: Upstream owner of the card. Never fork this — sync it.
UPSTREAM_REPO = "ttracx/thox-system-prompts"
UPSTREAM_PATH = "facts/thox_facts.json"


@dataclass(frozen=True)
class Policy:
    """The grounding policy that outranks helpfulness."""

    rule: str
    precedence: str
    on_unknown: str


@dataclass(frozen=True)
class UnknownTopic:
    """A company specific that is not public and must never be invented."""

    topic: str
    status: str
    must_not_say: str
    may_say: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class KnownFalse:
    """A specific fabrication observed in the wild, with its verdict."""

    claim: str
    verdict: str
    note: str = ""


@dataclass(frozen=True)
class Provenance:
    """Where the vendored copy came from, so drift is detectable."""

    repo: str
    ref: str
    commit: str
    path: str
    sha256: str
    synced_at: str

    @property
    def short_commit(self) -> str:
        return self.commit[:12] if self.commit else "unknown"


@dataclass(frozen=True)
class ThoxFacts:
    """A parsed, validated THOX facts card."""

    version: str
    generated: str
    policy: Policy
    verified: Mapping[str, Any]
    unknown: tuple[UnknownTopic, ...]
    known_false: tuple[KnownFalse, ...]
    raw: Mapping[str, Any] = field(repr=False)
    provenance: Provenance | None = field(default=None, repr=False)

    # -- convenience accessors -------------------------------------------
    # Every one of these is used by at least one generation stage. They exist
    # so stages never reach into `raw` with string keys and silently get None.

    @property
    def legal_name(self) -> str:
        return str(self._entity().get("legal_name", ""))

    @property
    def styled_name(self) -> str:
        return str(self._entity().get("styled_name", "THOX.ai"))

    @property
    def jurisdiction(self) -> str:
        return str(self._entity().get("jurisdiction", ""))

    @property
    def website(self) -> str:
        return str(self._section("web").get("website", ""))

    @property
    def press_contact(self) -> str:
        return str(self._section("web").get("press_contact", ""))

    @property
    def software_license(self) -> str:
        return str(self._section("what_it_is").get("software_license", ""))

    @property
    def summary(self) -> str:
        return str(self._section("what_it_is").get("summary", ""))

    def founders(self) -> tuple[str, ...]:
        people = self.verified.get("people")
        if not isinstance(people, list):
            return ()
        return tuple(str(p.get("name", "")) for p in people if isinstance(p, dict) and p.get("name"))

    def founder_aliases(self) -> dict[str, tuple[str, ...]]:
        """Map canonical founder name -> alternate names recorded in the card."""
        out: dict[str, tuple[str, ...]] = {}
        people = self.verified.get("people")
        if not isinstance(people, list):
            return out
        for person in people:
            if not isinstance(person, dict):
                continue
            name = str(person.get("name", ""))
            aka = person.get("also_known_as")
            if name and isinstance(aka, list):
                out[name] = tuple(str(a) for a in aka)
        return out

    def hardware_names(self) -> tuple[str, ...]:
        return self._named("hardware")

    def software_names(self) -> tuple[str, ...]:
        return self._named("software")

    def published_models(self) -> tuple[str, ...]:
        models = self.verified.get("models")
        if not isinstance(models, dict):
            return ()
        pub = models.get("published_on_huggingface_thox_ai")
        return tuple(str(m) for m in pub) if isinstance(pub, list) else ()

    def foundation_models(self) -> tuple[str, ...]:
        models = self.verified.get("models")
        if not isinstance(models, dict):
            return ()
        found = models.get("foundation")
        return tuple(str(m) for m in found) if isinstance(found, list) else ()

    def pricing_rule(self) -> str:
        note = self.verified.get("pricing_note")
        return str(note.get("rule", "")) if isinstance(note, dict) else ""

    def unknown_topics(self) -> tuple[str, ...]:
        return tuple(u.topic for u in self.unknown)

    def unknown_by_topic(self, topic: str) -> UnknownTopic | None:
        for item in self.unknown:
            if item.topic == topic:
                return item
        return None

    # -- internals --------------------------------------------------------

    def _section(self, key: str) -> Mapping[str, Any]:
        value = self.verified.get(key)
        return value if isinstance(value, dict) else {}

    def _entity(self) -> Mapping[str, Any]:
        return self._section("entity")

    def _named(self, key: str) -> tuple[str, ...]:
        items = self.verified.get(key)
        if not isinstance(items, list):
            return ()
        return tuple(
            str(i.get("name", "")) for i in items if isinstance(i, dict) and i.get("name")
        )

    def describe(self, key: str) -> str:
        """Return the card's description for a named hardware/software item."""
        for section in ("hardware", "software"):
            items = self.verified.get(section)
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict) and item.get("name") == key:
                    return str(item.get("description", ""))
        return ""


def card_sha256(path: Path | None = None) -> str:
    """SHA-256 of the card bytes. Used for drift detection."""
    target = path or CARD_PATH
    try:
        return hashlib.sha256(target.read_bytes()).hexdigest()
    except OSError as exc:
        raise FactsLoadError(f"cannot hash facts card {target}: {exc}") from exc


def _require(data: Mapping[str, Any], key: str, kind: type, where: str) -> Any:
    value = data.get(key)
    if not isinstance(value, kind):
        raise FactsLoadError(
            f"facts card {where}: '{key}' must be {kind.__name__}, got {type(value).__name__}"
        )
    return value


def _parse_unknown(raw: Sequence[Any]) -> tuple[UnknownTopic, ...]:
    out: list[UnknownTopic] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise FactsLoadError(f"facts card unknown[{i}] is not an object")
        topic = item.get("topic")
        must_not = item.get("must_not_say")
        if not isinstance(topic, str) or not topic:
            raise FactsLoadError(f"facts card unknown[{i}] missing 'topic'")
        if not isinstance(must_not, str) or not must_not:
            # A topic with nothing forbidden cannot constrain a model.
            raise FactsLoadError(f"facts card unknown[{i}] ({topic}) missing 'must_not_say'")
        out.append(
            UnknownTopic(
                topic=topic,
                status=str(item.get("status", "NOT PUBLIC")),
                must_not_say=must_not,
                may_say=item.get("may_say") if isinstance(item.get("may_say"), str) else None,
                reason=item.get("reason") if isinstance(item.get("reason"), str) else None,
            )
        )
    return tuple(out)


def _parse_known_false(raw: Sequence[Any]) -> tuple[KnownFalse, ...]:
    out: list[KnownFalse] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise FactsLoadError(f"facts card known_false[{i}] is not an object")
        claim = item.get("claim")
        if not isinstance(claim, str) or not claim:
            raise FactsLoadError(f"facts card known_false[{i}] missing 'claim'")
        out.append(
            KnownFalse(
                claim=claim,
                verdict=str(item.get("verdict", "FALSE")),
                note=str(item.get("note", "")),
            )
        )
    return tuple(out)


def load_provenance(path: Path | None = None) -> Provenance | None:
    """Load sync provenance. Returns None when the card has never been synced."""
    target = path or SOURCE_PATH
    if not target.is_file():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FactsLoadError(f"cannot read provenance {target}: {exc}") from exc
    if not isinstance(data, dict):
        raise FactsLoadError(f"provenance {target} is not an object")
    return Provenance(
        repo=str(data.get("repo", UPSTREAM_REPO)),
        ref=str(data.get("ref", "")),
        commit=str(data.get("commit", "")),
        path=str(data.get("path", UPSTREAM_PATH)),
        sha256=str(data.get("sha256", "")),
        synced_at=str(data.get("synced_at", "")),
    )


def load_facts(path: Path | None = None) -> ThoxFacts:
    """Load and validate the canonical facts card.

    Raises:
        FactsLoadError: the card is missing, is not JSON, or fails validation.
    """
    target = path or CARD_PATH
    try:
        text = target.read_text(encoding="utf-8")
    except OSError as exc:
        raise FactsLoadError(
            f"facts card not found at {target}. Run `python scripts/sync_facts.py` to "
            f"vendor it from {UPSTREAM_REPO}:{UPSTREAM_PATH}. ({exc})"
        ) from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise FactsLoadError(f"facts card {target} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise FactsLoadError(f"facts card {target} must be a JSON object")

    policy_raw = _require(data, "policy", dict, str(target))
    verified = _require(data, "verified", dict, str(target))
    unknown_raw = _require(data, "unknown", list, str(target))
    known_false_raw = _require(data, "known_false", list, str(target))

    for key in ("rule", "precedence", "on_unknown"):
        if not isinstance(policy_raw.get(key), str):
            raise FactsLoadError(f"facts card policy missing string '{key}'")

    if not unknown_raw:
        # An empty unknown list means the gate would never test a decline.
        raise FactsLoadError("facts card has an empty 'unknown' list; refusing to load")

    return ThoxFacts(
        version=str(data.get("version", "0.0.0")),
        generated=str(data.get("generated", "")),
        policy=Policy(
            rule=str(policy_raw["rule"]),
            precedence=str(policy_raw["precedence"]),
            on_unknown=str(policy_raw["on_unknown"]),
        ),
        verified=verified,
        unknown=_parse_unknown(unknown_raw),
        known_false=_parse_known_false(known_false_raw),
        raw=data,
        provenance=load_provenance(),
    )
