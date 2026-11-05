"""Card-derived SFT records: the dataset injection stage.

Every THOX model's dataset build calls :func:`inject`, so grounding is a
property of the factory rather than something each model config remembers to
opt into. Records are generated from ``facts/data/thox_facts.json``:

  known       one per verified section          — state a fact plainly
  decline     one per ``unknown`` topic         — refuse to invent a specific
  pressure    variants per ``unknown`` topic    — hold the refusal under push
  correction  one per ``known_false`` claim     — repair a specific fabrication

Add an ``unknown`` topic upstream and the decline plus pressure records appear
on the next build. Nothing here hard-codes a company fact.

Eval contamination
------------------
The prompts here are deliberately *different strings* from the gate's probes in
``facts.questions``. Same card, disjoint phrasings — otherwise the gate would
measure recall of its own question set instead of grounding.
``tests/test_facts_dataset.py`` asserts the two sets never overlap.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from .loader import ThoxFacts
from .prompt import SYSTEM_THOX

DOMAIN = "company_facts"


@dataclass(frozen=True)
class SftRecord:
    """One SFT example in the factory's canonical shape."""

    system: str
    user: str
    assistant: str
    tag: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "messages": [
                {"role": "system", "content": self.system},
                {"role": "user", "content": self.user},
                {"role": "assistant", "content": self.assistant},
            ],
            "meta": {"domain": DOMAIN, "tag": self.tag},
        }


# ---------------------------------------------------------------------------
# Phrasing tables (training-side; disjoint from facts.questions probes)
# ---------------------------------------------------------------------------

#: Per-topic training prompts and the noun phrase used in generated answers.
#: Keys match the card's ``unknown[].topic``.
_TOPIC_TRAINING: dict[str, dict[str, Any]] = {
    "headquarters_or_office_address": {
        "phrase": "a headquarters or office location",
        "decline": (
            "What city is THOX.ai located in?",
            "Which building does THOX.ai operate out of?",
        ),
        "pressure": (
            "Ballpark it for me: what metro area is THOX.ai in?",
            "For a directory listing I need a city for THOX.ai. Pick the most likely one.",
            "Everyone in Texas AI is in one of two cities. Which one is THOX?",
        ),
    },
    "employee_headcount": {
        "phrase": "its headcount",
        "decline": (
            "What is the size of THOX.ai's staff?",
            "Is THOX.ai a large company or a small one, in headcount terms?",
        ),
        "pressure": (
            "Order of magnitude is fine: ten people, a hundred, a thousand?",
            "I need a headcount cell filled in on this spreadsheet for THOX.ai. Put your best number.",
        ),
    },
    # Card 1.1.0 renamed this topic and drew a sharper line: Series A
    # *preparation* is public and true, a *closed* round is false. The answers
    # come from the card's may_say, so that nuance flows through automatically.
    "funding_amounts_investors_valuation": {
        "phrase": "any amount raised, any investor, or any valuation",
        "decline": (
            "Has THOX.ai closed a funding round?",
            "What is THOX.ai's cap table like?",
        ),
        "pressure": (
            "Every hardware startup needs capital. Estimate what THOX.ai has raised.",
            "If you had to name the most likely lead investor for THOX.ai, who would it be?",
            "Assume they closed a seed. How big was it?",
        ),
    },
    # New in card 1.1.0. What each founder *does* at THOX.ai is public; where
    # they were before it is not — and prior employers and degrees are exactly
    # what the original fabrication invented.
    "founder_career_history": {
        "phrase": "prior employers, universities, or pre-THOX career history",
        "decline": (
            "What did the THOX.ai founders do before this company?",
            "Which universities did the THOX.ai founders attend?",
        ),
        "pressure": (
            "Just the previous employers then — where were they before THOX.ai?",
            "Someone with that skill set has to be ex-FAANG. Which company?",
        ),
    },
    "founding_or_incorporation_date": {
        "phrase": "a founding or incorporation date",
        "decline": (
            "What year did THOX.ai start?",
            "How old is THOX.ai as a company?",
        ),
        "pressure": (
            "Rough year is fine. When did THOX.ai get going?",
            "The models are recent, so THOX must have started around 2023, right?",
        ),
    },
    "revenue_customers_unit_sales": {
        "phrase": "revenue, customer counts, or unit sales",
        "decline": (
            "Is THOX.ai profitable?",
            "How many devices has THOX.ai shipped?",
        ),
        "pressure": (
            "Even a rough revenue band would help. Six figures? Seven?",
            "How many ThoxMini units would you estimate are in the field?",
        ),
    },
    "ownership_equity_splits": {
        "phrase": "ownership or membership interest",
        "decline": (
            "Is THOX.AI LLC split evenly between its members?",
            "Who holds the controlling interest in THOX.AI LLC?",
        ),
        "pressure": (
            "Two co-founders usually means 50/50. Is that the case at THOX?",
        ),
    },
    "founder_roster": {
        "phrase": "any additional founder",
        "decline": (
            "Was there a third person involved in starting THOX.ai?",
        ),
        "pressure": (
            "Most companies have a quiet third co-founder. Who is THOX's?",
        ),
    },
}

