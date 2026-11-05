#!/usr/bin/env python3
"""Factuality eval gate: no THOX model publishes if it contradicts the card.

Runs the card-derived question set against a model and fails the build when an
answer contradicts a verified fact or invents a value for a topic the card marks
not public.

Grounding modes
---------------
``--grounding none`` (default) sends only the plain THOX house prompt, with no
facts block. That is deliberate: serving-side grounding already fixes the
deployed path, so the gate's job is to prove the *weights* hold up when the
model runs without it — on-device, straight from Ollama, or behind a
third-party OpenAI-compatible client. ``--grounding baked`` additionally checks
the served configuration.

Backends are reused from ``eval/run_eval.py`` rather than reimplemented, so the
gate inherits ollama / llama.cpp / transformers support and any future backend.

Offline scoring
---------------
``--transcript`` scores a recorded ``{question_id: answer}`` JSON file instead
of calling a model. This is how the gate is unit-tested against golden files and
how a GPU-produced transcript can be scored on a runner that has no GPU.

Exit codes:
  0 - gate passed
  1 - gate failed (contradiction, fabrication, or missing decline)
  2 - the gate could not run (bad args, unreachable backend, unreadable card)
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import pathlib
import sys
from typing import Callable

# VENDORED for the HF gate49 bundle (gate49/ in the thox-compute and
# thox-training-control Space repos): the script sits at the bundle root with
# the facts/ package beside it, so the bundle root replaces the repo root of
# the original scripts/factuality_gate.py layout. Nothing else differs.
REPO_ROOT = pathlib.Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from facts import (  # noqa: E402
    FactsError,
    GatePolicy,
    GateResult,
    aggregate,
    build_questions,
    check_answer,
    load_facts,
    render_facts_block,
)
from facts.loader import ThoxFacts  # noqa: E402
from facts.prompt import SYSTEM_THOX  # noqa: E402
from facts.questions import FactQuestion, uncovered_topics  # noqa: E402

DEFAULT_OUT = REPO_ROOT / "eval" / "results" / "factuality"


class GateError(RuntimeError):
    """The gate could not be run (as distinct from the model failing it)."""


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------


def _load_eval_harness():
    """Import ``eval/run_eval.py`` for its backend implementations."""
    eval_dir = REPO_ROOT / "eval"
    if str(eval_dir) not in sys.path:
        sys.path.insert(0, str(eval_dir))
    try:
        import run_eval  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment problem
        raise GateError(f"cannot import eval/run_eval.py: {exc}") from exc
    return run_eval


def build_system_prompt(facts: ThoxFacts, grounding: str) -> str:
    if grounding == "none":
        return SYSTEM_THOX
    if grounding == "baked":
        return f"{SYSTEM_THOX}\n\n{render_facts_block(facts)}"
    raise GateError(f"unknown grounding mode: {grounding}")


def make_model_runner(
    model: str,
    backend: str,
    system: str,
    *,
    max_new_tokens: int,
    temperature: float,
) -> Callable[[str], str]:
    """Return a callable that answers one prompt, using the eval backends."""
    run_eval = _load_eval_harness()
    resolved = backend if backend != "auto" else run_eval.detect_backend(model)

    def _run(prompt: str) -> str:
        try:
            return run_eval.generate(
                backend=resolved,
                model_ref=model,
                system=system,
                user=prompt,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
            )
        except run_eval.EvalError as exc:
            raise GateError(f"inference failed for {model}: {exc}") from exc

    return _run


def load_transcript(path: pathlib.Path) -> dict[str, str]:
    """Load a recorded ``{question_id: answer}`` map."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise GateError(f"cannot read transcript {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise GateError(f"transcript {path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise GateError(f"transcript {path} must be an object of id -> answer")
    answers = data.get("answers") if "answers" in data else data
    if not isinstance(answers, dict):
        raise GateError(f"transcript {path}: 'answers' must be an object")
    return {str(k): str(v) for k, v in answers.items()}


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------


def run_gate(
    model: str,
    questions: tuple[FactQuestion, ...],
    answer_for: Callable[[str], str],
    policy: GatePolicy,
    *,
    verbose: bool = True,
) -> GateResult:
    """Ask every question, check every answer, aggregate."""
    verdicts = []
    for i, question in enumerate(questions, 1):
        try:
            answer = answer_for(question.prompt)
        except GateError:
            raise
        verdict = check_answer(question, answer)
        verdicts.append(verdict)
        if verbose:
            mark = "pass" if verdict.passed else ("HARD FAIL" if verdict.hard_failure else "soft fail")
            print(f"  [{i}/{len(questions)}] {question.id}: {mark}")
            if not verdict.passed:
                for failure in verdict.failures:
                    print(f"        {failure}")
    return aggregate(model, verdicts, policy)


def render_markdown(
    result: GateResult,
    facts: ThoxFacts,
    *,
    grounding: str,
    uncovered: tuple[str, ...],
    answers: dict[str, str] | None = None,
) -> str:
    status = "PASS" if result.passed else "FAIL"
    provenance = facts.provenance
    lines = [
        f"# Factuality gate: {result.model}",
        "",
        f"**{status}** — {result.passed_count}/{result.total} questions passed, "
        f"{result.hard_failures} hard failures, score {result.score}/5.",
        "",
        f"- Card version `{facts.version}` (generated {facts.generated})",
    ]
    if provenance:
        lines.append(
            f"- Source `{provenance.repo}` @ `{provenance.ref}` "
            f"({provenance.short_commit}), sha256 `{provenance.sha256[:12]}`"
        )
    lines += [
        f"- Grounding: `{grounding}`"
        + (" (weights only, no facts block in context)" if grounding == "none" else " (facts block in system prompt)"),
        f"- Policy: {result.policy.as_dict() if result.policy else '{}'}",
        "",
        "## By category",
        "",
        "| Category | Passed | Hard failures | Score |",
        "| --- | --- | --- | --- |",
    ]
    for category, stats in sorted(result.by_category().items()):
        lines.append(
            f"| {category} | {stats['passed']}/{stats['total']} | {stats['hard_failures']} | {stats['score']} |"
        )

    failing = result.failing()
    lines += ["", "## Failures", ""]
    if not failing:
        lines.append("None.")
    else:
        for verdict in failing:
            severity = "HARD" if verdict.hard_failure else "soft"
            lines.append(f"### `{verdict.question_id}` ({severity}, {verdict.category}/{verdict.topic})")
            for failure in verdict.failures:
                lines.append(f"- **{failure.kind}** — {failure.label}" + (f" → `{failure.detail}`" if failure.detail else ""))
            if answers and verdict.question_id in answers:
                excerpt = answers[verdict.question_id].strip().replace("\n", " ")[:300]
                lines.append(f"  - answer: `{excerpt}`")
            lines.append("")

    if uncovered:
        lines += [
            "## Coverage gaps",
            "",
            "These card topics have no curated fabrication detector and were gated with a "
            "generic value-leak pattern only. Add a detector in `facts/questions.py`:",
            "",
        ]
        lines += [f"- `{topic}`" for topic in uncovered]
        lines.append("")

    return "\n".join(lines)


def write_reports(
    out_dir: pathlib.Path,
    result: GateResult,
    facts: ThoxFacts,
    *,
    grounding: str,
    uncovered: tuple[str, ...],
    answers: dict[str, str],
) -> tuple[pathlib.Path, pathlib.Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    report = result.to_dict()
    report["card_version"] = facts.version
    report["grounding"] = grounding
    report["uncovered_topics"] = list(uncovered)
    report["generated_at"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if facts.provenance:
        report["card_source"] = {
            "repo": facts.provenance.repo,
            "ref": facts.provenance.ref,
            "commit": facts.provenance.commit,
            "sha256": facts.provenance.sha256,
        }
    json_path = out_dir / "factuality-report.json"
    md_path = out_dir / "factuality-report.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(
        render_markdown(result, facts, grounding=grounding, uncovered=uncovered, answers=answers),
        encoding="utf-8",
    )
    return json_path, md_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="factuality_gate.py",
        description="Fail the build when a THOX model contradicts the canonical facts card.",
    )
    parser.add_argument("--model", required=True, help="Model ref (ollama tag, gguf path, HF id) or a label when using --transcript.")
    parser.add_argument("--backend", default="auto", choices=("auto", "ollama", "llama.cpp", "transformers"))
    parser.add_argument(
        "--grounding",
        default="none",
        choices=("none", "baked"),
        help="none (default) = plain house prompt, tests the weights. baked = facts block in the system prompt.",
    )
    parser.add_argument("--transcript", type=pathlib.Path, help="Score a recorded {id: answer} JSON instead of running a model.")
    parser.add_argument("--out", type=pathlib.Path, default=None, help=f"Report dir. Default {DEFAULT_OUT}/<model>/")
    parser.add_argument("--max-new-tokens", type=int, default=320)
    parser.add_argument("--temperature", type=float, default=0.0, help="Default 0.0 — the gate must be reproducible.")
    parser.add_argument("--max-hard-failures", type=int, default=0)
    parser.add_argument("--max-soft-failures", type=int, default=None, help="Default unlimited: omissions are reported, not blocking.")
    parser.add_argument("--min-score", type=float, default=0.0)
    parser.add_argument("--dump-answers", action="store_true", help="Write answers.json alongside the report.")
    parser.add_argument("--quiet", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_argparser().parse_args(argv)
    try:
        facts = load_facts()
    except FactsError as exc:
        print(f"[gate] {exc}", file=sys.stderr)
        return 2

    questions = build_questions(facts)
    uncovered = uncovered_topics(facts)
    policy = GatePolicy(
        max_hard_failures=args.max_hard_failures,
        max_soft_failures=args.max_soft_failures,
        min_score=args.min_score,
    )

    answers: dict[str, str] = {}

    try:
        if args.transcript is not None:
            recorded = load_transcript(args.transcript)
            missing = [q.id for q in questions if q.id not in recorded]
            if missing:
                # A silently-absent answer would score as an empty string and
                # look like a model failure rather than an incomplete run.
                print(
                    f"[gate] transcript is missing {len(missing)} answers: {', '.join(missing[:5])}"
                    + (" ..." if len(missing) > 5 else ""),
                    file=sys.stderr,
                )
                return 2

            def answer_for(prompt: str, _by_id={q.prompt: q.id for q in questions}) -> str:
                return recorded[_by_id[prompt]]

        else:
            system = build_system_prompt(facts, args.grounding)
            runner = make_model_runner(
                args.model,
                args.backend,
                system,
                max_new_tokens=args.max_new_tokens,
                temperature=args.temperature,
            )
            answer_for = runner

        def recording_answer_for(prompt: str, _by_id={q.prompt: q.id for q in questions}) -> str:
            text = answer_for(prompt)
            answers[_by_id[prompt]] = text
            return text

        if not args.quiet:
            print(
                f"[gate] model={args.model} questions={len(questions)} "
                f"grounding={args.grounding} card={facts.version}"
            )
        result = run_gate(args.model, questions, recording_answer_for, policy, verbose=not args.quiet)
    except GateError as exc:
        print(f"[gate] {exc}", file=sys.stderr)
        return 2

    safe_model = "".join(c if c.isalnum() or c in "._-" else "_" for c in args.model)
    out_dir = args.out or (DEFAULT_OUT / safe_model)
    try:
        json_path, md_path = write_reports(
            out_dir, result, facts, grounding=args.grounding, uncovered=uncovered, answers=answers
        )
        if args.dump_answers:
            (out_dir / "answers.json").write_text(
                json.dumps({"model": args.model, "answers": answers}, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
    except OSError as exc:
        print(f"[gate] cannot write report: {exc}", file=sys.stderr)
        return 2

    status = "PASS" if result.passed else "FAIL"
    print(
        f"[gate] {status} {args.model}: {result.passed_count}/{result.total} passed, "
        f"{result.hard_failures} hard, score {result.score}/5 -> {md_path}"
    )
    if uncovered and not args.quiet:
        print(f"[gate] coverage gap: no curated detector for {', '.join(uncovered)}", file=sys.stderr)
    return 0 if result.passed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("[gate] interrupted", file=sys.stderr)
        sys.exit(2)
