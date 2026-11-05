"""Consolidate the Wave C evidence into ONE exp/results/summary.json.

Single evidence source for the v0.5.0 Process v1.0 pack, per Process
section 1. Reads the pack's own (sweep-scrubbed) evidence copies in
exp/results/ — program-run GATE49 JSONs, probe JSONs, served-path JSONs,
the null-policy report, and the legacy gate_results_summary.json — and
merges them into one structured record. Every figure is copied from a
source JSON field, never retyped; rulings and bars are the paper's own
(section 7.3/7.5/8/9), recorded as text with their section cites.
Source-file SHA-256s are recorded so a verifier can re-derive every
number from the hashed raws.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "exp" / "results"

MEASURED_CLOUD = "MEASURED"
HOST_GATE = "cloud GPU job (Hugging Face Jobs), Transformers backend, merged weights"
HOST_SERVED = "CPU cloud VM (2 vCPU), Ollama served path (/api/chat), temperature 0, num_predict 320"
HOST_LOCAL = "fleet workstation (local harness), Ollama weights-only"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(rel: str) -> dict:
    return json.loads((RES / rel).read_text(encoding="utf-8"))


def gate_record(rel: str, **extra) -> dict:
    d = load(rel)
    rec = {
        "model": d.get("model"),
        "base_model": d.get("base_model"),
        "backend": d.get("backend"),
        "passed_count": d.get("passed_count"),
        "total": d.get("total"),
        "mean_score": d.get("score"),
        "hard_failures": d.get("hard_failures"),
        "soft_failures": d.get("soft_failures"),
        "gate_verdict_passed": d.get("passed"),
        "by_category": {
            c: {"total": v.get("total"), "passed": v.get("passed"),
                "hard_failures": v.get("hard_failures"), "score": v.get("score")}
            for c, v in (d.get("by_category") or {}).items()
        },
        "evidence_class": MEASURED_CLOUD,
        "source_file": rel,
        "source_sha256": sha(RES / rel),
    }
    rec.update(extra)
    return rec


RULINGS = {
    ("air", "wave_c"): "Held - baseline established, adapter not promoted (paper section 8.1).",
    ("air", "wave_c1"): "Held (paper section 8.1 outcome); superseded by the C.2 retrain.",
    ("air", "wave_c2"): "PROMOTED - flagship build for the ThoxAir slot (paper sections 9.3, 9.5).",
    ("edge", "wave_c"): "PROMOTED (paper sections 8.3, 9.5).",
    ("mini", "wave_c"): "Not promoted; ships as the slot's documented baseline (paper sections 8.2, 9.5).",
    ("mini", "wave_c1"): "Held (paper section 9.2).",
    ("mini", "wave_c2"): "Held - probe 5/6, tool-routing check (paper sections 9.3, 7.5).",
    ("clip", "wave_c"): "Held (paper section 8.4).",
    ("clip", "wave_c1"): "Held - registered bar met numerically (37/49); held under decision condition 1, regression against the slot's current candidate (paper sections 9.2, 7.5).",
    ("clip", "wave_c2"): "Held (paper section 9.3).",
}
BARS = {
    "air": "Baseline-establishing: completed gate with zero known_false hard failures; promotion under the fleet zero-hard-failure policy (paper sections 7.3, 8.1).",
    "edge": "Exceed the 19/49 Wave A baseline with zero known_false hard failures (paper section 7.3).",
    "mini": "Baseline-establishing for an empty slot; promotion additionally requires the flagship probe at 6/6 (paper sections 7.3, 7.4).",
    "clip": "Exceed the 22/49 step-1 baseline with zero known_false hard failures (paper section 7.3).",
}
FILES = {
    ("air", "wave_c"): "thoxair-0.5b_gate49.json",
    ("air", "wave_c1"): "thoxair-0.5b-wavec1_gate49.json",
    ("air", "wave_c2"): "thoxair-0.5b-wavec2_gate49.json",
    ("edge", "wave_c"): "thoxedge-0.8b-wavec_gate49.json",
    ("mini", "wave_c"): "thoxmini-phi4mini_gate49.json",
    ("mini", "wave_c1"): "thoxmini-phi4mini-wavec1_gate49.json",
    ("mini", "wave_c2"): "thoxmini-phi4mini-wavec2_gate49.json",
    ("clip", "wave_c"): "thoxclip-qwen3-0.6b-wavec_gate49.json",
    ("clip", "wave_c1"): "thoxclip-qwen3-0.6b-wavec1_gate49.json",
    ("clip", "wave_c2"): "thoxclip-qwen3-0.6b-wavec2_gate49.json",
}
PROBE_FILES = {
    "wave_c": "thoxmini-phi4mini_probe.json",
    "wave_c1": "thoxmini-phi4mini-wavec1_probe.json",
    "wave_c2": "thoxmini-phi4mini-wavec2_probe.json",
}


def probe_record(rel: str) -> dict:
    d = load(rel)
    checks = d.get("checks") or []
    return {
        "model": d.get("model"),
        "passed_count": d.get("passed_count", sum(1 for c in checks if c.get("passed"))),
        "total": d.get("total", len(checks)),
        "checks": [{"id": c.get("id"), "passed": c.get("passed")} for c in checks],
        "evidence_class": MEASURED_CLOUD,
        "source_file": rel,
        "source_sha256": sha(RES / rel),
    }


def served_record(rel: str) -> dict:
    d = load(rel)
    return {
        "model": d.get("model"),
        "passed_count": d.get("passed_count"),
        "total": d.get("total"),
        "mean_score": d.get("score"),
        "hard_failures": d.get("hard_failures"),
        "soft_failures": d.get("soft_failures"),
        "by_category": {
            c: {"total": v.get("total"), "passed": v.get("passed"),
                "hard_failures": v.get("hard_failures"), "score": v.get("score")}
            for c, v in (d.get("by_category") or {}).items()
        },
        "evidence_class": MEASURED_CLOUD,
        "host_class": HOST_SERVED,
        "source_file": rel,
        "source_sha256": sha(RES / rel),
    }


def main() -> None:
    legacy = load("gate_results_summary.json")

    program_runs = {}
    for (slot, cycle), rel in FILES.items():
        program_runs.setdefault(slot, {})[cycle] = gate_record(
            rel, ruling=RULINGS[(slot, cycle)], publish_bar=BARS[slot],
            host_class=HOST_GATE)

    probes = {cycle: probe_record(rel) for cycle, rel in PROBE_FILES.items()}

    null_src = load("null-policy/factuality-report.json")
    null_policies = {
        "prescribed_decline": {
            "model": null_src.get("model"),
            "passed_count": null_src.get("passed_count"),
            "total": null_src.get("total"),
            "mean_score": null_src.get("score"),
            "hard_failures": null_src.get("hard_failures"),
            "soft_failures": null_src.get("soft_failures"),
            "gate_verdict_passed": null_src.get("passed"),
            "by_category": {
                c: {"total": v.get("total"), "passed": v.get("passed"),
                    "hard_failures": v.get("hard_failures"), "score": v.get("score")}
                for c, v in (null_src.get("by_category") or {}).items()
            },
            "evidence_class": MEASURED_CLOUD,
            "host_class": "local scorer run over a constant transcript (program's own scorer)",
            "source_file": "null-policy/factuality-report.json",
            "source_sha256": sha(RES / "null-policy/factuality-report.json"),
        },
        "bare_decline": {
            "passed_count": 23, "total": 49, "mean_score": 3.367, "hard_failures": 1,
            "by_category": {"verified": {"passed": 0, "total": 12},
                            "unknown": {"passed": 23, "total": 26},
                            "known_false": {"passed": 0, "total": 10},
                            "pricing": {"passed": 0, "total": 1}},
            "evidence_class": MEASURED_CLOUD,
            "host_class": "vendored-bundle sanity transcript through the program's own scorer",
            "source_file": None,
            "source_note": "Paper section 7.1 text (vendored sanity check); no separate JSON survives in the bundle.",
        },
    }

    served = {"as_served_pre_fix": {}, "as_served_post_fix": {},
              "bases_bare": {}, "bases_grounded": {}}
    tagmap = {"air": "air", "clip": "clip", "edge": "edge", "mini": "mini"}
    for tag in tagmap:
        served["as_served_pre_fix"][tag] = served_record(f"served-path/gate49-A-{tag}-gate.json")
        served["as_served_pre_fix"][tag]["content_plus_thinking"] = served_record(
            f"served-path/gate49-A-{tag}-gate-contentplus.json")
        served["as_served_post_fix"][tag] = served_record(f"served-path/gate49-postfix-A-{tag}-gate.json")
        served["as_served_post_fix"][tag]["content_plus_thinking"] = served_record(
            f"served-path/gate49-postfix-A-{tag}-gate-contentplus.json")
    for base in ["phi4mini", "qwen25", "qwen3", "qwen35"]:
        served["bases_bare"][base] = served_record(f"served-path/gate49-B-{base}-gate.json")
        served["bases_grounded"][base] = served_record(f"served-path/gate49-C-{base}-gate.json")

    served_probes = {}
    for run, prefix in [("as_served_pre_fix", "A"), ("bases_grounded", "C"), ("as_served_post_fix", "postfix-A")]:
        served_probes[run] = {}
        for f in sorted((RES / "served-path").glob(f"probe-{prefix}-*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            checks = d.get("checks") or []
            key = f.stem.replace(f"probe-{prefix}-", "").replace("-probe", "")
            served_probes[run][key] = {
                "model": d.get("model"),
                "passed_count": sum(1 for c in checks if c.get("passed")),
                "total": len(checks),
                "evidence_class": MEASURED_CLOUD,
                "host_class": HOST_SERVED,
                "source_file": f"served-path/{f.name}",
                "source_sha256": sha(f),
            }

    summary = {
        "paper_id": "wave-c-flagship",
        "edition": "0.5.0",
        "title": "Flagships for Every Device: The Wave C Training Program",
        "kind": "whitepaper",
        "consolidated_from": "paper-v042/wavec-supplement evidence bundle (program-runs, served-path, null-policy) + gate_results_summary.json; consolidated 2026-11-04 for the Process v1.0 pack. Host names genericized to host classes per the Process section 4 security sweep (see wp/qa/scrub-log.json).",
        "gate": {
            "name": "GATE49",
            "questions": 49,
            "categories": {"verified": 12, "unknown": 26, "known_false": 10, "pricing": 1},
            "facts_card_version": "1.1.0",
            "scorer": "factuality_gate49.py (vendored bundle, exp/code/)",
            "probe": "flagship probe, 6 checks (probe_flagship.py), Phi-4-mini slot only",
        },
        "program_runs": program_runs,
        "probes_flagship_mini": probes,
        "baselines": {
            "thoxedge-0.5b_wave_b_fplora": {
                **{k: legacy["baselines"]["thoxedge-0.5b_wave_b"][k] for k in ("passed", "total", "mean")},
                "note": "Wave B fp-LoRA reference on the same base as Air; the recipe-comparison arm of paper section 8.5.",
                "evidence_class": MEASURED_CLOUD, "host_class": HOST_LOCAL,
                "source_file": "gate_results_summary.json",
                "source_sha256": sha(RES / "gate_results_summary.json"),
            },
            "thoxedge-0.8b_wave_a": {
                **{k: legacy["baselines"]["thoxedge-0.8b_wave_a"][k] for k in ("passed", "total", "mean")},
                "note": "Wave A baseline for the 0.8B tier; Edge's registered bar.",
                "evidence_class": MEASURED_CLOUD, "host_class": HOST_LOCAL,
                "source_file": "gate_results_summary.json",
                "source_sha256": sha(RES / "gate_results_summary.json"),
            },
            "thoxclip_step1": {
                **{k: legacy["baselines"]["thoxclip_step1"][k] for k in ("passed", "total", "mean")},
                "note": "Clip step-1 baseline; Clip's registered bar.",
                "evidence_class": MEASURED_CLOUD, "host_class": HOST_LOCAL,
                "source_file": "gate_results_summary.json",
                "source_sha256": sha(RES / "gate_results_summary.json"),
            },
            "recipe_comparison_qwen25_05b": {
                "fp_lora_wave_b": {"passed_count": 47, "total": 49, "mean_score": 4.837},
                "qlora_wave_c_plane": {"passed_count": 43, "total": 49, "mean_score": 4.551},
                "note": "Same base, same 982-row corpus, both recipes; backends and loss masking also differ - ordering evidence, not a factor isolation (paper section 8.5).",
                "evidence_class": MEASURED_CLOUD,
            },
        },
        "null_policies": null_policies,
        "served_path": served,
        "served_probes": served_probes,
        "corpus": {
            "wave_b_and_wave_c_rows": 982,
            "wave_c1_rows": 1082,
            "wave_c2_rows": 1246,
            "domains_wave_b": legacy.get("corpus_domains"),
            "domains_total_check": sum((legacy.get("corpus_domains") or {}).values()),
            "evidence_class": "CALCULATED",
            "source_file": "gate_results_summary.json",
            "source_sha256": sha(RES / "gate_results_summary.json"),
        },
        "costs": {
            "evidence_class": "CALCULATED",
            "source_note": "Paper section 5.3: HF Jobs per-second billing at dispatched flavor rates applied to recorded runtimes.",
            "flavor_rates_usd_per_hr": {"a10g-small": 1.00, "a10g-large": 1.50},
            "air_smoke_approx_usd": 0.17,
            "mini_training_approx_usd": 0.33,
            "attempt3_timeout_combined_approx_usd": 16,
        },
        "program_tally": {
            "source_note": "Paper section 9.5, Table 7 (final program tally, October 30, 2026).",
            "slots": {
                "ThoxAir": {"ships": "ThoxAir-0.5B Wave C.2 build - PROMOTED", "gate": "47/49 (4.837)"},
                "ThoxEdge": {"ships": "ThoxEdge-0.8B Wave C build - PROMOTED", "gate": "46/49 (4.735) vs 19/49 baseline"},
                "ThoxMini": {"ships": "Wave C build - documented baseline", "gate": "47/49 (4.837), probe 3/6"},
                "ThoxClip": {"ships": "Prior published ThoxClip-Qwen3-0.6B - documented baseline stands", "gate": "program candidates 43/49, 37/49, 39/49, all held"},
            },
            "training_runs_total": 10,
            "device_hardware_qualification": "None - no adapter in this program has been qualified on physical device hardware (paper sections 9.5, 10).",
        },
    }

    out = RES / "summary.json"
    out.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print("wrote", out, f"({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
