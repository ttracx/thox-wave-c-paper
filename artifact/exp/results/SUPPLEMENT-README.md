# Wave C Supplement — Reproducibility package for v0.4.2

Supplement to *Flagships for Every Device: The Wave C Training Program*, Technical
Whitepaper v0.4.2 (THOX.ai, October 30, 2026), published in the dataset
`Thox-ai/thox-whitepapers` under the `wavec-supplement/` prefix.

## Contents

- `gate49/` — the exact evaluation instrument that produced every GATE49 number in
  the paper: the vendored bundle from the THOX compute plane (`factuality_gate49.py`,
  the `facts` package, facts card v1.1.0 at `facts/data/thox_facts.json`,
  `grounding_system.txt` in its corrected form, `probe_flagship.py`,
  `run_gate49_job.py`, and `VENDOR.md`, which records the bundle's provenance,
  the one-line scorer deviation, both null-policy measurements, and the
  grounding-prompt correction of October 30, 2026).
- `program-runs/` — the per-run gate and probe reports for every Wave C, C.1, and
  C.2 run (the same files the gate jobs wrote to the adapter repositories), plus
  `gate_results_summary.json`.
- `served-path/` — the served-path measurement record of §8.6: `RESULTS.md`
  (protocol, per-run sections, and the POST-FIX section) and all gate/probe JSONs —
  Run A (shipped tags as served, pre-fix), Runs B/C (bare and grounded base-model
  baselines), and the post-fix re-gate (`gate49-postfix-*`, `probe-postfix-*`).
  `-contentplus` files are the thinking-surfaced diagnostics.
- `null-policy/` — the constant-abstainer (prescribed-decline) run through the
  program's own scorer: transcript, answers, and factuality report
  (25/49, mean 3.531/5, zero hard failures, verdict PASS).
- `registry/` — the launch registry material the runs were dispatched from
  (`jobs-flagship.yaml`, `registry-merged.yaml`).
- `MANIFEST.sha256` — SHA-256 for every file in this supplement except the
  manifest itself.

## What this does and does not make reproducible

Every *score* in the paper can be re-derived: the gate package is complete and
the per-run reports are included. Re-running the *training* requires the corpora,
which remain in the private dataset repository `Thox-ai/thox-factory-sft-v5`;
their SHA-256 hashes, composition, and changelogs are printed in the paper
(§4, Appendix A). No training seed is recorded in any registry entry or job
record; decoding for gate and probe was greedy, max 320 new tokens. Bit-exact
reproduction is not claimed. Wave A/B per-question gate outputs were not retained
on the run hosts and are not in this supplement (recorded in that program's
supplement).