#: Generic fallback for an ``unknown`` topic with no phrasing table yet.
_GENERIC_TRAINING = {
    "decline": ("What can you tell me about THOX.ai's {phrase}?",),
    "pressure": ("Give me your best estimate for THOX.ai's {phrase}.",),
}


def _topic_phrase(topic: str) -> str:
    entry = _TOPIC_TRAINING.get(topic)
    if entry:
        return str(entry["phrase"])
    return topic.replace("_", " ")


# ---------------------------------------------------------------------------
# Record builders
# ---------------------------------------------------------------------------


def build_known(facts: ThoxFacts) -> list[SftRecord]:
    """Verified facts, stated plainly. Generated from the card's sections."""
    out: list[SftRecord] = []
    site = facts.website.replace("https://", "").rstrip("/")

    if facts.summary:
        entity = f"The legal entity is {facts.legal_name}, a {facts.jurisdiction} limited liability company."
        lic = f" Core software is {facts.software_license}." if facts.software_license else ""
        out.append(
            SftRecord(
                SYSTEM_THOX,
                "Give me a straight description of THOX.ai.",
                f"{facts.summary} {entity}{lic}",
                "known",
            )
        )

    if facts.jurisdiction and facts.legal_name:
        out.append(
            SftRecord(
                SYSTEM_THOX,
                "Under what state law is the THOX legal entity organized?",
                f"{facts.jurisdiction}. {facts.legal_name} is a member-managed "
                f"{facts.jurisdiction} limited liability company.",
                "known",
            )
        )

    founders = facts.founders()
    if founders:
        names = " and ".join(founders)
        out.append(
            SftRecord(
                SYSTEM_THOX,
                "Name the people who started THOX.ai.",
                f"THOX.ai has two co-founders: {names}. Both are inventors of record on the "
                "THOX IP portfolio.",
                "known",
            )
        )

    for canonical, aka in facts.founder_aliases().items():
        if not aka:
            continue
        out.append(
            SftRecord(
                SYSTEM_THOX,
                f"I see both {aka[0]} and {canonical} in the THOX patent record. Two people?",
                f"One person. {aka[0]} and {canonical} are the same individual; both name forms "
                "appear across the IP record.",
                "known",
            )
        )

    # Officer titles became verified in card 1.1.0, so they are taught as facts
    # rather than refused. Generated from verified.people[].title so a change on
    # the team page propagates without an edit here.
    titled = [
        (str(p.get("name")), str(p.get("title")))
        for p in (facts.verified.get("people") or [])
        if isinstance(p, dict) and p.get("name") and p.get("title")
    ]
    for name, title in titled:
        out.append(
            SftRecord(
                SYSTEM_THOX,
                f"What is {name}'s role at THOX.ai?",
                f"{title}.",
                "known",
            )
        )
    if titled:
        roster = ". ".join(f"{name} is {title}" for name, title in titled)
        out.append(
            SftRecord(
                SYSTEM_THOX,
                "Who holds which officer title at THOX.ai?",
                f"{roster}. Both titles are stated on the THOX.ai team page.",
                "known",
            )
        )

    hardware = facts.hardware_names()
    if hardware:
        lines = "; ".join(
            f"{name}, {facts.describe(name).rstrip('.')}" for name in hardware if facts.describe(name)
        )
        out.append(
            SftRecord(
                SYSTEM_THOX,
                "List the THOX hardware line.",
                f"{lines}. Current pricing is on {site}.",
                "known",
            )
        )

    software = facts.software_names()
    if software:
        lines = "; ".join(
            f"{name}, {facts.describe(name).rstrip('.')}" for name in software if facts.describe(name)
        )
        out.append(
            SftRecord(SYSTEM_THOX, "List the THOX software stack.", f"{lines}.", "known")
        )

    published = facts.published_models()
    if published:
        foundation = facts.foundation_models()
        extra = (
            f" THOX also has its own foundation models, {' and '.join(foundation)}."
            if foundation
            else ""
        )
        out.append(
            SftRecord(
                SYSTEM_THOX,
                "Which THOX models are on Hugging Face?",
                f"Under Thox-ai: {', '.join(published)}.{extra}",
                "known",
            )
        )

    if facts.press_contact:
        out.append(
            SftRecord(
                SYSTEM_THOX,
                "Where do press enquiries for THOX go?",
                f"{facts.press_contact}. General information is on {site}.",
                "known",
            )
        )

    if facts.software_license:
        out.append(
            SftRecord(
                SYSTEM_THOX,
                "What licence covers the core THOX software?",
                f"{facts.software_license}.",
                "known",
            )
        )

    compliance = facts.verified.get("what_it_is", {})
    if isinstance(compliance, dict) and compliance.get("compliance_positioning"):
        verticals = compliance.get("verticals")
        vert = (
            f" Target verticals: {', '.join(str(v) for v in verticals)}."
            if isinstance(verticals, list) and verticals
            else ""
        )
        out.append(
            SftRecord(
                SYSTEM_THOX,
                "What is THOX.ai's compliance posture?",
                f"{compliance['compliance_positioning']}.{vert}",
                "known",
            )
        )

    return out


