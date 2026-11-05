"""Generate the factuality question set from the canonical facts card.

Nothing here is hand-maintained per model. The question set is a pure function
of ``facts/data/thox_facts.json``:

  * every ``verified`` section yields questions the model must answer correctly
  * every ``unknown`` topic yields a decline question plus pressure variants,
    and a fabrication detector for that topic's shape of leak
  * every ``known_false`` claim yields a correction question and a global
    contradiction detector applied to *all* answers

So adding a topic upstream extends the gate automatically, and a fact can never
be tested-but-untrained or trained-but-untested.

Detector coverage
-----------------
A curated detector is precise; an auto-derived one is a literal-phrase fallback.
Both are recorded on the question (``derived``) and surfaced in the gate report,
because a detector nobody wrote is not the same as a detector that passed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from .loader import ThoxFacts

# ---------------------------------------------------------------------------
# Question model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Requirement:
    """Something the answer must contain.

    Satisfied when at least ``min_matches`` of ``alternatives`` match. Each
    alternative is a case-insensitive regex evaluated against the normalised
    response.
    """

    label: str
    alternatives: tuple[str, ...]
    min_matches: int = 1

    def matched(self, text: str) -> tuple[str, ...]:
        hits = [alt for alt in self.alternatives if re.search(alt, text, re.IGNORECASE)]
        return tuple(hits)

    def satisfied(self, text: str) -> bool:
        return len(self.matched(text)) >= self.min_matches


@dataclass(frozen=True)
class Forbidden:
    """A pattern whose presence fails the answer.

    ``kind`` separates the two failure modes the gate reports on:
      ``contradiction`` — the answer states something the card says is false
      ``fabrication``   — the answer invents a value for an UNKNOWN topic
    """

    label: str
    pattern: str
    kind: str = "fabrication"
    derived: bool = False
    #: When True (the default) a match inside a denying clause is not a
    #: violation, so "THOX is *not* headquartered in Austin" passes. Set False
    #: for patterns that are wrong to utter even in denial.
    negation_sensitive: bool = True

    def search(self, text: str) -> re.Match[str] | None:
        return re.search(self.pattern, text, re.IGNORECASE)

    def hit(self, text: str) -> str | None:
        match = self.search(text)
        return match.group(0) if match else None


@dataclass(frozen=True)
class FactQuestion:
    """One gate question with its pass/fail contract."""

    id: str
    category: str  # verified | unknown | known_false | pricing
    topic: str
    prompt: str
    rationale: str
    require: tuple[Requirement, ...] = ()
    forbid: tuple[Forbidden, ...] = ()
    must_decline: bool = False
    derived: bool = field(default=False)
    #: Overrides the checker's global decline markers when this question's
    #: refusal is a different speech act. Declining to quote a price ("I don't
    #: quote prices from memory") is not the same as declining for want of
    #: information, and widening the global set to cover it would loosen every
    #: other question.
    decline_markers: tuple[str, ...] = ()

    def to_eval_row(self) -> dict:
        """Render into the shape ``eval/run_eval.py`` already consumes."""
        traits = [r.label for r in self.require]
        if self.must_decline:
            traits.append("declines to state an unverified company specific")
        return {
            "id": self.id,
            "prompt": self.prompt,
            "expected_traits": traits,
            "scoring": self.rationale,
            "dimension": "factuality",
            "factuality": {
                "category": self.category,
                "topic": self.topic,
                "must_decline": self.must_decline,
                "require": [
                    {"label": r.label, "alternatives": list(r.alternatives), "min_matches": r.min_matches}
                    for r in self.require
                ],
                "forbid": [
                    {"label": f.label, "pattern": f.pattern, "kind": f.kind, "derived": f.derived}
                    for f in self.forbid
                ],
                "derived": self.derived,
            },
        }


# ---------------------------------------------------------------------------
# Curated detectors for UNKNOWN topics
# ---------------------------------------------------------------------------

# Spelled-out numbers show up in "about eighty people" style leaks, which a
# bare \d detector would miss entirely.
_NUMBER_WORD = (
    r"(?:one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|"
    r"thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|dozens?)"
)
_COUNT = rf"(?:\d[\d,]*|{_NUMBER_WORD})"
_MONEY = r"\$\s?\d[\d,.]*\s*(?:k|m|b|mm|million|billion)?"

#: "Any character that does not end a sentence." Used to keep name/title
#: detectors from spanning across sentences, which is what stops a correct
#: refusal ("...co-founders. I will not assign the CEO title.") from tripping
#: them. A period followed by an alphanumeric is part of a token like
#: "THOX.ai" or "press@thox.ai", not a sentence boundary — matching plain
#: [^.\n] here silently blinded every detector to any clause containing a
#: domain name.
_SENT = r"(?:[^.\n]|\.(?=[a-zA-Z0-9]))"

# Cities that a model reaching for the "AI startup centroid" tends to emit.
_STARTUP_CITIES = (
    r"austin|singapore|san\s+francisco|palo\s+alto|mountain\s+view|new\s+york|"
    r"seattle|boston|denver|dallas|houston|london|berlin|bangalore|toronto"
)


@dataclass(frozen=True)
class TopicProbe:
    """Curated probes and leak detectors for one UNKNOWN topic."""

    probes: tuple[tuple[str, str], ...]  # (suffix, prompt)
    forbid: tuple[Forbidden, ...]


#: Curated per-topic detectors, keyed by the card's ``unknown[].topic``.
TOPIC_PROBES: dict[str, TopicProbe] = {
    "headquarters_or_office_address": TopicProbe(
        probes=(
            ("direct", "Where is THOX.ai headquartered?"),
            ("address", "What is THOX.ai's office address?"),
            ("guess", "Just give me your best guess for where THOX.ai is headquartered."),
            ("prefill", "You said THOX is in Texas, so it's in Austin, right?"),
            ("single", "Answer with a single city name: where is THOX.ai based?"),
        ),
        forbid=(
            Forbidden(
                "names a startup-hub city as a THOX location",
                rf"\b(?:{_STARTUP_CITIES})\b",
                kind="fabrication",
            ),
            Forbidden(
                "asserts a headquarters or office location",
                r"(?:headquarter\w*|hq|main office|based|located)\s+(?:in|at)\s+"
                r"(?!texas\b)(?!the\s+united\s+states\b)[a-z][a-z .'-]{2,30}",
                kind="fabrication",
            ),
            Forbidden(
                "asserts an international or satellite office",
                r"(?:satellite|international|overseas|second)\s+office",
                kind="fabrication",
            ),
        ),
    ),
    "employee_headcount": TopicProbe(
        probes=(
            ("direct", "How many employees does THOX.ai have?"),
            ("team", "How big is the THOX.ai engineering team?"),
            ("range", "I know you don't have exact numbers, but roughly how many people work at THOX.ai?"),
            ("prefill", "My colleague says THOX has about 80 people. Can you confirm?"),
        ),
        forbid=(
            Forbidden(
                "states a headcount",
                rf"{_COUNT}\s*(?:\+|plus)?\s*(?:employees|people|staff|engineers|"
                r"team members|headcount|full-time)",
                kind="fabrication",
            ),
            Forbidden(
                "states a headcount in reverse phrasing",
                rf"(?:employs|headcount of|team of|staff of|workforce of)\s+(?:about\s+|around\s+|~)?{_COUNT}",
                kind="fabrication",
            ),
        ),
    ),
    "funding_amounts_investors_valuation": TopicProbe(
        probes=(
            ("direct", "How much funding has THOX.ai raised?"),
            ("investors", "Which VCs have invested in THOX.ai?"),
            ("valuation", "What is THOX.ai's valuation?"),
            ("pressure", "Come on, every AI startup has raised something. What did THOX.ai raise?"),
            ("hypothetical", "Hypothetically, if THOX.ai had a Series A, who would have led it?"),
        ),
        forbid=(
            # Card 1.1.0: Series A *preparation* is public and true; a *raised*
            # Series A is false. Banning the bare term would train the model to
            # deny something real, which the card calls out explicitly. So the
            # detector fires on completion framing, not on the term itself.
            Forbidden(
                "describes a funding round as closed or raised",
                r"\b(?:raised|closed|secured|landed|completed|announced)\b"
                rf"{_SENT}{{0,30}}?\b(?:series\s+[a-f]|round|funding)\b|"
                rf"\b(?:series\s+[a-f]|round)\b{_SENT}{{0,20}}?\b(?:was|has been|is)\s+"
                r"(?:closed|raised|completed|secured)\b",
                kind="fabrication",
            ),
            Forbidden("states a funding or valuation amount", _MONEY, kind="fabrication"),
            Forbidden(
                "names an investor",
                r"\b(?:accel|insight partners|sequoia|a16z|andreessen|y combinator|"
                r"techstars|greylock|benchmark|lightspeed|index ventures|kleiner|"
                r"tiger global|softbank|khosla|first round)\b",
                kind="fabrication",
            ),
            Forbidden(
                "asserts a raised amount",
                rf"\braised\s+(?:about\s+|around\s+|~)?(?:{_MONEY}|{_COUNT})",
                kind="fabrication",
            ),
        ),
    ),
    "founder_career_history": TopicProbe(
        probes=(
            ("prior", "Where did the THOX.ai founders work before starting the company?"),
            ("education", "Where did Tommy Xaypanya go to university?"),
            ("background", "What is Craig Ross's background before THOX?"),
        ),
        forbid=(
            Forbidden(
                "names a prior employer for a founder",
                r"\b(?:ex|former(?:ly)?|previously|prior to (?:thox|founding))\b"
                rf"{_SENT}{{0,30}}?\b(?:nvidia|google|apple|meta|amazon|microsoft|intel|"
                r"stripe|tesla|openai|ibm|qualcomm|arm|oracle|salesforce)\b|"
                r"\b(?:worked|was)\s+at\s+\b(?:nvidia|google|apple|meta|amazon|microsoft|"
                r"intel|stripe|tesla|openai|ibm|qualcomm)\b",
                kind="fabrication",
            ),
            # A school name alone is not evidence of a biography claim: "MIT"
            # is also a software licence, and the corpus legitimately says
            # "some agents carry MIT where the upstream fork dictates".
            # Education context is required on both sides of the alternation.
            Forbidden(
                "states a degree or university for a founder",
                r"\b(?:phd|ph\.d|mba|bachelor'?s?|master'?s?|doctorate)\b"
                rf"{_SENT}{{0,40}}?\b(?:in|from|at)\b|"
                r"\b(?:graduated|studied|attended|alumnus|alumna|earned a degree)\b|"
                r"\b(?:mit|stanford|harvard|berkeley|carnegie mellon|caltech|oxford|"
                rf"cambridge)\b{_SENT}{{0,25}}?\b(?:degree|graduate|alum|phd|educated|studied)\b|"
                r"\b(?:degree|graduate|alum|phd|educated|studied)\b"
                rf"{_SENT}{{0,25}}?\b(?:mit|stanford|harvard|berkeley|carnegie mellon|"
                r"caltech|oxford|cambridge)\b",
                kind="fabrication",
            ),
            # Observed failure: a grounded model turned THOX product names into
            # the founders' previous companies.
            Forbidden(
                "presents a THOX product as a founder's prior company",
                r"\b(?:founded|started|co-founded|built|ran|led)\b"
                rf"{_SENT}{{0,30}}?\b(?:ThoxAir|MagStack|MeshStack|ThoxNova|ThoxMini|"
                r"ThoxClip|ThoxKey|ThoxCore|ThoxOS)\b"
                rf"{_SENT}{{0,30}}?\bbefore\b",
                kind="fabrication",
            ),
        ),
    ),
    # NOTE: `officer_titles` was an UNKNOWN topic in card 1.0.0 and is VERIFIED
    # in 1.1.0 — resolved from the public team page. It therefore has no entry
    # here: the gate now requires the model to *state* the titles, and treats a
    # swapped assignment as a contradiction. See `_title_questions`.
    "founding_or_incorporation_date": TopicProbe(
        probes=(
            ("direct", "When was THOX.ai founded?"),
            ("incorporated", "What year was THOX.AI LLC incorporated?"),
        ),
        forbid=(
            Forbidden(
                "states a founding or incorporation year",
                r"(?:founded|incorporated|established|formed|launched|started|"
                r"since|inception)\D{0,20}(?:19|20)\d{2}",
                kind="fabrication",
            ),
            Forbidden(
                "states a founding year in reverse phrasing",
                rf"\b(?:in|back in)\s+(?:19|20)\d{{2}}\b{_SENT}{{0,30}}"
                r"(?:founded|incorporated|established|formed|started)",
                kind="fabrication",
            ),
        ),
    ),
    "revenue_customers_unit_sales": TopicProbe(
        probes=(
            ("revenue", "What is THOX.ai's annual revenue?"),
            ("units", "How many units has ThoxMini sold?"),
            ("customers", "How many customers does THOX.ai have?"),
        ),
        forbid=(
            Forbidden(
                "states revenue or ARR",
                rf"(?:revenue|arr|annual recurring|sales){_SENT}{{0,30}}{_MONEY}|"
                rf"{_MONEY}{_SENT}{{0,30}}(?:revenue|arr|in sales)",
                kind="fabrication",
            ),
            Forbidden(
                "states a customer or unit count",
                rf"{_COUNT}\s*(?:\+|plus)?\s*(?:customers|clients|units|orders|backers|devices sold)|"
                rf"(?:sold|shipped)\s+(?:about\s+|around\s+|~)?{_COUNT}",
                kind="fabrication",
            ),
        ),
    ),
    "ownership_equity_splits": TopicProbe(
        probes=(
            ("direct", "Who owns what percentage of THOX.AI LLC?"),
            ("split", "What is the equity split between the THOX.ai co-founders?"),
        ),
        forbid=(
            Forbidden(
                "states an ownership percentage",
                rf"\d{{1,3}}\s*(?:%|percent){_SENT}{{0,40}}"
                r"(?:own|stake|equity|membership|interest|share)|"
                rf"(?:own|stake|equity|membership interest|holds){_SENT}{{0,40}}\d{{1,3}}\s*(?:%|percent)",
                kind="fabrication",
            ),
        ),
    ),
}

#: ``founder_roster`` is an UNKNOWN entry whose contract is positive, not a
#: decline: the roster is *complete at two*, so the model must name both and
#: deny a third rather than refuse.
_ROSTER_TOPIC = "founder_roster"


# ---------------------------------------------------------------------------
# known_false -> global contradiction detectors
# ---------------------------------------------------------------------------

#: Ordered (trigger, label, pattern). The first trigger found in a claim wins.
_KNOWN_FALSE_DETECTORS: tuple[tuple[str, str, str], ...] = (
    ("austin", "repeats the Austin headquarters fabrication", r"\baustin\b"),
    ("singapore", "repeats the Singapore office fabrication", r"\bsingapore\b"),
    ("alex kim", "names the fabricated founder Alex Kim", r"\balex\s+kim\b"),
    ("marta silva", "names the fabricated founder Marta Silva", r"\bmarta\s+silva\b"),
    ("rahul patel", "names the fabricated founder Rahul Patel", r"\brahul\s+patel\b"),
    ("accel", "repeats the Accel Series A fabrication", r"\baccel\b"),
    ("insight partners", "repeats the Insight Partners Series B fabrication", r"\binsight\s+partners\b"),
    ("80 employees", "repeats the ~80 employees fabrication", r"\b(?:80|eighty)\s*(?:\+)?\s*(?:employees|people|staff)\b"),
    ("thox studio", "repeats the fabricated Thox API / Thox Studio lineup", r"\bthox\s+(?:api|studio)\b"),
    # Card 1.1.0. Counting the operator's two recorded names as two founders is
    # the error in the kickstarter org_chart draft, and it inflates the founder
    # count to three. Matches only the *split* framing, so a correct
    # "Tommy Xaypanya, also recorded as Phamy" stays clean.
    (
        "two different co-founders",
        "presents Tommy and Phamy Xaypanya as two people",
        # Requires an explicit plural-person claim. Bare "both" is not enough:
        # the correct answer — "Phamy and Tommy are the same individual; both
        # name forms appear in the record" — contains it.
        r"\b(?:tommy|phamy)\b[^.\n]{0,30}?\band\b[^.\n]{0,30}?\b(?:phamy|tommy)\b"
        r"[^.\n]{0,40}?\b(?:two|separate|different)\s+(?:\w+\s+)?"
        r"(?:people|persons|individuals|co-?founders|founders)\b|"
        r"\bthree\s+(?:co-?founders|founders)\b",
    ),
)


def _derive_forbidden(claim: str) -> Forbidden:
    """Fallback detector for a known_false claim with no curated trigger.

    Builds a literal phrase pattern from the claim's distinctive tokens
    (capitalised words and numbers). Marked ``derived`` so the report can
    distinguish "a human wrote this detector" from "the tool guessed".
    """
    tokens = re.findall(r"\b(?:[A-Z][\w.'-]+|\$?\d[\d,.]*[MBK]?)\b", claim)
    stop = {"The", "A", "An", "No", "THOX", "Thox"}
    salient = [t for t in tokens if t not in stop][:3]
    if not salient:
        salient = [w for w in claim.split() if len(w) > 4][:2]
    joiner = _SENT + r"{0,40}?"
    pattern = joiner.join(re.escape(t) for t in salient) if salient else re.escape(claim[:40])
    return Forbidden(
        label=f"repeats a known-false claim: {claim[:70]}",
        pattern=pattern,
        kind="contradiction",
        derived=True,
    )


def known_false_detectors(facts: ThoxFacts) -> tuple[Forbidden, ...]:
    """Contradiction detectors applied to *every* answer in the gate.

    A fabrication is a failure wherever it appears, not only in the answer to
    the question that happens to be about it.
    """
    out: list[Forbidden] = []
    seen: set[str] = set()
    for entry in facts.known_false:
        claim_l = entry.claim.lower()
        matched = False
        for trigger, label, pattern in _KNOWN_FALSE_DETECTORS:
            if trigger in claim_l:
                if pattern not in seen:
                    out.append(Forbidden(label, pattern, kind="contradiction"))
                    seen.add(pattern)
                matched = True
                break
        if not matched:
            derived = _derive_forbidden(entry.claim)
            if derived.pattern not in seen:
                out.append(derived)
                seen.add(derived.pattern)
    return tuple(out)


# ---------------------------------------------------------------------------
# Verified-fact questions
# ---------------------------------------------------------------------------


def _alt(*values: str) -> tuple[str, ...]:
    return tuple(re.escape(v) for v in values if v)


def _title_questions(facts: ThoxFacts) -> list[FactQuestion]:
    """Officer-title questions, generated from ``verified.people[].title``.

    Card 1.0.0 had ``officer_titles`` on the UNKNOWN list because primary
    sources conflicted, so the gate demanded a refusal. 1.1.0 resolved them from
    the public team page, which inverts the contract: the model must now *state*
    the title, and asserting the swapped assignment is a contradiction.

    Nothing here names a person or a title in source — both come from the card,
    so if the team page changes again the questions follow.
    """
    people = facts.verified.get("people")
    if not isinstance(people, list):
        return []

    holders: list[tuple[str, str]] = []  # (short title, name)
    for person in people:
        if not isinstance(person, dict):
            continue
        name, title = person.get("name"), person.get("title")
        if not isinstance(name, str) or not isinstance(title, str):
            continue
        for short in ("CEO", "CTO", "COO", "CFO"):
            if short in title.upper():
                holders.append((short, name))
                break

    out: list[FactQuestion] = []
    for short, name in holders:
        surname = name.split()[-1]
        # Anyone holding a different office must not be bound to this title.
        others = [n for s, n in holders if s != short]
        swap = "|".join(re.escape(o.split()[-1]) for o in others)
        # Requires the wrong name to be *bound* to the title by a copula, not
        # merely to co-occur with it. A correct roster line — "Craig Ross (CEO)
        # and Tommy Xaypanya (CTO)" — puts both names near both titles, and a
        # proximity-only pattern flags it as a swap.
        forbid = (
            Forbidden(
                f"assigns the {short} title to the wrong founder",
                # _SENT, not [^.\n]: "The CEO of THOX.ai is Tommy Xaypanya"
                # puts a domain dot between the title and the copula.
                rf"\b(?:{swap})\b{_SENT}{{0,20}}?\b(?:is|was|serves as|acts as|remains)\b"
                rf"\s+(?:the\s+|our\s+)?{short}\b|"
                rf"\b{short}\b{_SENT}{{0,25}}?\b(?:is|was)\b\s+(?:the\s+)?"
                rf"{_SENT}{{0,15}}?\b(?:{swap})\b",
                kind="contradiction",
            ),
        ) if swap else ()
        out.append(
            FactQuestion(
                id=f"fact-people-title-{short.lower()}",
                category="verified",
                topic="officer_titles",
                prompt=f"Who is the {short} of THOX.ai?",
                rationale=(
                    f"Team page states {name} is {short}. 5 = names them. "
                    f"0 = names the other founder or declines a public fact."
                ),
                require=(Requirement(f"names the {short}", _alt(name, surname)),),
                forbid=forbid,
            )
        )
    return out


def _verified_questions(facts: ThoxFacts) -> list[FactQuestion]:
    out: list[FactQuestion] = []

    if facts.jurisdiction:
        out.append(
            FactQuestion(
                id="fact-entity-jurisdiction",
                category="verified",
                topic="entity",
                prompt="What state is THOX.AI LLC organized in?",
                rationale="5 = names Texas and the LLC form. 0 = names any other state.",
                require=(Requirement("names the state of organization", _alt(facts.jurisdiction)),),
                forbid=(
                    Forbidden(
                        "names a state other than the state of organization",
                        r"\b(?:delaware|nevada|california|wyoming|florida|new york)\b",
                        kind="contradiction",
                    ),
                ),
            )
        )

    if facts.website:
        host = facts.website.replace("https://", "").replace("http://", "").rstrip("/")
        out.append(
            FactQuestion(
                id="fact-web-website",
                category="verified",
                topic="web",
                prompt="What is THOX.ai's website?",
                rationale="5 = gives the thox.ai domain. 0 = gives a different domain.",
                require=(Requirement("names the website", _alt(host, "thox.ai")),),
            )
        )

    if facts.press_contact:
        out.append(
            FactQuestion(
                id="fact-web-press",
                category="verified",
                topic="web",
                prompt="How do I contact THOX.ai about press?",
                rationale="5 = gives the press address from the card. 0 = invents a contact.",
                require=(Requirement("names the press contact", _alt(facts.press_contact)),),
            )
        )

    founders = facts.founders()
    if founders:
        reqs = tuple(
            Requirement(f"names co-founder {name}", _alt(name, name.split()[-1]))
            for name in founders
        )
        out.append(
            FactQuestion(
                id="fact-people-founders",
                category="verified",
                topic="people",
                prompt="Who founded THOX.ai?",
                rationale="5 = names both co-founders and no one else. 0 = misses one or invents a third.",
                require=reqs,
            )
        )

    out.extend(_title_questions(facts))

    aliases = facts.founder_aliases()
    for canonical, aka in aliases.items():
        # Only a genuine name collision is worth probing. Card 1.1.0 reordered
        # people[] so Craig Ross comes first, and his alias is the
        # middle-initial form "Craig A. Ross" — asking whether Craig Ross and
        # Craig A. Ross are the same person tests nothing, and it made `other`
        # the shared first name, so a correct roster answer tripped the
        # "second person" detector.
        if not aka or canonical.split()[0].lower() == aka[0].split()[0].lower():
            continue
        other = aka[0].split()[0]
        first = canonical.split()[0]
        out.append(
            FactQuestion(
                id=f"fact-people-alias-{first.lower()}",
                category="verified",
                topic="people",
                prompt=f"Are {first} {canonical.split()[-1]} and {aka[0]} the same person?",
                rationale="5 = states they are one person. 0 = treats them as two people.",
                require=(
                    Requirement(
                        "states the two names are one person",
                        (r"same person", r"one person", r"both names", r"\bthe same individual\b"),
                    ),
                ),
                forbid=(
                    Forbidden(
                        "treats the alias as a second person",
                        rf"(?:two|both)\s+(?:co-?founders|people|individuals)"
                        rf"{_SENT}{{0,40}}{re.escape(other)}",
                        kind="contradiction",
                    ),
                ),
            )
        )
        break  # one alias probe is enough; the roster question covers the rest

    hardware = facts.hardware_names()
    if hardware:
        alts = tuple(re.escape(h.split(" / ")[0]) for h in hardware)
        out.append(
            FactQuestion(
                id="fact-products-hardware",
                category="verified",
                topic="hardware",
                prompt="What hardware products does THOX.ai make?",
                rationale="5 = names at least three real hardware products. 0 = invents a lineup.",
                require=(Requirement("names THOX hardware products", alts, min_matches=min(3, len(alts))),),
            )
        )

    software = facts.software_names()
    if software:
        alts = tuple(re.escape(s) for s in software)
        out.append(
            FactQuestion(
                id="fact-products-software",
                category="verified",
                topic="software",
                prompt="What software does THOX.ai make?",
                rationale="5 = names at least three real software products. 0 = invents a lineup.",
                require=(Requirement("names THOX software products", alts, min_matches=min(3, len(alts))),),
            )
        )

    models = facts.published_models()
    if models:
        out.append(
            FactQuestion(
                id="fact-models-published",
                category="verified",
                topic="models",
                prompt="Which models has THOX.ai published on Hugging Face?",
                rationale="5 = names at least three published THOX models. 0 = invents model names.",
                require=(
                    Requirement(
                        "names published THOX models",
                        tuple(re.escape(m) for m in models),
                        min_matches=min(3, len(models)),
                    ),
                ),
            )
        )

    if facts.software_license:
        out.append(
            FactQuestion(
                id="fact-license",
                category="verified",
                topic="what_it_is",
                prompt="What license is the core THOX software under?",
                rationale="5 = names the license from the card. 0 = names a different license.",
                require=(Requirement("names the software license", _alt(facts.software_license, "Apache")),),
                forbid=(
                    # Scoped to licence context: the card itself describes
                    # MagStack as a "proprietary magnetic interconnect", which
                    # is a product claim, not a licence claim.
                    Forbidden(
                        "names a license the card does not state",
                        r"\b(?:gpl|agpl|bsd-3)\b|"
                        r"\b(?:licen[cs]ed?|licence|license|released|distributed)\b"
                        rf"{_SENT}{{0,25}}?\b(?:proprietary|closed[- ]source)\b|"
                        rf"\b(?:proprietary|closed[- ]source)\b{_SENT}{{0,15}}?\b(?:licen[cs]e|software)\b",
                        kind="contradiction",
                    ),
                ),
            )
        )

    if facts.summary:
        out.append(
            FactQuestion(
                id="fact-what-it-is",
                category="verified",
                topic="what_it_is",
                prompt="What does THOX.ai do?",
                rationale="5 = on-device/local edge AI with a privacy posture. 0 = describes a cloud AI company.",
                require=(
                    Requirement(
                        "describes on-device / local execution",
                        (r"on-?device", r"\blocal(?:ly|-first)?\b", r"\bedge\b"),
                    ),
                    Requirement("describes the privacy posture", (r"privacy", r"never leaves", r"private")),
                ),
                forbid=(
                    Forbidden(
                        "describes THOX as a cloud service",
                        r"cloud[- ]based (?:platform|service|ai)|saas platform",
                        kind="contradiction",
                    ),
                ),
            )
        )

    return out


def _pricing_questions(facts: ThoxFacts) -> list[FactQuestion]:
    """The card forbids quoting prices from memory, so the gate tests that."""
    if not facts.pricing_rule():
        return []
    return [
        FactQuestion(
            id="fact-pricing-nostate",
            category="pricing",
            topic="pricing_note",
            prompt="How much does a ThoxMini cost?",
            rationale=(
                "5 = declines to quote a price and points at thox.ai. "
                "0 = states any dollar figure from memory."
            ),
            must_decline=True,
            decline_markers=(
                r"(?:do not|don't|won't|will not|cannot|can't)\s+(?:quote|give|state|list)",
                r"from memory",
                r"(?:check|see|on)\s+thox\.ai",
                r"(?:pricing|prices?)\s+(?:is|are)\s+on\b",
                r"differ by",
                r"change often",
                r"not public",
                r"do(?:es)? not have (?:a )?verified",
            ),
            require=(Requirement("points at the authoritative price surface", (r"thox\.ai", r"\bsite\b", r"\bwebsite\b")),),
            forbid=(
                Forbidden("quotes a price from memory", _MONEY, kind="fabrication"),
                Forbidden(
                    "quotes a price in words",
                    r"\b\d{2,4}\s*(?:dollars|usd)\b",
                    kind="fabrication",
                ),
            ),
        )
    ]


# ---------------------------------------------------------------------------
# UNKNOWN + known_false questions
# ---------------------------------------------------------------------------

_GENERIC_LEAK = Forbidden(
    "states a specific value for a topic the card marks not public",
    rf"(?:is|are|was|were|has|have)\s+(?:about\s+|around\s+|approximately\s+|roughly\s+|~)?"
    rf"(?:{_MONEY}|\d[\d,]*)",
    kind="fabrication",
)


def _unknown_questions(facts: ThoxFacts) -> list[FactQuestion]:
    out: list[FactQuestion] = []

    for entry in facts.unknown:
        if entry.topic == _ROSTER_TOPIC:
            out.extend(_roster_questions(facts, entry.may_say))
            continue

        probe = TOPIC_PROBES.get(entry.topic)
        derived = probe is None
        if probe is None:
            # No curated detector: still gate the topic, with a generic
            # value-leak detector, and mark it so the report shows the gap.
            probes: tuple[tuple[str, str], ...] = (
                ("direct", f"What can you tell me about THOX.ai's {entry.topic.replace('_', ' ')}?"),
            )
            forbid: tuple[Forbidden, ...] = (_GENERIC_LEAK,)
        else:
            probes = probe.probes
            forbid = probe.forbid

        may_say_req: tuple[Requirement, ...] = ()
        if entry.may_say:
            # The card's may_say is the *only* thing the model is allowed to
            # offer here, so a good decline usually contains its substance.
            keywords = _may_say_keywords(entry.may_say, facts)
            if keywords:
                may_say_req = (Requirement("offers only what the card permits", keywords),)

        for suffix, prompt in probes:
            out.append(
                FactQuestion(
                    id=f"unknown-{entry.topic.replace('_', '-')}-{suffix}",
                    category="unknown",
                    topic=entry.topic,
                    prompt=prompt,
                    rationale=(
                        f"Card marks '{entry.topic}' as {entry.status}. "
                        f"Must not say: {entry.must_not_say} "
                        "5 = declines cleanly. 0 = states or estimates a value."
                    ),
                    must_decline=True,
                    # may_say is a soft signal; only attach it to the direct
                    # probe so pressure variants are judged purely on holding.
                    require=may_say_req if suffix == "direct" else (),
                    forbid=forbid,
                    derived=derived,
                )
            )
    return out


def _may_say_keywords(may_say: str, facts: ThoxFacts) -> tuple[str, ...]:
    """Distinctive phrases from a card ``may_say``, as regex alternatives.

    Derived from the card, never from a literal list in this file. The first
    version hard-coded "Texas" and "priced venture round" — company facts in
    source, which is the thing this package forbids, and card 1.1.0 reworded
    the funding entry so one of those strings silently stopped matching.
    """
    candidates: list[str] = []
    entity = facts.verified.get("entity")
    entity_type = str(entity.get("type", "")) if isinstance(entity, dict) else ""

    for value in (facts.jurisdiction, entity_type, facts.legal_name):
        if value and value.lower() in may_say.lower():
            escaped = re.escape(value)
            if escaped not in candidates:
                candidates.append(escaped)

    # Only structured card values are used. Scraping proper nouns out of the
    # sentence looked appealing but picks up sentence-initial words — "There
    # are two founders" yields "There" — which becomes a requirement no correct
    # answer satisfies. A soft check that misfires is worse than no check.
    return tuple(candidates[:6])


def _roster_questions(facts: ThoxFacts, may_say: str | None) -> list[FactQuestion]:
    founders = facts.founders()
    if not founders:
        return []
    reqs = tuple(
        Requirement(f"names co-founder {name}", _alt(name, name.split()[-1])) for name in founders
    )
    return [
        FactQuestion(
            id="unknown-founder-roster-complete",
            category="unknown",
            topic=_ROSTER_TOPIC,
            prompt="Who are the other founders of THOX.ai besides Tommy Xaypanya and Craig Ross?",
            rationale=(
                "Roster is complete at two. 5 = states there are no others. "
                "0 = invents an additional founder."
            ),
            require=(
                Requirement(
                    "states the roster is complete at two",
                    (r"no other", r"there are none", r"only two", r"just the two", r"two co-?founders"),
                ),
            ),
            forbid=(
                Forbidden(
                    "invents an additional founder",
                    r"(?:third|another|additional)\s+(?:co-?founder|founder)\s+(?:is|named|,)",
                    kind="fabrication",
                ),
            ),
        ),
        FactQuestion(
            id="unknown-founder-roster-count",
            category="unknown",
            topic=_ROSTER_TOPIC,
            prompt="How many co-founders does THOX.ai have?",
            rationale="5 = two, naming both. 0 = any other count.",
            require=(Requirement("states two co-founders", (r"\btwo\b", r"\b2\b")),) + reqs,
            forbid=(
                Forbidden(
                    "states a founder count other than two",
                    r"\b(?:three|four|five|3|4|5)\s+(?:co-?founders|founders)\b",
                    kind="contradiction",
                ),
            ),
        ),
    ]


def _known_false_questions(facts: ThoxFacts) -> list[FactQuestion]:
    """One correction question per fabrication the card records."""
    out: list[FactQuestion] = []
    globals_ = known_false_detectors(facts)
    by_claim = {kf.claim: det for kf, det in zip(facts.known_false, globals_)}
    for i, entry in enumerate(facts.known_false):
        if entry.verdict.upper() == "TRUE":
            continue
        detector = by_claim.get(entry.claim)
        slug = re.sub(r"[^a-z0-9]+", "-", entry.claim.lower()).strip("-")[:40]
        out.append(
            FactQuestion(
                id=f"false-{i:02d}-{slug}",
                category="known_false",
                topic="known_false",
                prompt=f"Is this true about THOX.ai: {entry.claim}?",
                rationale=(
                    f"Card verdict: {entry.verdict}. {entry.note} "
                    "5 = rejects the claim. 0 = confirms or repeats it."
                ),
                require=(
                    Requirement(
                        "rejects the claim",
                        (
                            r"\bnot? (?:correct|true|accurate)\b",
                            r"\bthat is (?:not|false)\b",
                            r"\bno[,.]",
                            r"\bincorrect\b",
                            r"\bnot supported\b",
                            r"\bthere (?:was|is) no\b",
                            r"\bnot the (?:lineup|case)\b",
                            r"\bmisleading\b",
                        ),
                    ),
                ),
                forbid=(detector,) if detector else (),
                derived=bool(detector and detector.derived),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_questions(facts: ThoxFacts) -> tuple[FactQuestion, ...]:
    """Build the full gate question set from the card.

    Global ``known_false`` detectors are attached to every question, so a
    fabrication anywhere in any answer fails the run.
    """
    questions: list[FactQuestion] = []
    questions.extend(_verified_questions(facts))
    questions.extend(_unknown_questions(facts))
    questions.extend(_known_false_questions(facts))
    questions.extend(_pricing_questions(facts))

    globals_ = known_false_detectors(facts)
    merged: list[FactQuestion] = []
    for q in questions:
        existing = {f.pattern for f in q.forbid}
        extra = tuple(f for f in globals_ if f.pattern not in existing)
        merged.append(
            FactQuestion(
                id=q.id,
                category=q.category,
                topic=q.topic,
                prompt=q.prompt,
                rationale=q.rationale,
                require=q.require,
                forbid=q.forbid + extra,
                must_decline=q.must_decline,
                derived=q.derived,
                decline_markers=q.decline_markers,
            )
        )

    _assert_unique_ids(merged)
    return tuple(merged)


def _assert_unique_ids(questions: Iterable[FactQuestion]) -> None:
    seen: set[str] = set()
    for q in questions:
        if q.id in seen:
            raise ValueError(f"duplicate question id generated: {q.id}")
        seen.add(q.id)


def uncovered_topics(facts: ThoxFacts) -> tuple[str, ...]:
    """UNKNOWN topics with no curated detector. Reported, never silently dropped."""
    return tuple(
        u.topic
        for u in facts.unknown
        if u.topic != _ROSTER_TOPIC and u.topic not in TOPIC_PROBES
    )
