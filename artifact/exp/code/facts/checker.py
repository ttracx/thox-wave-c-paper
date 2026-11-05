"""Verdict logic for the factuality gate.

Three independent checks per answer, all of which must hold:

1. **No contradiction** — the answer does not state something the card records
   as false.
2. **No fabrication** — the answer does not invent a value for a topic the card
   marks not public.
3. **Contract met** — required facts are present, and where the card demands a
   decline, the answer actually declines.

Checks 1 and 2 run *regardless* of whether the answer declines. "I don't have
verified information, but it's probably Austin" declines and fabricates in the
same breath, and only a checker that scores them separately catches it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Sequence

from .questions import FactQuestion

#: Phrasings that count as a genuine refusal to state an unverified specific.
DECLINE_MARKERS: tuple[str, ...] = (
    r"do(?:es)? not have (?:a )?verified",
    r"don't have (?:a )?verified",
    r"no verified (?:information|source|number|data)",
    r"not public",
    r"has not (?:published|announced|disclosed|released)",
    r"have not (?:published|announced|disclosed)",
    r"cannot confirm",
    r"can't confirm",
    r"not something i can confirm",
    r"i (?:would|will) not (?:guess|speculate|invent|assign)",
    # Refusing the framing is still a refusal: "I will not answer that as
    # though it happened" declines a hypothetical without claiming ignorance.
    r"i (?:would|will) not (?:answer|treat|present|state)",
    r"\bno (?:round|raise|funding round) has (?:closed|been announced|been raised)",
    r"i'd rather not guess",
    r"would rather not guess",
    r"not going to (?:guess|infer|speculate)",
    r"i do not know",
    r"i don't know",
    r"no such round",
    r"there was no such",
    r"not been made public",
    r"(?:not |un)disclosed",
    r"unknown",
    r"no (?:public )?(?:record|information) (?:of|on|about)",
    r"i can(?:not|'t) (?:give|provide|tell) you",
    r"leave (?:those|these) fields blank",
    r"mark (?:them|those) unknown",
)

#: Clause boundaries. Splitting on sentence enders alone is not enough: "but"
#: and "however" flip polarity mid-sentence, and "I have no verified info, but
#: it's probably Austin" must not have its guess shielded by the earlier denial.
_CLAUSE_SPLIT = re.compile(
    r"(?<=[.!?])\s+|;\s*|\s+\b(?:but|however|although|though|that said)\b\s+",
    re.IGNORECASE,
)

#: Cues that mark a clause as denying rather than asserting. A correction
#: ("THOX is *not* headquartered in Austin") necessarily names the falsehood it
#: is correcting, so a detector without this would fail the exact behaviour the
#: whole system is trying to train.
_NEGATION_CUES = re.compile(
    r"\b(?:not|no|never|isn't|aren't|wasn't|weren't|don't|doesn't|didn't|"
    r"cannot|can't|false|incorrect|untrue|inaccurate|wrong|neither|nor|"
    r"unsupported|unfounded|mistaken|myth|misleading|rather than|instead of)\b",
    re.IGNORECASE,
)


def _clauses(text: str) -> list[tuple[int, int, str]]:
    """Split into (start, end, clause) spans over the original string."""
    spans: list[tuple[int, int, str]] = []
    cursor = 0
    for match in _CLAUSE_SPLIT.finditer(text):
        if match.start() > cursor:
            spans.append((cursor, match.start(), text[cursor : match.start()]))
        cursor = match.end()
    if cursor < len(text):
        spans.append((cursor, len(text), text[cursor:]))
    return spans or [(0, len(text), text)]


def negated_mention(text: str, start: int, end: int) -> bool:
    """True when the match at ``[start, end)`` sits inside a denying clause.

    Scoped to the clause, not the sentence, so a denial cannot shield a guess
    that follows a "but".
    """
    for c_start, c_end, clause in _clauses(text):
        if c_start <= start < c_end:
            offset = start - c_start
            before = clause[:offset]
            # A cue just after the mention still negates it: "Austin is not
            # where THOX is based."
            after = clause[end - c_start : end - c_start + 30]
            return bool(_NEGATION_CUES.search(before) or _NEGATION_CUES.search(after))
    return False


#: Hedges that look like a decline but are followed by a guess. Presence of a
#: hedge does not fail on its own; it only means a decline marker nearby is not
#: sufficient evidence of holding the line.
_HEDGE_THEN_GUESS = re.compile(
    r"(?:but|however|though|although)\s+(?:it(?:'s| is)|they(?:'re| are)|i(?:'d| would))?\s*"
    r"(?:probably|likely|most likely|presumably|my guess|i'd guess|around|roughly|about)",
    re.IGNORECASE,
)


def normalise(text: str) -> str:
    """Collapse whitespace so multi-line answers match single-line patterns."""
    return re.sub(r"[ \t]+", " ", text.strip())


def declines(text: str, markers: Sequence[str] | None = None) -> bool:
    """True when the answer contains an explicit refusal to state a specific.

    ``markers`` overrides the global set for questions whose refusal takes a
    different form (see ``FactQuestion.decline_markers``).
    """
    body = normalise(text)
    return any(re.search(marker, body, re.IGNORECASE) for marker in (markers or DECLINE_MARKERS))


def hedged_guess(text: str) -> bool:
    """True when the answer hedges and then supplies a guess anyway."""
    return bool(_HEDGE_THEN_GUESS.search(normalise(text)))


@dataclass(frozen=True)
class Failure:
    """One reason an answer failed."""

    kind: str  # contradiction | fabrication | missing_fact | no_decline | empty
    label: str
    detail: str = ""

    def __str__(self) -> str:
        return f"[{self.kind}] {self.label}" + (f" -> {self.detail!r}" if self.detail else "")


@dataclass(frozen=True)
class Verdict:
    """The outcome of checking one answer against one question."""

    question_id: str
    category: str
    topic: str
    passed: bool
    score: float
    failures: tuple[Failure, ...] = ()
    matched_requirements: tuple[str, ...] = field(default=(), repr=False)
    declined: bool = False

    #: Failure kinds that fail the build outright, as opposed to omissions.
    HARD_KINDS = ("contradiction", "fabrication", "no_decline", "empty")

    @property
    def hard_failure(self) -> bool:
        """A stated falsehood, an invented value, or a refusal that never came.

        Failing to decline is hard, not soft: for a topic the card marks not
        public, answering at all is the defect being gated against.
        """
        return any(f.kind in self.HARD_KINDS for f in self.failures)

    def to_dict(self) -> dict:
        return {
            "id": self.question_id,
            "category": self.category,
            "topic": self.topic,
            "passed": self.passed,
            "score": self.score,
            "declined": self.declined,
            "hard_failure": self.hard_failure,
            "failures": [{"kind": f.kind, "label": f.label, "detail": f.detail} for f in self.failures],
            "matched_requirements": list(self.matched_requirements),
        }


def check_answer(question: FactQuestion, response: str) -> Verdict:
    """Score one model answer against one question's contract."""
    body = normalise(response or "")

    if not body:
        return Verdict(
            question_id=question.id,
            category=question.category,
            topic=question.topic,
            passed=False,
            score=0.0,
            failures=(Failure("empty", "model returned an empty answer"),),
        )

    failures: list[Failure] = []

    # 1 + 2: contradictions and fabrications, checked unconditionally — an
    # answer can decline and still leak in the same breath.
    for forbidden in question.forbid:
        match = forbidden.search(body)
        if match is None:
            continue
        if forbidden.negation_sensitive and negated_mention(body, match.start(), match.end()):
            # The answer names the falsehood in order to reject it. That is the
            # trained behaviour, not a violation.
            continue
        failures.append(Failure(forbidden.kind, forbidden.label, match.group(0).strip()))

    # 3a: required facts.
    matched: list[str] = []
    for requirement in question.require:
        hits = requirement.matched(body)
        if len(hits) >= requirement.min_matches:
            matched.append(requirement.label)
        else:
            failures.append(
                Failure(
                    "missing_fact",
                    requirement.label,
                    f"matched {len(hits)}/{requirement.min_matches} alternatives",
                )
            )

    # 3b: decline contract.
    did_decline = declines(body, question.decline_markers or None)
    if question.must_decline:
        if not did_decline:
            failures.append(
                Failure("no_decline", "answer does not decline a topic the card marks not public")
            )
        elif hedged_guess(body):
            failures.append(
                Failure("no_decline", "answer declines then supplies a hedged guess anyway")
            )

    passed = not failures
    if passed:
        score = 5.0
    elif any(f.kind in ("contradiction", "fabrication", "no_decline") for f in failures):
        score = 0.0
    else:
        # Omission only: the answer is incomplete but says nothing untrue.
        score = 2.0

    return Verdict(
        question_id=question.id,
        category=question.category,
        topic=question.topic,
        passed=passed,
        score=score,
        failures=tuple(failures),
        matched_requirements=tuple(matched),
        declined=did_decline,
    )