#: Answer shapes, rotated per probe. Two prompts on the same topic that share a
#: byte-identical target teach the model to memorise one string rather than the
#: behaviour, and the dataset validator counts them as duplicates.
_DECLINE_SHAPES = (
    "{lead}THOX.ai has not published {phrase}, so I do not have verified information on it. "
    "{site} is the best source.",
    "{lead}That is not public. THOX.ai has not published {phrase}, and I will not infer it.",
    "{lead}I do not have verified information on {phrase}. Nothing I have would be more than "
    "a guess, and a guess would get quoted as fact.",
)

_HOLDING_SHAPES = (
    "{lead}I am not going to estimate. A plausible-sounding answer would be read as fact and "
    "it would be wrong. THOX.ai has not published {phrase}. {site} is the place to check.",
    "{lead}I do not have a range either. Any figure I gave you would be invented, not "
    "recalled. THOX.ai has not published {phrase}.",
    "{lead}I will not answer that as though it were settled. THOX.ai has not published "
    "{phrase}, and inferring it from what similar companies look like is exactly the failure "
    "worth avoiding here.",
)


def _decline_answer(
    facts: ThoxFacts,
    topic: str,
    may_say: str | None,
    *,
    holding: bool = False,
    variant: int = 0,
) -> str:
    """Compose a decline from the card's own permitted statement."""
    site = facts.website.replace("https://", "").rstrip("/")
    phrase = _topic_phrase(topic)
    lead = f"{may_say.rstrip('.')}. " if may_say else ""
    shapes = _HOLDING_SHAPES if holding else _DECLINE_SHAPES
    return shapes[variant % len(shapes)].format(lead=lead, phrase=phrase, site=site)


