#!/usr/bin/env python3
"""Gate49 HF-Job entrypoint: the fleet 49-question factuality gate on HF infra.

Runs INSIDE an HF Job after a flagship training job completes. The plane's
built-in gate (gate.py, 12 prompts) authorises nothing by itself; this is the
publishing authority from GATE49.md.

Why it looks the way it does
----------------------------
The canonical gate, ``factuality_gate49.py`` in this bundle (vendored from
``scripts/factuality_gate.py`` in ttracx/thoxllm-factory), gets its model
answers through ``eval/run_eval.py`` backends. Those backends cannot load a
LoRA adapter, and the eval harness is not vendored. So this entrypoint does
the generation itself, in the only shape that measures exactly the artifact
that would ship:

  1. load base + adapter with transformers, ``merge_and_unload()``, save the
     merged model to a temp dir and reload it standalone (the merged dir is
     the pre-GGUF artifact; if it does not load, nothing downstream matters);
  2. answer all 49 card-derived questions greedily, weights only (system =
     the facts package house prompt, NO facts block — the Wave A/B
     baselines were measured weights-only through Ollama, and comparability
     is the point), ``enable_thinking=False`` for Qwen3/Qwen3.5 so the
     thinking channel cannot hide answers the way Ollama 0.40.11 did;
  3. score the recorded transcript with the vendored gate itself
     (``--transcript`` mode), so the scorer that produced the baselines is
     the scorer that produces these numbers — not a reimplementation;
  4. upload the gate report to the adapter repo as ``thox_gate49.json``
     (enriched with the raw answers, which the gate's own report omits),
     stamp the verdict banner on the model card, print passed/49 + mean.

Exit code is 0 even when the gate verdict is FAIL — a FAIL is a successful
measurement, not a crash (plane convention, gate.py). Exit code is non-zero
only when the gate could not run at all.

Inputs (either route; CLI wins):
  --base-model / --adapter-repo [/ --output-repo, defaults to adapter repo]
  env THOX_SPEC = {"id": ..., "base_model": ..., "output_repo": ...}
Secret: HF_TOKEN (the adapter repos are private).
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile

BUNDLE_DIR = pathlib.Path(__file__).resolve().parent
if str(BUNDLE_DIR) not in sys.path:
    sys.path.insert(0, str(BUNDLE_DIR))

GATE_SCRIPT = BUNDLE_DIR / "factuality_gate49.py"
SCORECARD_NAME = "thox_gate49.json"
MAX_NEW_TOKENS = 320  # matches the plane gate and the historical gate runs

_THINKING_MODEL_TYPES = {"qwen3", "qwen3_5", "qwen3_moe", "qwen3_5_moe"}


# ---------------------------------------------------------------------------
# Spec / args
# ---------------------------------------------------------------------------


def resolve_spec(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="run_gate49_job.py")
    parser.add_argument("--base-model", default=None)
    parser.add_argument("--adapter-repo", default=None)
    parser.add_argument("--output-repo", default=None,
                        help="Repo that receives thox_gate49.json. Default: the adapter repo.")
    parser.add_argument("--out-dir", type=pathlib.Path, default=None)
    parser.add_argument("--max-new-tokens", type=int, default=MAX_NEW_TOKENS)
    args = parser.parse_args(argv)

    spec = {}
    if os.environ.get("THOX_SPEC"):
        spec = json.loads(os.environ["THOX_SPEC"])
    args.base_model = args.base_model or spec.get("base_model")
    args.adapter_repo = args.adapter_repo or spec.get("output_repo")
    args.output_repo = args.output_repo or args.adapter_repo
    if not args.base_model or not args.adapter_repo:
        parser.error("need a base model and an adapter repo (CLI flags or THOX_SPEC)")
    return args


# ---------------------------------------------------------------------------
# Model loading (shared with probe_flagship.py)
# ---------------------------------------------------------------------------


def load_tokenizer(source: str, token: str | None):
    """Plane-identical tokenizer load, including the gemma-4 config workaround."""
    from transformers import AutoTokenizer

    try:
        tok = AutoTokenizer.from_pretrained(source, token=token, trust_remote_code=True)
    except AttributeError as exc:
        if "'list' object has no attribute 'keys'" not in str(exc):
            raise
        tok = AutoTokenizer.from_pretrained(
            source, token=token, trust_remote_code=True, extra_special_tokens={}
        )
    if not getattr(tok, "chat_template", None):
        # Must match the template the adapter was trained with, or the gate
        # measures template mismatch instead of factuality (gate.py's rule).
        tok.chat_template = (
            "{% for m in messages %}"
            "{{ '<|im_start|>' + m['role'] + '\\n' + m['content'] + '<|im_end|>' + '\\n' }}"
            "{% endfor %}"
            "{% if add_generation_prompt %}{{ '<|im_start|>assistant\\n' }}{% endif %}"
        )
    return tok


def load_merged_model(base: str, adapter: str, token: str | None, workdir: pathlib.Path):
    """Load base + LoRA adapter, merge, save, reload standalone. Returns (model, tok).

    The reload is deliberate: the merged directory is the artifact that later
    gets GGUF-converted, so the gate measures the artifact, not the training
    stack's in-memory view of it.
    """
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM

    tok = load_tokenizer(base, token)
    model = AutoModelForCausalLM.from_pretrained(
        base, token=token, trust_remote_code=True,
        torch_dtype=torch.bfloat16, device_map={"": 0},
    )
    model = PeftModel.from_pretrained(model, adapter, token=token)
    model = model.merge_and_unload()
    merged_dir = workdir / "merged"
    model.save_pretrained(merged_dir)
    tok.save_pretrained(merged_dir)
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    merged = AutoModelForCausalLM.from_pretrained(
        merged_dir, trust_remote_code=True,
        torch_dtype=torch.bfloat16, device_map={"": 0},
    )
    merged.eval()
    tok = load_tokenizer(str(merged_dir), token)
    return merged, tok


def thinking_kwargs(model, base_hint: str) -> dict:
    """enable_thinking=False for Qwen3/Qwen3.5, nothing for anyone else.

    GATE49.md: generation must match the deployed thinking-off configuration
    the flagship decisions were made under. Other families' chat templates do
    not accept the kwarg, so it is passed only where the architecture is one
    of the thinking families.
    """
    model_type = str(getattr(getattr(model, "config", None), "model_type", "") or "")
    if model_type in _THINKING_MODEL_TYPES or "qwen3" in base_hint.lower():
        return {"enable_thinking": False}
    return {}


def generate_one(model, tok, system: str | None, user: str, *,
                 max_new_tokens: int = MAX_NEW_TOKENS, tools=None,
                 extra_template_kwargs: dict | None = None) -> tuple[str, int, bool]:
    """One greedy generation. Returns (text, n_new_tokens, hit_token_cap)."""
    import torch

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})

    template_kwargs = dict(extra_template_kwargs or {})
    if tools is not None:
        template_kwargs["tools"] = tools
    enc = tok.apply_chat_template(
        messages, add_generation_prompt=True, return_tensors="pt",
        return_dict=True, **template_kwargs,
    )
    enc = {k: v for k, v in enc.items() if k in ("input_ids", "attention_mask")}
    device = next(model.parameters()).device
    enc = {k: v.to(device) for k, v in enc.items()}
    prompt_len = enc["input_ids"].shape[-1]
    with torch.no_grad():
        out = model.generate(
            **enc, max_new_tokens=max_new_tokens, do_sample=False,
            pad_token_id=tok.pad_token_id or tok.eos_token_id,
        )
    new_tokens = out[0][prompt_len:]
    text = tok.decode(new_tokens, skip_special_tokens=True)
    return text, int(new_tokens.shape[-1]), int(new_tokens.shape[-1]) >= max_new_tokens


# ---------------------------------------------------------------------------
# Gate run
# ---------------------------------------------------------------------------


def run_gate49(argv: list[str] | None = None) -> int:
    args = resolve_spec(argv)
    token = os.environ.get("HF_TOKEN")
    out_dir = args.out_dir or pathlib.Path(tempfile.mkdtemp(prefix="gate49-out-"))
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[gate49] base={args.base_model} adapter={args.adapter_repo} "
          f"output={args.output_repo}", flush=True)

    from facts import build_questions, load_facts
    from facts.prompt import SYSTEM_THOX

    facts = load_facts()
    questions = build_questions(facts)
    print(f"[gate49] card={facts.version} questions={len(questions)}", flush=True)

    with tempfile.TemporaryDirectory(prefix="gate49-merged-") as tmp:
        model, tok = load_merged_model(
            args.base_model, args.adapter_repo, token, pathlib.Path(tmp)
        )
        extra = thinking_kwargs(model, args.base_model)
        transcript: dict[str, str] = {}
        for i, question in enumerate(questions, 1):
            answer, _, _ = generate_one(
                model, tok, SYSTEM_THOX, question.prompt,
                max_new_tokens=args.max_new_tokens, extra_template_kwargs=extra,
            )
            transcript[question.id] = answer
            print(f"[gate49] answered {i}/{len(questions)} {question.id}", flush=True)
        del model

    transcript_path = out_dir / "transcript.json"
    transcript_path.write_text(
        json.dumps(transcript, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    proc = subprocess.run(
        [sys.executable, str(GATE_SCRIPT),
         "--model", args.adapter_repo,
         "--transcript", str(transcript_path),
         "--out", str(out_dir),
         "--dump-answers", "--quiet"],
        capture_output=True, text=True,
    )
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode == 2:
        print("[gate49] the gate could not run (exit 2)", file=sys.stderr)
        return 2
    # returncode 0 (PASS) or 1 (FAIL) are both successful measurements.

    report_path = out_dir / "factuality-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    # The gate report's verdicts omit the raw answers; GATE49.md's output
    # spec for thox_gate49.json requires them, so enrich before upload.
    report["answers"] = transcript
    for verdict in report.get("verdicts", []):
        verdict["answer"] = transcript.get(verdict.get("id", ""), "")
    report["base_model"] = args.base_model
    report["adapter_repo"] = args.adapter_repo
    report["backend"] = "transformers (merged adapter, greedy, weights-only)"
    enriched_path = out_dir / SCORECARD_NAME
    enriched_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    from huggingface_hub import HfApi, ModelCard

    api = HfApi(token=token)
    api.upload_file(
        path_or_fileobj=str(enriched_path), path_in_repo=SCORECARD_NAME,
        repo_id=args.output_repo, repo_type="model",
        commit_message=(
            f"gate49: {report['passed_count']}/{report['total']} "
            f"({report['score']}/5, {report['hard_failures']} hard)"
        ),
    )
    print(f"[gate49] uploaded {SCORECARD_NAME} to {args.output_repo}", flush=True)

    verdict_word = "PASS" if report["passed"] else "FAIL"
    banner = (
        f"\n\n## THOX gate49: **{verdict_word}** "
        f"({report['passed_count']}/{report['total']}, score {report['score']}/5, "
        f"{report['hard_failures']} hard failures)\n\n"
        f"Fleet 49-question factuality gate (facts card {report.get('card_version')}), "
        f"weights-only, Transformers backend on the merged adapter. Full per-question "
        f"results in `{SCORECARD_NAME}`.\n"
        + ("This adapter clears the gate49 run. Promotion still requires beating its "
           "registered baseline (see GATE49.md).\n" if verdict_word == "PASS" else
           "**Do not promote or make public.** This adapter still fabricates or "
           "omits canonical THOX facts.\n")
    )
    try:
        card = ModelCard.load(args.output_repo, token=token)
        card.text = (card.text or "") + banner
    except Exception:
        card = ModelCard(f"# {args.output_repo}\n{banner}")
    card.push_to_hub(args.output_repo, token=token)
    print(f"[gate49] stamped {args.output_repo}", flush=True)

    print(f"[gate49] RESULT {report['passed_count']}/{report['total']} passed, "
          f"mean score {report['score']}/5, hard failures {report['hard_failures']}",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(run_gate49())