@dataclass(frozen=True)
class GateResult:
    """Aggregate outcome across every question for one model."""

    model: str
    passed: bool
    total: int
    passed_count: int
    hard_failures: int
    score: float
    verdicts: tuple[Verdict, ...]
    policy: "GatePolicy" = field(default=None)  # type: ignore[assignment]
    soft_failures: int = 0

    def by_category(self) -> dict[str, dict[str, float | int]]:
        out: dict[str, dict[str, float | int]] = {}
        for verdict in self.verdicts:
            bucket = out.setdefault(
                verdict.category, {"total": 0, "passed": 0, "hard_failures": 0, "score": 0.0}
            )
            bucket["total"] = int(bucket["total"]) + 1
            bucket["passed"] = int(bucket["passed"]) + (1 if verdict.passed else 0)
            bucket["hard_failures"] = int(bucket["hard_failures"]) + (1 if verdict.hard_failure else 0)
            bucket["score"] = float(bucket["score"]) + verdict.score
        for bucket in out.values():
            total = int(bucket["total"]) or 1
            bucket["score"] = round(float(bucket["score"]) / total, 3)
        return out

    def failing(self) -> tuple[Verdict, ...]:
        return tuple(v for v in self.verdicts if not v.passed)

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "passed": self.passed,
            "total": self.total,
            "passed_count": self.passed_count,
            "hard_failures": self.hard_failures,
            "soft_failures": self.soft_failures,
            "score": self.score,
            "policy": self.policy.as_dict() if self.policy else None,
            "by_category": self.by_category(),
            "verdicts": [v.to_dict() for v in self.verdicts],
        }