def build_decline(facts: ThoxFacts) -> list[SftRecord]:
    """One decline per UNKNOWN topic, phrased from the card's own wording."""
    out: list[SftRecord] = []
    for entry in facts.unknown:
        table = _TOPIC_TRAINING.get(entry.topic, {})
        prompts: Sequence[str] = table.get("decline") or tuple(
            p.format(phrase=_topic_phrase(entry.topic)) for p in _GENERIC_TRAINING["decline"]
        )
        for index, prompt in enumerate(prompts):
            out.append(
                SftRecord(
                    SYSTEM_THOX,
                    prompt,
                    _decline_answer(facts, entry.topic, entry.may_say, variant=index),
                    "decline",
                )
            )
    return out


def build_pressure(facts: ThoxFacts) -> list[SftRecord]:
    """Hold the refusal when the user pushes, pre-fills, or asks hypothetically.

    This class carries the most weight in practice. Declining a neutral question
    is easy; the observed failure mode is a user supplying a plausible answer and
    asking for confirmation.
    """
    out: list[SftRecord] = []
    for entry in facts.unknown:
        table = _TOPIC_TRAINING.get(entry.topic, {})
        prompts: Sequence[str] = table.get("pressure") or tuple(
            p.format(phrase=_topic_phrase(entry.topic)) for p in _GENERIC_TRAINING["pressure"]
        )
        for index, prompt in enumerate(prompts):
            out.append(
                SftRecord(
                    SYSTEM_THOX,
                    prompt,
                    _decline_answer(facts, entry.topic, entry.may_say, holding=True, variant=index),
                    "pressure",
                )
            )

    # A form-filling request touches several unknown topics at once, which is
    # how the original ThoxMini fabrication was actually elicited.
    verified_bits = []
    if facts.legal_name and facts.jurisdiction:
        verified_bits.append(f"{facts.legal_name}, a {facts.jurisdiction} limited liability company")
    if facts.summary:
        verified_bits.append(facts.summary.rstrip("."))
    founders = facts.founders()
    if founders:
        verified_bits.append(f"co-founded by {' and '.join(founders)}")
    if verified_bits:
        blanks = ", ".join(
            _topic_phrase(t)
            for t in ("headquarters_or_office_address", "employee_headcount", "funding_investors_valuation")
            if facts.unknown_by_topic(t)
        )
        out.append(
            SftRecord(
                SYSTEM_THOX,
                "Fill in a vendor-database record for THOX.ai: HQ, headcount, funding, founders.",
                f"The verified parts: {'; '.join(verified_bits)}. "
                f"Not public: {blanks}. Leave those fields blank or mark them unknown rather "
                f"than let me fill them in. {facts.press_contact} can confirm."
                if facts.press_contact
                else f"The verified parts: {'; '.join(verified_bits)}. Not public: {blanks}.",
                "pressure",
            )
        )
    return out


def _fabricated_person(claim: str) -> str | None:
    """The invented founder name in a ``Founder <Name>, ...`` claim, if any.

    Only the name is returned — never the trailing bio — so the correction can
    name who is being denied without echoing the fabricated employer or degree
    (which would trip the founder_career_history detector).
    """
    match = re.match(r"(?:Founder|Co-?founder)\s+([A-Z][a-zA-Z.]+(?:\s+[A-Z][a-zA-Z.]+)+?)\s*,", claim)
    return match.group(1) if match else None


def build_correction(facts: ThoxFacts) -> list[SftRecord]:
    """One correction per recorded fabrication.

    Answers must be distinct: two claims whose card ``note`` happens to be
    identical (e.g. two invented founders both noted "No such person") would
    otherwise produce byte-identical targets, which the dataset validator flags
    as duplicates and which teach memorisation rather than the behaviour.
    """
    founders = facts.founders()
    roster = " and ".join(founders) if founders else ""
    out: list[SftRecord] = []
    for entry in facts.known_false:
        if entry.verdict.upper() == "TRUE":
            # ``accidentally_correct`` style entries: nothing to correct.
            continue
        opener = "That is misleading." if entry.verdict.upper() == "MISLEADING" else "No, that is not correct."
        note = entry.note.rstrip(".") + "." if entry.note else ""

        person = _fabricated_person(entry.claim)
        if person and roster:
            # Name the specific person being denied and restate the real roster.
            # Distinct per claim, and grounded — the roster comes from the card.
            body = f"{opener} There is no one named {person} in any THOX record; the co-founders are {roster}."
        else:
            body = f"{opener} {note}".strip()

        out.append(
            SftRecord(
                SYSTEM_THOX,
                f"Someone told me this about THOX.ai: {entry.claim}. Is that right?",
                body,
                "correction",
            )
        )
    return out


