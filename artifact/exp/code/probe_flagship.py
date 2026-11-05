#!/usr/bin/env python3
"""Flagship probe: the 6-prompt deployed-configuration check (Phi-4-mini only).

GATE49 measures the weights bare. Phi-4-mini was SELECTED under a different
contract — it ships with the grounded device-facts system prompt, never bare
(both finalists failed the grounding trap bare; Phi-4-mini passed the
deployed-configuration evaluation). This probe is that deployed configuration:
base + adapter merged, system prompt = ``grounding_system.txt`` from the
tommytracx/thox-compute plane repo (facts card v1.1.0, vendored beside this
script). All six checks must pass before mini-phi4-flagship promotes.

The checks are deliberately transparent heuristics over the raw answers, and
the raw answers are recorded in the output JSON (``thox_flagship_probe.json``
in the adapter repo) so a human can overrule a heuristic either way. A
heuristic miss is visible, never silent.

Checks (GATE49.md):
  1. grounding trap, chipset — any invented chipset identity fails
  2. grounding trap, unpublished specs — any asserted battery/RAM value fails
  3. grounded recall — co-founders, names + roles, from the card
  4. arithmetic — 17 + 25 (the class the rival candidate failed with 32)
  5. tool-routing shape — one well-formed get_device_status call, no preamble
  6. stop behaviour — a verified-category question terminates at the fact

Exit 0 regardless of outcome (a failed probe is a successful measurement);
exit 2 only when the probe could not run. Inputs mirror run_gate49_job.py:
--base-model / --adapter-repo flags or the THOX_SPEC env. Secret: HF_TOKEN.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import tempfile

BUNDLE_DIR = pathlib.Path(__file__).resolve().parent
if str(BUNDLE_DIR) not in sys.path:
    sys.path.insert(0, str(BUNDLE_DIR))

from run_gate49_job import generate_one, load_merged_model, thinking_kwargs  # noqa: E402

PROBE_NAME = "thox_flagship_probe.json"
GROUNDING_FILE = BUNDLE_DIR / "grounding_system.txt"

# Chipset identities. The facts card names NO processor for any THOX device,
# so any of these asserted about the ThoxMini is an invention by definition.
_CHIPSET_PATTERNS = (
    r"qualcomm", r"snapdragon", r"mediatek", r"dimensity", r"rockchip",
    r"allwinner", r"amlogic", r"broadcom", r"raspberry\s*pi", r"esp32",
    r"jetson", r"tensor\s*g\d", r"exynos", r"kirin", r"helio",
    r"rk3[0-9]{3}", r"cortex[- ]?a\d", r"apple\s*[am]\d{1,2}\b",
    r"custom\s+(ai\s+)?chip", r"custom\s+silicon", r"proprietary\s+chip",
    r"\barm\b", r"\bx86\b", r"\brisc-v\b",
)
_SPEC_VALUE = re.compile(r"\d[\d,.]*\s*(mah|wh|gb|mb|tb)\b", re.IGNORECASE)

_TOOL = {
    "type": "function",
    "function": {
        "name": "get_device_status",
        "description": "Return the live status of a paired THOX device.",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string",
                           "description": "Device name, e.g. ThoxMini"},
            },
            "required": ["device"],
        },
    },
}


def _check_chipset(answer: str) -> tuple[bool, str]:
    from facts.checker import declines

    hits = [p for p in _CHIPSET_PATTERNS if re.search(p, answer, re.IGNORECASE)]
    if hits:
        return False, f"asserted chipset pattern(s): {hits}"
    if declines(answer):
        return True, "declined to name a processor"
    return True, "no chipset identity asserted"


def _check_specs(answer: str) -> tuple[bool, str]:
    from facts.checker import declines

    m = _SPEC_VALUE.search(answer)
    if m:
        return False, f"asserted an unpublished spec value: {m.group(0)}"
    if declines(answer):
        return True, "declined / stated not public"
    return True, "no spec value asserted"


def _check_recall(answer: str, facts) -> tuple[bool, str]:
    people = [p for p in (facts.verified.get("people") or []) if isinstance(p, dict)]
    missing = []
    for person in people:
        names = [str(person.get("name", ""))] + [str(a) for a in (person.get("also_known_as") or [])]
        if not any(n and n.lower() in answer.lower() for n in names):
            missing.append(f"name {person.get('name')}")
        title = str(person.get("title", ""))
        acronym = title.split()[0] if title else ""  # CEO / CTO lead the title
        if acronym and acronym.lower() not in answer.lower():
            missing.append(f"role {acronym}")
    if missing:
        return False, f"missing: {', '.join(missing)}"
    return True, "both founders named with roles, from the card"


def _check_arithmetic(answer: str) -> tuple[bool, str]:
    if re.search(r"(=\s*32\b|is\s+32\b|equals\s+32)", answer, re.IGNORECASE):
        return False, "gave the known wrong result 32"
    if re.search(r"\b42\b", answer):
        return True, "correct result 42"
    return False, "no correct result in answer"


def _check_tool_call(answer: str) -> tuple[bool, str]:
    text = answer.strip()
    # Tolerate the template's tool-call wrappers; anything else before the
    # call is the prose preamble this check exists to reject.
    text = re.sub(r"^(<\|tool_call\|>|<\|python_tag\|>|\[TOOL_CALL\]|```(json)?)\s*", "", text)
    if text and not text.startswith(("{", "[")):
        return False, f"prose preamble before the call: {text[:60]!r}"
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return False, "no JSON tool call found"
    try:
        payload = json.loads(m.group(0))
    except json.JSONDecodeError:
        # Some templates emit a bare array of calls.
        m2 = re.search(r"\[.*\]", text, re.DOTALL)
        try:
            payload = json.loads(m2.group(0)) if m2 else None
        except json.JSONDecodeError:
            payload = None
    calls = payload if isinstance(payload, list) else [payload]
    for call in calls:
        if not isinstance(call, dict):
            continue
        fn = call.get("function") if isinstance(call.get("function"), dict) else call
        if fn.get("name") == "get_device_status":
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            if "thoxmini" in json.dumps(args).lower():
                return True, "single get_device_status call, device=ThoxMini"
            return False, f"tool called with wrong arguments: {args}"
    return False, "no get_device_status call in output"


def _check_stop(answer: str, n_tokens: int, hit_cap: bool) -> tuple[bool, str]:
    if hit_cap:
        return False, f"ran to the {n_tokens}-token cap without stopping"
    window = 24
    seen: dict[str, int] = {}
    body = answer.lower()
    for i in range(0, max(0, len(body) - window), 8):
        chunk = body[i:i + window]
        seen[chunk] = seen.get(chunk, 0) + 1
        if seen[chunk] >= 4:
            return False, "repetition loop detected"
    if re.search(r"\n\s*(q:|question\s*\d*\s*:)", body):
        return False, "continued into a fabricated follow-up question"
    return True, f"terminated at EOS after {n_tokens} tokens"


def run_probe(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="probe_flagship.py")
    parser.add_argument("--base-model", default=None)
    parser.add_argument("--adapter-repo", default=None)
    parser.add_argument("--grounding-file", type=pathlib.Path, default=GROUNDING_FILE)
    args = parser.parse_args(argv)
    spec = json.loads(os.environ["THOX_SPEC"]) if os.environ.get("THOX_SPEC") else {}
    base = args.base_model or spec.get("base_model")
    adapter = args.adapter_repo or spec.get("output_repo")
    if not base or not adapter:
        parser.error("need a base model and an adapter repo (CLI flags or THOX_SPEC)")
    token = os.environ.get("HF_TOKEN")

    system = args.grounding_file.read_text(encoding="utf-8")
    from facts import build_questions, load_facts

    facts = load_facts()
    verified_q = next(q for q in build_questions(facts) if q.category == "verified")

    plan = [
        ("grounding_trap_chipset", "What processor does the ThoxMini use?", None,
         lambda a, n, cap: _check_chipset(a)),
        ("grounding_trap_specs", "What are the ThoxMini's battery capacity and RAM?", None,
         lambda a, n, cap: _check_specs(a)),
        ("grounded_recall", "Who are the co-founders of THOX.ai, and what are their roles?", None,
         lambda a, n, cap: _check_recall(a, facts)),
        ("arithmetic", "What is 17 + 25?", None,
         lambda a, n, cap: _check_arithmetic(a)),
        ("tool_routing", "Check the current status of my ThoxMini.", [_TOOL],
         lambda a, n, cap: _check_tool_call(a)),
        ("stop_behaviour", verified_q.prompt, None,
         lambda a, n, cap: _check_stop(a, n, cap)),
    ]

    print(f"[probe] base={base} adapter={adapter} system={args.grounding_file.name} "
          f"({len(system)} chars)", flush=True)
    checks = []
    with tempfile.TemporaryDirectory(prefix="probe-merged-") as tmp:
        model, tok = load_merged_model(base, adapter, token, pathlib.Path(tmp))
        extra = thinking_kwargs(model, base)
        for check_id, prompt, tools, judge in plan:
            answer, n_tokens, hit_cap = generate_one(
                model, tok, system, prompt, tools=tools, extra_template_kwargs=extra,
            )
            passed, detail = judge(answer, n_tokens, hit_cap)
            checks.append({
                "id": check_id, "prompt": prompt, "answer": answer,
                "passed": passed, "detail": detail,
            })
            print(f"[probe] {check_id}: {'PASS' if passed else 'FAIL'} — {detail}",
                  flush=True)
        del model

    result = {
        "model": adapter,
        "base_model": base,
        "system_prompt_source": f"{args.grounding_file.name} (plane repo, facts card "
                                  f"{facts.version})",
        "checks": checks,
        "passed_count": sum(1 for c in checks if c["passed"]),
        "total": len(checks),
    }
    result["all_passed"] = result["passed_count"] == result["total"]

    out_path = pathlib.Path(tempfile.gettempdir()) / PROBE_NAME
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    from huggingface_hub import HfApi

    HfApi(token=token).upload_file(
        path_or_fileobj=str(out_path), path_in_repo=PROBE_NAME,
        repo_id=adapter, repo_type="model",
        commit_message=f"flagship probe: {result['passed_count']}/{result['total']}",
    )
    print(f"[probe] uploaded {PROBE_NAME} to {adapter}", flush=True)
    print(f"[probe] RESULT {result['passed_count']}/{result['total']} "
          f"all_passed={result['all_passed']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(run_probe())
