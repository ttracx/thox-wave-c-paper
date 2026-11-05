# QA report — Wave C Flagship Program Whitepaper v0.5.0 (staged pack)

Build date: 2026-11-04. Builder: Sadie Weaving lane (Process v1.0 pack build).
Status: **STAGED ONLY** — no deposit, no surface edits, no announcements.

## What this edition is

A Process v1.0 reissue of the published v0.4.2 (2026-10-30): content
unchanged, layout moved to Research Paper Template v1.0, evidence
consolidated into one `exp/results/summary.json`, companion GATE49
explorer demo built, internal host identifiers genericized to host
classes in the paper text and in the staged copies of the evidence
files (the already-public HF supplement is untouched).

## Numbers verification — PASS 56/56

`verify_numbers.py` (a checker independent of the build scripts)
re-derives every headline figure from the per-run evidence JSONs —
counting verdicts, recomputing means and category splits — compares
them against summary.json and against the source files' SHA-256, then
checks the figures printed in the shipped PDF text and HTML. Coverage:
all 10 program runs (totals, means, hard failures, category splits),
the 3 Mini flagship probes, the prescribed-decline null policy
(25/49), all 16 served-path/baseline runs, the corpus domain sum
(982), and every headline figure as printed (program totals and means,
served pre/post totals, null 25/49 and 23/49, corpus 982/1,082/1,246,
the 35/49 content+thinking diagnostic, the ≈$16 attempt-3 cost).
Result: **56/56 PASS** (`numbers-verification.json`).

Two source discrepancies found and resolved in favour of the per-run
JSONs, recorded in summary.json (`known_source_discrepancies`): the
legacy program summary's Mini C.1 mean (4.837 is the Wave C value; the
per-run report gives 4.694) and its top-level air/mini entries
describing the Wave C cycle rather than the latest. The bare-decline
null result (23/49, mean 3.367, 1 hard failure) survives only as the
paper's §7.1 text and the vendored sanity record; no JSON report
exists, and summary.json says so rather than reconstructing one.

## Blocker sweep — PASS, one item HELD by design

`sweep.json`, three tiers:

- **Tier 1 — internal identifiers (all 85 pack text files): 0 hits.**
  No host names, tailnet IPs or names, internal paths, or credential
  shapes anywhere in the shipped paper, demo, or evidence bundle.
  The scrub that produced this (15 phrase substitutions in the paper
  text; 70 occurrences across 49 evidence files) is logged in the
  internal build tree; the tooling itself enumerates the identifiers
  it removes and is therefore not part of the public bundle.
- **Tier 2 — shipped paper HTML: 0 hits** (no placeholders, format
  braces, confidentiality marks, TODO/FIXME/lorem).
- **Tier 3 — evidence content: 30 matches, all adjudicated** in
  sweep.json: recorded model answers quoted verbatim in the demo
  payload (incl. one answer containing "TBD" as its own text), the
  facts package's own CONFIDENTIAL field values (the gate's data
  semantics; the package is already public), the grounding prompt's
  topic classification, Ollama/Go template syntax quoted in the
  served-path record, and regex quantifier braces in the scorer's
  source. None is a document placeholder or mark.
- **Byline: HELD.** The cover carries a clearly-marked placeholder
  author block drawn from the manifest's authorship record (author:
  Sadie Weaving, CAO; accountable human author: Tommy Xaypanya, CTO &
  Co-Founder; Craig Ross is not an author of this paper), and the
  v0.4.2 authorship disclosure is retained verbatim in the front
  matter below it. Finalizing the cover is the one step waiting on
  Tommy's byline ruling. Not passed, not waived — held.

## Render QA — PASS

Playwright renders at 1280 px and a true 390 px (`render-metrics.json`,
screenshots + `contact-sheet.jpg` in this folder):

- No horizontal document scroll at either width for the paper or the
  demo (390/390, 1280/1280). Three overflow defects were found and
  fixed during the build: the template's block-scroller tables needed
  no wrapper (an added wrapper broke them — removed); a `pre` block
  needed a screen-only `overflow-x:auto`; long unbreakable tokens
  (hashes, URLs) in §13/§15 prose needed mobile `overflow-wrap`.
- A fourth defect was caught by the same pass: the §13 provenance
  register's second row group had been printing as raw markdown pipe
  text (the source splits the table with blank lines). The build now
  rejoins table row groups; the shipped HTML has 14 tables and zero
  raw-pipe paragraphs.
- Demo interaction smoke test: run cards render all 27 runs in three
  groups; selecting a run renders its category bar and 49-cell
  per-question grid (program/null runs) or its recorded-answer browser
  (served runs, whose bundle records carry answers, not verdicts —
  the demo says so); a cell click returns the question's record.
- PDF: 56 pages, Letter; cover is the template's dark cover panel by
  design, body is the light editorial layout with running header
  (short title / "THOX.ai Research · preprint, not peer reviewed")
  and the tagline footer with page numbers. Print renders with the
  default (light) colour scheme; an `emulateMedia` colour-scheme call
  was removed from pdf.cjs after it was found to flip this Chromium
  build's print layout to screen metrics (22 pp, wrong layout) —
  caught by this QA pass when the page count moved.

## Provenance of this build

- Source text: `paper-v042/whitepaper.md`, verified byte-identical in
  result to the live v0.4.2 (local PDF SHA-256 cea173de…e8918 = the HF
  dataset copy).
- Evidence: the v0.4.2 `wavec-supplement/` bundle, consolidated by
  `wp/consolidate_summary.py`; per-file SHA-256 for every source is
  recorded inside summary.json.
- Nothing was deposited, pushed, or posted. Live surfaces are
  byte-unchanged by this build.

## Finalization addendum — 2026-11-04 (publication lane)

- **Byline: FINALIZED** under Tommy Xaypanya's ruling of 2026-11-04
  (keep the original authorship as published). The cover placeholder
  block is replaced by the final byline (Sadie Weaving, author; Tommy
  Xaypanya, accountable human author, corresponding author); the cover
  pill reads "Public edition"; section 14 document control gained the
  v0.5.0 row. The v0.4.2 authorship-and-accountability disclosure is
  retained verbatim in the front matter. Craig Ross is not an author.
- **Re-verification after finalization:** numbers 56/56 PASS; blocker
  sweep PASS (byline item finalized; tier 1: 0, tier 2: 0, tier 3: 30,
  all adjudicated); PDF 56 pp.
- **Final hashes (SHA-256):** PDF
  19ad720f8e842f06b0069f01bd36ffb7429c9d7886bee92089402a28d0761c45;
  HTML b9233dd0a945e223ddfa35e45ffa86cee43a958002dda8c058d87031e0a32d30;
  demo 1a39e729d0276bf5daac2c43a6eaea42c0da2c31d7d574e05ab234209554626c
  (unchanged by finalization); summary.json
  d75756afe81e8c2640c57bd22a50e66da1b6bce555e2d128d51ad97385efabe7
  (unchanged). The artifact ZIP hash is recorded in the pack
  HANDOFF.md (the ZIP cannot hash itself).
