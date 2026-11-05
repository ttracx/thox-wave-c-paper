"""Error types for the THOX facts subsystem."""

from __future__ import annotations


class FactsError(RuntimeError):
    """Base class for every controlled failure in the facts subsystem."""


class FactsLoadError(FactsError):
    """The facts card is missing, unreadable, or structurally invalid."""


class FactsDriftError(FactsError):
    """The vendored facts card diverges from the upstream single source of truth."""


class FactsCoverageError(FactsError):
    """The card contains an entry the tooling has no detector for.

    Raised rather than silently skipped: an unknown topic with no fabrication
    detector is a hole in the gate, and a hole in the gate reads as a pass.
    """
