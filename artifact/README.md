# Flagships for Every Device: The Wave C Training Program — v0.5.0 artifact bundle

Process v1.0 pack for the THOX Wave C flagship whitepaper, finalized
2026-11-04. Byline finalized under Tommy Xaypanya's ruling of
2026-11-04: the v0.4.2 authorship stands as published (Sadie Weaving,
author; Tommy Xaypanya, accountable human author), and the v0.4.2
authorship-and-accountability disclosure is retained verbatim in the
paper's front matter. The DOI of record is issued by this edition's
Zenodo deposit and is recorded in `CITATION.cff`, the THOX
research-publishing pipeline manifest, and `HANDOFF.md`.

## Contents

- `dist/` — the shipped trio:
  - `THOX_Wave_C_Flagship_Program_Whitepaper_v0.5.0.pdf` — the paper (56 pp, Template v1.0).
  - `THOX_Wave_C_Flagship_Program_Whitepaper_v0.5.0.html` — single-file HTML edition (embedded fonts and figures).
  - `WaveC_Demo_v0.5.0.html` — the GATE49 explorer demo; renders entirely client-side from the evidence data embedded in it.
- `exp/` — the evidence bundle:
  - `exp/results/summary.json` — **the single evidence source**: every headline figure in the paper, consolidated from the per-run reports, each with its source file's SHA-256.
  - `exp/results/` — the per-run GATE49 reports (program runs, Mini probes), `served-path/` (§8.6 measurements), `null-policy/` (§7 measurements), the legacy program summary, and the supplement's own manifest.
  - `exp/code/` — the gate49 scorer, flagship probe, runner, facts package, and grounding prompt the results were produced with.
  - `exp/registry/` — the model-registry snapshots the program ran against.
- `wp/` — the build: `build.py` (Template v1.0 layout), `build_demo.py`,
  `consolidate_summary.py` (builds summary.json from the per-run reports),
  `pdf.cjs` (PDF render), and `qa/` with the QA report, the numbers
  verification and blocker-sweep results, render metrics, screenshots, and
  the contact sheet. The identifier-scrub tooling and its raw logs are
  retained in the internal build tree only: they enumerate the internal
  identifiers they remove, so they are not part of the public bundle; the
  scrub's effect is verified by the tier-1 sweep result in `wp/qa/`.

## Edition note

v0.5.0 is a Process v1.0 reissue of the published v0.4.2 (2026-10-30):
content unchanged; layout moved to Research Paper Template v1.0; internal
host identifiers genericized to host classes in the paper text and in the
copies of the evidence files in this bundle (the public supplement on
the Hugging Face whitepapers dataset is untouched). The paper's own
§14 document control records the edition history, including this
reissue's v0.5.0 row.

## Verification

- Numbers: `wp/qa/verify_numbers.py` re-derives every headline figure
  from the per-run JSONs and checks the printed paper against them —
  56/56 PASS (`wp/qa/numbers-verification.json`).
- Blocker sweep: `wp/qa/sweep.json` — PASS, byline item finalized
  (see `wp/qa/QA-REPORT.md`).
