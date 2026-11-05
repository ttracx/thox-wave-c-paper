"""Sync the facts card from its upstream owner, and detect drift.

The card is owned by ``ttracx/thox-system-prompts``. This repo vendors a
byte-identical copy so the factory can build offline and so a training run is
reproducible against a pinned card version — but vendoring without a drift
check is just a fork with extra steps. :func:`check_drift` compares the local
bytes against upstream and fails CI when they diverge, which is what keeps
"vendored copy" from quietly becoming "second source of truth".

Auth: a token is read from ``GITHUB_TOKEN`` or ``GH_TOKEN`` when present, for
the case where the upstream repo is private. Nothing is ever written to disk.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import FactsDriftError, FactsLoadError
from .loader import (
    CARD_DOC_PATH,
    CARD_PATH,
    DATA_DIR,
    SOURCE_PATH,
    UPSTREAM_PATH,
    UPSTREAM_REPO,
    Provenance,
    load_provenance,
)

DEFAULT_REF = "main"
#: The card doc that ships alongside the JSON, synced for human readers.
UPSTREAM_DOC_PATH = "docs/THOX_FACTS.md"

_API = "https://api.github.com"
_RAW = "https://raw.githubusercontent.com"


def default_ref() -> str:
    """The ref to track, taken from provenance when the card is pinned.

    The card currently lives on an unmerged upstream branch, so a hard-coded
    ``main`` would make every drift check fail. Provenance is the pin.
    """
    provenance = load_provenance()
    return provenance.ref if provenance and provenance.ref else DEFAULT_REF


def default_repo() -> str:
    provenance = load_provenance()
    return provenance.repo if provenance and provenance.repo else UPSTREAM_REPO


@dataclass(frozen=True)
class SyncResult:
    changed: bool
    provenance: Provenance
    message: str


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github.raw",
        "User-Agent": "thoxllm-factory-facts-sync",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch(url: str, *, timeout: int = 30) -> bytes:
    request = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:200].decode("utf-8", "replace")
        raise FactsLoadError(f"HTTP {exc.code} fetching {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise FactsLoadError(f"cannot reach {url}: {exc.reason}") from exc


def fetch_upstream(repo: str = UPSTREAM_REPO, ref: str = DEFAULT_REF, path: str = UPSTREAM_PATH) -> bytes:
    """Fetch the raw card bytes from upstream."""
    return _fetch(f"{_RAW}/{repo}/{ref}/{path}")


def resolve_commit(repo: str = UPSTREAM_REPO, ref: str = DEFAULT_REF) -> str:
    """Resolve a ref to a commit SHA so provenance pins an exact version."""
    try:
        raw = _fetch(f"{_API}/repos/{repo}/commits/{ref}")
        data = json.loads(raw.decode("utf-8"))
    except (FactsLoadError, json.JSONDecodeError, UnicodeDecodeError):
        # Provenance degrades to the ref alone rather than failing the sync.
        return ""
    sha = data.get("sha") if isinstance(data, dict) else None
    return str(sha) if isinstance(sha, str) else ""


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


#: Generated on every sync, so it is never carried forward.
_GENERATED_NOTE_KEYS = frozenset({"_comment"})


def _preserved_notes() -> dict[str, Any]:
    """Underscore-prefixed notes a human wrote into SOURCE.json.

    Everything else in that file is regenerated from the sync, so without this
    a routine `sync_facts.py` run would quietly drop standing instructions.
    """
    if not SOURCE_PATH.is_file():
        return {}
    try:
        existing = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(existing, dict):
        return {}
    return {
        key: value
        for key, value in existing.items()
        if key.startswith("_") and key not in _GENERATED_NOTE_KEYS
    }


def sync(
    *,
    repo: str = UPSTREAM_REPO,
    ref: str = DEFAULT_REF,
    path: str = UPSTREAM_PATH,
    from_path: Path | None = None,
    doc: bool = True,
) -> SyncResult:
    """Vendor the upstream card into ``facts/data/``.

    Args:
        from_path: read from a local checkout instead of the network. Used by
            offline builds and by the runner on ``thox-build-01``, which has no
            outbound access.
    """
    if from_path is not None:
        try:
            payload = from_path.read_bytes()
        except OSError as exc:
            raise FactsLoadError(f"cannot read local card {from_path}: {exc}") from exc
        commit = ""
        origin = str(from_path)
    else:
        payload = fetch_upstream(repo, ref, path)
        commit = resolve_commit(repo, ref)
        origin = f"{repo}@{ref}:{path}"

    try:
        parsed = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FactsLoadError(f"upstream card at {origin} is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict) or "verified" not in parsed:
        raise FactsLoadError(f"upstream card at {origin} does not look like a facts card")

    digest = hashlib.sha256(payload).hexdigest()
    previous = load_provenance()
    changed = previous is None or previous.sha256 != digest

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CARD_PATH.write_bytes(payload)

    if doc and from_path is None:
        try:
            CARD_DOC_PATH.write_bytes(_fetch(f"{_RAW}/{repo}/{ref}/{UPSTREAM_DOC_PATH}"))
        except FactsLoadError:
            # The human-readable doc is a convenience; the JSON is the contract.
            pass

    provenance = Provenance(
        repo=repo,
        ref=ref,
        commit=commit,
        path=path,
        sha256=digest,
        synced_at=_now(),
    )
    document: dict[str, Any] = {
        "_comment": (
            "Provenance for the vendored THOX facts card. The card is OWNED by "
            f"{repo} at {path} — edit it there, then re-run "
            "`python scripts/sync_facts.py`. Never edit facts/data/thox_facts.json "
            "in this repo."
        )
    }
    # Carry forward human-authored underscore notes. A sync must not silently
    # delete standing instructions — the note recording that `ref` is pinned to
    # an unmerged branch is exactly the thing someone needs to read next.
    document.update(_preserved_notes())
    document.update(
        {
            "repo": provenance.repo,
            "ref": provenance.ref,
            "commit": provenance.commit,
            "path": provenance.path,
            "sha256": provenance.sha256,
            "synced_at": provenance.synced_at,
            "card_version": str(parsed.get("version", "")),
        }
    )
    SOURCE_PATH.write_text(
        # ensure_ascii=False: the comment contains an em-dash, and escaping it
        # to — makes the file harder to read for no benefit.
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return SyncResult(
        changed=changed,
        provenance=provenance,
        message=(
            f"synced card {parsed.get('version', '?')} from {origin} "
            f"({'updated' if changed else 'unchanged'}, sha256={digest[:12]})"
        ),
    )


def check_integrity() -> Provenance:
    """Offline: verify the vendored card matches its recorded provenance.

    This is the guard that belongs in PR CI. It needs no network and no
    cross-repo auth: it recomputes the sha256 of the vendored card and compares
    it to the hash `scripts/sync_facts.py` recorded in SOURCE.json at sync time.
    The one thing it catches is the one thing CI must catch — someone editing
    the vendored copy by hand instead of upstream — because a hand-edit changes
    the bytes without updating the recorded hash.

    The upstream comparison (`check_drift`) is a strictly stronger check, but it
    depends on fetching an upstream repo that may be private or on an unmerged
    branch, so it cannot gate every PR. Integrity here + drift on a schedule is
    the split.

    Raises:
        FactsDriftError: no vendored card, no provenance, or a hash mismatch.
    """
    if not CARD_PATH.is_file():
        raise FactsDriftError(
            f"no vendored facts card at {CARD_PATH}; run `python scripts/sync_facts.py`"
        )
    provenance = load_provenance()
    if provenance is None:
        raise FactsDriftError(
            f"no provenance at {SOURCE_PATH}; the vendored card is untracked. "
            "Run `python scripts/sync_facts.py`."
        )
    if not provenance.sha256:
        raise FactsDriftError(
            f"provenance at {SOURCE_PATH} records no sha256; re-run "
            "`python scripts/sync_facts.py` to pin the vendored card."
        )
    actual = hashlib.sha256(CARD_PATH.read_bytes()).hexdigest()
    if actual != provenance.sha256:
        raise FactsDriftError(
            f"vendored facts card does not match its recorded provenance\n"
            f"  card     sha256 {actual}\n"
            f"  SOURCE   sha256 {provenance.sha256}\n"
            "The vendored copy was edited by hand. The card is owned upstream at "
            f"{provenance.repo}:{provenance.path} — land the change there and re-run "
            "`python scripts/sync_facts.py`, or `git checkout facts/data/` to discard it."
        )
    return provenance


def check_drift(
    *,
    repo: str = UPSTREAM_REPO,
    ref: str = DEFAULT_REF,
    path: str = UPSTREAM_PATH,
    from_path: Path | None = None,
) -> None:
    """Raise if the vendored card differs from upstream.

    Needs network access to ``repo`` (and cross-repo auth when it is private),
    so this is for scheduled or manual runs, not per-PR gating. Use
    :func:`check_integrity` in CI.

    Raises:
        FactsDriftError: the vendored copy has diverged, or was never synced.
        FactsLoadError:  upstream could not be reached (network, 404, or auth).
    """
    if not CARD_PATH.is_file():
        raise FactsDriftError(
            f"no vendored facts card at {CARD_PATH}; run `python scripts/sync_facts.py`"
        )
    local = hashlib.sha256(CARD_PATH.read_bytes()).hexdigest()

    if from_path is not None:
        upstream = hashlib.sha256(from_path.read_bytes()).hexdigest()
        origin = str(from_path)
    else:
        upstream = hashlib.sha256(fetch_upstream(repo, ref, path)).hexdigest()
        origin = f"{repo}@{ref}:{path}"

    if local != upstream:
        raise FactsDriftError(
            f"vendored facts card has drifted from {origin}\n"
            f"  local    sha256 {local}\n"
            f"  upstream sha256 {upstream}\n"
            "The card is owned upstream. If the change belongs upstream, land it there "
            "and re-run `python scripts/sync_facts.py`. Do not edit the vendored copy."
        )
