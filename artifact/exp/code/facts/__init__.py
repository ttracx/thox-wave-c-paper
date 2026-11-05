"""THOX factuality: one card, every model.

The canonical THOX company-facts card is owned by ``ttracx/thox-system-prompts``
(``facts/thox_facts.json``). This package vendors it, keeps it honest with a
drift check, and derives everything downstream from it:

    facts.loader     load + validate the card
    facts.questions  generate the gate question set
    facts.checker    score an answer against the card
    facts.dataset    generate grounded SFT records (the injection stage)
    facts.prompt     render the system-prompt grounding block
    facts.sync       vendor from upstream, detect drift

No module in this repo should state a THOX company fact in its own source. If
you find yourself typing one, it belongs in the card.
"""

from __future__ import annotations

from .checker import (
    DEFAULT_POLICY,
    Failure,
    GatePolicy,
    GateResult,
    Verdict,
    aggregate,
    check_answer,
    declines,
)
from .dataset import DOMAIN, SftRecord, build_records, counts_by_tag, inject
from .errors import (
    FactsCoverageError,
    FactsDriftError,
    FactsError,
    FactsLoadError,
)
from .loader import (
    CARD_PATH,
    UPSTREAM_PATH,
    UPSTREAM_REPO,
    KnownFalse,
    Provenance,
    ThoxFacts,
    UnknownTopic,
    card_sha256,
    load_facts,
    load_provenance,
)
from .prompt import SYSTEM_THOX, bake, render_facts_block, render_marked_block, render_rule
from .questions import FactQuestion, Forbidden, Requirement, build_questions, uncovered_topics

__all__ = [
    "CARD_PATH",
    "DEFAULT_POLICY",
    "DOMAIN",
    "SYSTEM_THOX",
    "UPSTREAM_PATH",
    "UPSTREAM_REPO",
    "FactQuestion",
    "FactsCoverageError",
    "FactsDriftError",
    "FactsError",
    "FactsLoadError",
    "Failure",
    "Forbidden",
    "GatePolicy",
    "GateResult",
    "KnownFalse",
    "Provenance",
    "Requirement",
    "SftRecord",
    "ThoxFacts",
    "UnknownTopic",
    "Verdict",
    "aggregate",
    "bake",
    "build_questions",
    "build_records",
    "card_sha256",
    "check_answer",
    "counts_by_tag",
    "declines",
    "inject",
    "load_facts",
    "load_provenance",
    "render_facts_block",
    "render_marked_block",
    "render_rule",
    "uncovered_topics",
]