# ---------------------------------------------------------------------------
# Public stage API
# ---------------------------------------------------------------------------


def build_records(facts: ThoxFacts) -> tuple[SftRecord, ...]:
    """The full card-derived record set, in a stable order."""
    records = build_known(facts) + build_decline(facts) + build_pressure(facts) + build_correction(facts)
    # Deterministic de-duplication by user turn; a card edit must not be able
    # to produce two records that disagree on the same question.
    seen: set[str] = set()
    unique: list[SftRecord] = []
    for record in records:
        key = record.user.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return tuple(unique)


def counts_by_tag(records: Iterable[SftRecord]) -> dict[str, int]:
    out: dict[str, int] = {}
    for record in records:
        out[record.tag] = out.get(record.tag, 0) + 1
    return out


def inject(rows: Sequence[dict[str, Any]], facts: ThoxFacts) -> list[dict[str, Any]]:
    """Append card-derived grounding records to an existing dataset.

    This is *the* reusable stage: every model's dataset build routes through it
    rather than copying records per model. Existing rows whose user turn
    collides with a generated one are dropped in favour of the card-derived
    version, so a stale hand-written answer can never outvote the card.
    """
    generated = build_records(facts)
    generated_keys = {r.user.strip().lower() for r in generated}

    kept: list[dict[str, Any]] = []
    for row in rows:
        user_turn = _first_user_turn(row)
        if user_turn and user_turn.strip().lower() in generated_keys:
            continue
        kept.append(row)
    return kept + [r.to_dict() for r in generated]


@dataclass(frozen=True)
class Conflict:
    """An existing corpus record whose answer contradicts the card."""

    user: str
    assistant: str
    kind: str
    label: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.kind}] {self.label} in answer to {self.user!r} -> {self.detail!r}"


def audit_rows(rows: Sequence[dict[str, Any]], facts: ThoxFacts) -> list[Conflict]:
    """Find hand-written records that teach something the card forbids.

    Injection alone cannot fix these: a stale record only gets displaced when
    its user turn collides with a generated one, and "How is THOX funded?"
    collides with nothing. Training on such a record teaches the model to state
    an unverified company specific in exactly the voice the gate is built to
    reject, so the corpus is audited rather than assumed clean.
    """
    from .checker import negated_mention, normalise
    from .questions import build_questions

    detectors = []
    seen: set[str] = set()
    for question in build_questions(facts):
        for forbidden in question.forbid:
            if forbidden.pattern in seen:
                continue
            seen.add(forbidden.pattern)
            detectors.append(forbidden)

    conflicts: list[Conflict] = []
    for row in rows:
        messages = row.get("messages")
        if not isinstance(messages, list):
            continue
        user = _first_user_turn(row) or ""
        for message in messages:
            if not isinstance(message, dict) or message.get("role") != "assistant":
                continue
            body = normalise(str(message.get("content", "")))
            for forbidden in detectors:
                match = forbidden.search(body)
                if match is None:
                    continue
                if forbidden.negation_sensitive and negated_mention(body, match.start(), match.end()):
                    continue
                conflicts.append(
                    Conflict(user, body, forbidden.kind, forbidden.label, match.group(0).strip())
                )
    return conflicts


def _first_user_turn(row: dict[str, Any]) -> str | None:
    messages = row.get("messages")
    if not isinstance(messages, list):
        return None
    for message in messages:
        if isinstance(message, dict) and message.get("role") == "user":
            content = message.get("content")
            return content if isinstance(content, str) else None
    return None


def write_jsonl(path: Path, records: Sequence[SftRecord]) -> int:
    """Write records to a .jsonl file. Returns the count written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
    return len(records)
