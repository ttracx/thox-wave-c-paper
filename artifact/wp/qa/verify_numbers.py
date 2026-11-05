"""Non-producer numbers verification for the Wave C v0.5.0 pack.

Independent of the build: re-derives every headline figure from the
per-run evidence JSONs (counting verdicts, recomputing means and
category splits), compares them to exp/results/summary.json, checks
summary.json's recorded source hashes against the files on disk, and
then checks that the figures the paper prints (in the built PDF text
and the shipped HTML) match the re-derived values. Exit 0 only if all
checks pass. Writes wp/qa/numbers-verification.json.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "exp" / "results"
DIST = ROOT / "dist"
PDF = DIST / "THOX_Wave_C_Flagship_Program_Whitepaper_v0.5.0.pdf"
HTMLF = DIST / "THOX_Wave_C_Flagship_Program_Whitepaper_v0.5.0.html"

checks: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append({"check": name, "pass": bool(ok), "detail": detail})


def load(rel: str) -> dict:
    return json.loads((RES / rel).read_text(encoding="utf-8"))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


S = load("summary.json")

# --- 1. Re-derive program runs from verdicts -------------------------------
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
for (slot, cyc), rel in FILES.items():
    d = load(rel)
    vs = d["verdicts"]
    passed = sum(1 for v in vs if v["passed"])
    mean = round(sum(v["score"] for v in vs) / len(vs), 3)
    hard = sum(1 for v in vs if v["hard_failure"])
    rec = S["program_runs"][slot][cyc]
    ok = (passed == rec["passed_count"] == d["passed_count"]
          and abs(mean - rec["mean_score"]) < 0.0015
          and hard == rec["hard_failures"] == d["hard_failures"]
          and sha(RES / rel) == rec["source_sha256"])
    cats_ok = True
    for cat, crec in rec["by_category"].items():
        cv = [v for v in vs if v["category"] == cat]
        if not (sum(1 for v in cv if v["passed"]) == crec["passed"]
                and sum(1 for v in cv if v["hard_failure"]) == crec["hard_failures"]
                and len(cv) == crec["total"]):
            cats_ok = False
    check(f"program {slot}/{cyc} re-derived", ok and cats_ok,
          f"passed {passed}/49 mean {mean} hard {hard}; summary {rec['passed_count']}/{rec['mean_score']}/{rec['hard_failures']}")

# --- 2. Probes ---------------------------------------------------------------
for cyc, rel in [("wave_c", "thoxmini-phi4mini_probe.json"),
                 ("wave_c1", "thoxmini-phi4mini-wavec1_probe.json"),
                 ("wave_c2", "thoxmini-phi4mini-wavec2_probe.json")]:
    d = load(rel)
    n = sum(1 for c in d["checks"] if c["passed"])
    rec = S["probes_flagship_mini"][cyc]
    check(f"probe mini/{cyc}", n == rec["passed_count"] == d["passed_count"] and sha(RES / rel) == rec["source_sha256"],
          f"{n}/6")

# --- 3. Null policy ------------------------------------------------------------
nd = load("null-policy/factuality-report.json")
nvs = nd["verdicts"]
npassed = sum(1 for v in nvs if v["passed"])
nmean = round(sum(v["score"] for v in nvs) / len(nvs), 3)
rec = S["null_policies"]["prescribed_decline"]
check("null policy re-derived", npassed == rec["passed_count"] == 25 and abs(nmean - rec["mean_score"]) < 0.0015
      and sha(RES / "null-policy/factuality-report.json") == rec["source_sha256"],
      f"{npassed}/49 mean {nmean}")

# --- 4. Served path --------------------------------------------------------------
for group, pat in [("as_served_pre_fix", "gate49-A-{}-gate.json"),
                   ("as_served_post_fix", "gate49-postfix-A-{}-gate.json"),
                   ("bases_bare", "gate49-B-{}-gate.json"),
                   ("bases_grounded", "gate49-C-{}-gate.json")]:
    for tag, rec in S["served_path"][group].items():
        rel = f"served-path/{pat.format(tag)}"
        d = load(rel)
        check(f"served {group}/{tag}", d["passed_count"] == rec["passed_count"]
              and abs(d["score"] - rec["mean_score"]) < 0.001
              and sha(RES / rel) == rec["source_sha256"], f"{rec['passed_count']}/49")

# --- 5. Corpus -------------------------------------------------------------------
legacy = load("gate_results_summary.json")
check("corpus domains sum to 982", sum(legacy["corpus_domains"].values()) == 982 == S["corpus"]["domains_total_check"],
      str(legacy["corpus_domains"]))

# --- 6. Paper-printed figures vs summary -----------------------------------------
pdf_text = subprocess.run(["pdftotext", str(PDF), "-"], capture_output=True, text=True).stdout
html_text = re.sub(r"<[^>]+>", " ", HTMLF.read_text(encoding="utf-8"))
html_text = re.sub(r"data:[^ ]+", " ", html_text)


def fmt_mean(x: float) -> str:
    return f"{x:.3f}"


needles = []
for slot, runs in S["program_runs"].items():
    for cyc, r in runs.items():
        needles.append((f"{slot}/{cyc} total", f"{r['passed_count']}/49"))
        needles.append((f"{slot}/{cyc} mean", fmt_mean(r["mean_score"])))
for group in ("as_served_pre_fix", "as_served_post_fix"):
    for tag, r in S["served_path"][group].items():
        needles.append((f"served {group}/{tag}", f"{r['passed_count']}/49"))
needles += [("null prescribed", "25/49"), ("null bare", "23/49"),
            ("corpus wave C", "982"), ("corpus C.1", "1,082"), ("corpus C.2", "1,246"),
            ("edge contentplus", "35/49"), ("attempt3 cost", "$16")]
seen = {}
for name, needle in needles:
    seen.setdefault(needle, []).append(name)
for needle, names in seen.items():
    if "/" not in needle and needle.replace(".", "").isdigit():
        # means: the paper prints some at 2dp (4.49) and tables at 3dp (4.490);
        # either rendering of the same value passes.
        forms = {needle, needle.rstrip("0").rstrip(".") if "." in needle else needle}
        ok = any(f in pdf_text for f in forms) and any(f in html_text for f in forms)
        check(f"printed figure {needle!r}", ok, "for " + ", ".join(sorted(set(names))[:3]))
    else:
        check(f"printed figure {needle!r}", needle in pdf_text and needle in html_text,
              "for " + ", ".join(sorted(set(names))[:3]))

failed = [c for c in checks if not c["pass"]]
out = {"total": len(checks), "passed": len(checks) - len(failed), "failed": failed, "checks": checks}
(ROOT / "wp" / "qa" / "numbers-verification.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(f"numbers verification: {out['passed']}/{out['total']} PASS")
for f in failed:
    print("FAIL:", f["check"], f["detail"])
sys.exit(1 if failed else 0)
