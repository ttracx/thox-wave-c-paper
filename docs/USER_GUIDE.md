# User Guide — Wave C Flagship Program Whitepaper (paper repository)

## What this repository is

This is the publication record for the THOX.ai Research whitepaper
**"Flagships for Every Device: The Wave C Training Program" v0.5.0
(public edition)**, DOI
[10.5281/zenodo.23969809](https://doi.org/10.5281/zenodo.23969809).
Author: Sadie Weaving (THOX.ai); accountable human author: Tommy
Xaypanya (THOX.ai, corresponding author). It holds the paper, its
interactive GATE49 explorer demo, and the evidence files every
printed number traces to. It does not hold the models; the four
flagships live in their own model repositories.

v0.5.0 is a Process v1.0 reissue of v0.4.2 (2026-10-30), content
unchanged: Template v1.0 layout, evidence consolidated into one
source, and internal host identifiers genericized to host classes.
The edition history is in the paper's §14 document control.

## Who it is for

- Readers evaluating the Wave C flagship program and its rulings.
- Reviewers who want to check a claim in the paper against its
  evidence file.
- THOX engineers tracing a promotion or hold ruling to its record.

## Reading the paper

Open `paper/THOX_Wave_C_Flagship_Program_Whitepaper_v0.5.0.pdf`, or
the identical-content single-file HTML edition
`paper/THOX_Wave_C_Flagship_Program_Whitepaper_v0.5.0.html`.
Structure: the slate defense (§3), the corpus (§4), the training
plane (§§5–6), the GATE49 evaluation design (§7), per-model results
(§8), the C.1/C.2 fix cycles (§9), limitations (§10), the provenance
and evidence register (§13), and document control (§14).

## Checking a number

Every headline figure traces to `artifact/exp/results/summary.json`,
the pack's single evidence source, which records the SHA-256 of each
per-run report it consolidates. The QA record of the independent
re-verification (56/56 PASS for this edition) is in
`artifact/wp/qa/`.

## Running the demo

Open `paper/WaveC_Demo_v0.5.0.html` in any browser. It renders all
27 recorded runs (program, null policy, served-path) entirely
client-side from the evidence data embedded in it; no network is
needed.

## Citing the paper

Use `CITATION.cff` or `paper.bib` at the repository root. The DOI of
record is 10.5281/zenodo.23969809.
