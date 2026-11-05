# Development — Wave C Flagship Program Whitepaper repository

## Repository conventions

- This repository is a **publication record**, not a working tree.
  The paper is never edited silently: a new edition is a new version
  in `paper/`, a new GitHub release, and a new version on Zenodo,
  following the THOX Research Paper Process v1.0.
- Canonical bytes: the files in `paper/` and `artifact/` are the
  exact bytes of the edition of record. Their SHA-256 hashes are in
  the root README and in `artifact/MANIFEST.sha256.json`. Any change
  to a shipped file is a new edition, never a fix-up commit.
- The byline follows the paper's front matter. Do not restyle the
  authorship or the front-matter authorship and accountability
  disclosure; both are part of the published record.

## Rebuilding the paper

The build tree is preserved in `artifact/wp/`:

- `wp/build.py` — lays the frozen v0.4.2 source text into the THOX
  Research Paper Template v1.0 (cover, stat cards taken from
  `exp/results/summary.json`, body), appends the v0.5.0 row to the
  §14 document-control table, and writes `wp/paper.src.html` (==
  the shipped HTML edition), `wp/cover.html`, and `wp/body.html`.
- `wp/build_demo.py` — builds the GATE49 explorer demo into `dist/`.
- `wp/pdf.cjs` — renders the PDF (cover + body) with headless
  Chromium and merges with `pdfunite`. Do not reintroduce an
  `emulateMedia({colorScheme})` call: on this Chromium build it
  flips the print layout to screen metrics (see the QA report).
- `wp/consolidate_summary.py` — rebuilds `exp/results/summary.json`
  from the per-run reports.

## Verification before any new edition

- `wp/qa/verify_numbers.py` — re-derives every headline figure from
  the per-run JSONs and checks the printed paper (v0.5.0: 56/56 PASS).
- `wp/qa/sweep.py` (internal build tree only; the tool enumerates the
  identifiers it checks for) — the Process §4 blocker sweep
  (v0.5.0: PASS; tier 1 0, tier 2 0, tier 3 30 adjudicated).
- Render QA at desktop and 390 px widths before calling an edition
  done; page count and scroll metrics are recorded in `wp/qa/`.

## Releases

Each edition gets a formal GitHub release whose assets are the
paper PDF, the HTML edition, the demo, and the artifact ZIP,
byte-identical to the pack of record.