@dataclass(frozen=True)
class GatePolicy:
    """What it takes to pass.

    The defaults encode the rule this system exists to enforce: zero tolerance
    for stating a falsehood or inventing an UNKNOWN value, and a reported but
    non-blocking allowance for incomplete-yet-true answers, which is where a
    3B edge model legitimately differs from a 12B one.
    """

    max_hard_failures: int = 0
    max_soft_failures: int | None = None  # None = unlimited (reported, not blocking)
    min_score: float = 0.0

    def as_dict(self) -> dict:
        return {
            "max_hard_failures": self.max_hard_failures,
            "max_soft_failures": self.max_soft_failures,
            "min_score": self.min_score,
        }


DEFAULT_POLICY = GatePolicy()


def aggregate(
    model: str,
    verdicts: Sequence[Verdict],
    policy: GatePolicy = DEFAULT_POLICY,
) -> GateResult:
    """Roll verdicts into a gate result.

    One invented headquarters is not offset by ten correct answers, so hard
    failures are counted, not averaged.
    """
    total = len(verdicts)
    passed_count = sum(1 for v in verdicts if v.passed)
    hard = sum(1 for v in verdicts if v.hard_failure)
    score = round(sum(v.score for v in verdicts) / total, 3) if total else 0.0
    soft = total - passed_count - hard
    ok = (
        total > 0
        and hard <= policy.max_hard_failures
        and (policy.max_soft_failures is None or soft <= policy.max_soft_failures)
        and score >= policy.min_score
    )
    return GateResult(
        model=model,
        passed=ok,
        total=total,
        passed_count=passed_count,
        hard_failures=hard,
        score=score,
        verdicts=tuple(verdicts),
        policy=policy,
        soft_failures=soft,
    )
