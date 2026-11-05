# gate49 bundle — vendoring record

The fleet 49-question factuality gate, vendored so HF Jobs can run it on HF
infrastructure (HF Jobs cannot read the private GitHub repo the gate lives
in). Vendored 2026-10-28. Follows `(internal path)`
with the premise correction recorded there and in §2 below: the gate builds
its questions from the `facts` package, not from a `questions.jsonl`.

## 1. Bundle inventory (as uploaded, under `gate49/` in both plane repos)

| File | Bytes | Origin |
| --- | --- | --- |
| `factuality_gate49.py` | 14,737 | `scripts/factuality_gate.py`, ttracx/thoxllm-factory (14,448 B) + the §3 adaptation |
| `facts/__init__.py` | 2,221 | ttracx/thoxllm-factory `facts/` |
| `facts/checker.py` | 13,211 | 〃 |
| `facts/dataset.py` | 23,554 | 〃 |
| `facts/errors.py` | 694 | 〃 |
| `facts/loader.py` | 11,923 | 〃 |
| `facts/prompt.py` | 6,175 | 〃 |
| `facts/questions.py` | 41,819 | 〃 |
| `facts/sync.py` | 11,380 | 〃 |
| `facts/data/thox_facts.json` | 13,586 | the canonical facts card, v1.1.0 — the file the loader reads by default (see §2) |
| `facts/data/SOURCE.json` | 898 | card provenance (ships with the loader's drift data) |
| `facts/data/THOX_FACTS.md` | 11,643 | human-readable card doc (`CARD_DOC_PATH`) |
| `grounding_system.txt` | 5,032 | tommytracx/thox-compute plane repo root (facts card v1.1.0 baked system prompt) — the flagship probe's system prompt |
| `run_gate49_job.py` | 13,110 | new, §5 |
| `probe_flagship.py` | 10,954 | new, §6 |

Every fetched file's byte size matches its GitHub listing exactly. Fetched
via the GitHub connector read CLI (`get_file_contents`), never `call-tool`.

## 2. Loader data files — confirmed in bundle

`facts/loader.py` resolves its data relative to the package file itself
(`DATA_DIR = Path(__file__).resolve().parent / "data"`), so the bundle is
self-locating: `load_facts()` with no argument reads
`facts/data/thox_facts.json` (the card), `load_provenance()` reads
`facts/data/SOURCE.json`, and `CARD_DOC_PATH` points at
`facts/data/THOX_FACTS.md`. All three are in the bundle. No path surgery was
needed anywhere in the package.

## 3. The one adaptation to the gate script

`factuality_gate49.py` differs from the factory original by exactly one
block (verified by diff): the original computes
`REPO_ROOT = Path(__file__).resolve().parent.parent` because it lives in
`scripts/` with `facts/` at the repo root. In the bundle the script sits at
the bundle root with `facts/` beside it, so the vendored copy sets
`REPO_ROOT = Path(__file__).resolve().parent` (plus a comment saying why).
Behaviour is otherwise byte-identical.

Consequences, both benign:
- `DEFAULT_OUT` becomes `<bundle>/eval/results/factuality` — the job
  entrypoint always passes `--out` explicitly.
- The gate's live-backend path (`make_model_runner`) still imports
  `eval/run_eval.py`, which is deliberately NOT vendored: its backends
  cannot load a LoRA adapter. The job entrypoint (§5) never uses it — it
  generates with the merged model itself and scores via `--transcript`.

## 4. Local sanity run (transcript mode, no model, no venv)

The whole `facts` package is stdlib-only (json / re / hashlib / dataclasses /
pathlib / textwrap / datetime / urllib), so no venv was needed.

Run, from the bundle directory:

1. `load_facts()` + `build_questions(facts)` → **49 questions built** from
   card v1.1.0, category split **verified 12 / unknown 26 / known_false 10 /
   pricing 1** — exactly the split GATE49.md records for Waves A/B, which is
   what proves the vendored question set is the fleet's question set.
2. Fabricated a transcript answering all 49 ids with one harmless decline
   ("I don't have verified information on that, so I can't confirm it.")
   and ran:
   `python3 factuality_gate49.py --model sanity-decline-transcript --transcript <t.json> --out <dir> --dump-answers --quiet`
3. Result: **report produced scoring all 49 questions** —
   23/49 passed, mean 3.367/5, 1 hard failure, exit code 1 (a FAIL verdict
   is a successful measurement). Breakdown is the expected signature of a
   content-free transcript: unknown 23/26 passed with **0 hard failures**
   (declines are correct there), verified 0/12 (a decline contains no
   facts), known_false 0 passed but **0 hard failures** (the decline never
   repeats a false claim), pricing 1 hard failure (the pricing rule needs
   more than a bare decline). Imports resolve, the scorer runs, the report
   (`factuality-report.json` + `.md` + `answers.json`) writes. The bundle
   works standalone.

## 5. run_gate49_job.py — how a gate job runs

Per adapter, following the plane launcher's `_gate_command` shape:

1. Fetch the bundle from the plane Space repo
   (`snapshot_download(<space>, repo_type="space", allow_patterns="gate49/**")`
   into `/workspace`), install the entry's deps profile (all four flagship
   entries use `latest` on the bare CUDA image, apt prelude included — the
   gate reuses the trainer's profile so it measures the same stack).
2. `python /workspace/gate49/run_gate49_job.py` with secret `HF_TOKEN` and
   env `THOX_SPEC = {"id", "base_model", "output_repo", "gate": "gate49"}`
   (CLI flags `--base-model/--adapter-repo/--output-repo` override).
3. Inside: base + adapter load (plane-identical tokenizer handling,
   including the `extra_special_tokens` workaround and ChatML fallback) →
   `merge_and_unload()` → save merged dir → **reload standalone** → greedy
   answers to all 49 questions (max_new_tokens 320, weights-only house
   system prompt, `enable_thinking=False` via chat-template kwargs for
   Qwen3/Qwen3.5) → transcript scored by `factuality_gate49.py --transcript`
   (the baselines' own scorer, not a reimplementation).
4. Outputs: the gate report enriched with the raw answers (the gate's own
   report omits them; GATE49.md's spec for the file requires them) uploaded
   to the adapter repo as **`thox_gate49.json`**, verdict banner stamped on
   the model card (gate.py's pattern), stdout prints `passed/49` + mean.
   Exit 0 on PASS and on FAIL; non-zero only when the gate could not run
   (gate exit 2).

## 6. probe_flagship.py — Phi-4-mini only, additional

Deployed configuration: same merged model, system prompt =
`grounding_system.txt` from this bundle. Six checks per GATE49.md — chipset
grounding trap, unpublished-specs trap, grounded recall (founder names +
roles read from the card at runtime), arithmetic 17 + 25, tool-routing
shape (single `get_device_status` call for the ThoxMini, no prose
preamble), stop behaviour (first verified-category question must end at
EOS without looping). Checks are transparent heuristics; every raw answer
is recorded. Uploads **`thox_flagship_probe.json`** to the adapter repo;
exit 0 regardless of outcome.

## 7. Upload record

One commit per repo, all 15 bundle files under `gate49/`, via the HF
commit API with every file entry carrying `"encoding": "base64"` (without
it the API stores base64 text literally — the known fleet bug).

| Repo | Commit |
| --- | --- |
| tommytracx/thox-compute | `8b46f482facf4a22902f6cddfbba125b1c1a12d8` |
| Thox-ai/thox-training-control | `064f5729818f0a9680de86108c528d62aa69f34b` |

Read-back verification (resolve URLs, full-content sha256 vs local):
`gate49/factuality_gate49.py` (14,737 B) and
`gate49/facts/data/thox_facts.json` (13,586 B) — **sha256 MATCH in both
repos**. Tree listing confirms all 15 files present under `gate49/` in
both repos. This VENDOR.md was added to both repos under `gate49/` in a
follow-up commit after the bundle commit.

## 8. Gate-job launch parameters for the flagship entries

Common: deps `latest`, image `nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04`,
secret `HF_TOKEN`, greedy / 320 tokens / weights-only, outputs
`thox_gate49.json` + card banner. Publish bars from GATE49.md (an adapter
promotes only on improvement, never with a known_false hard failure
outstanding):

| Entry | Base model | Adapter repo | Gate flavor | Publish bar |
| --- | --- | --- | --- | --- |
| mini-phi4-flagship | `microsoft/Phi-4-mini-instruct` | `Thox-ai/ThoxMini-Phi4Mini` | a10g-large | No baseline (establishes it). Requires: gate completes, **zero known_false hard failures**, and **probe 6/6** (`probe_flagship.py`, same THOX_SPEC). |
| air-05b-flagship | `Qwen/Qwen2.5-0.5B-Instruct` | `Thox-ai/ThoxAir-0.5B` | a10g-small | No baseline (slot was empty). Requires: gate completes, **zero known_false hard failures**. |
| edge-08b-wavec | `Qwen/Qwen3.5-0.8B` | `Thox-ai/ThoxEdge-0.8B-WaveC` | a10g-small | Must exceed **19/49 (2.714/5)**, the Wave A baseline. The Wave B 0/49 was the Ollama thinking-channel serving artifact, NOT a baseline. `enable_thinking=False` applies. |
| clip-06b-wavec | `Qwen/Qwen3-0.6B` | `Thox-ai/ThoxClip-Qwen3-0.6B-WaveC` | a10g-small | Must exceed **22/49 (2.776/5)** (the 205-row-diet run). `enable_thinking=False` applies. |

Calibration reference, not a bar: ThoxEdge-0.5B Wave B gated 47/49
(4.837/5) on this recipe and corpus. An adapter that misses its bar stays
in its WaveC/flagship repo unpublished and the published repo keeps its
prior weights — nothing is overwritten pre-gate.

No training jobs and no gate jobs were launched as part of this vendoring;
no jobs.yaml and no model repo was modified.

## 9. Re-vendor 2026-10-30 — grounding_system.txt corrected at source

The §1 inventory row for `grounding_system.txt` (5,032 B) is superseded for
this one file. The prompt's hand-maintained THOX PRODUCT INTERNALS section
asserted unpublished device chipset identities (ThoxMini Air SoC, ThoxNova
prototype SoC, MagStack Air node hardware, the edge tier's Pi/Luckfox
hardware) under a "state these exactly when asked" header — contradicting
the facts card (which names no processor for any device) and THOX's
standing no-chipset-claims rule, and making the flagship probe's chipset
trap unpassable without disobeying the system prompt. Full investigation:
`(internal path)`.

Correction, applied at the source first and re-vendored from it:

- Source of truth located: the plane repo is the HF Space
  `tommytracx/thox-compute`; its repo-root `grounding_system.txt` was
  byte-identical to the bundle copy (sha256 `fcd65985…`, hash-verified
  2026-10-30 across the Space root, both Spaces' `gate49/` copies, this
  local copy, and the whitepaper supplement copy). No GitHub repo named
  `thox-compute` exists under `tommytracx`, `ttracx`, `sadiethox`, or the
  Thox-ai org (API 404 on every spelling, checked via the fleet Windows workstation `gh` and
  the GitHub connector identity, both acting as `ttracx`); the §1 origin
  note's "plane repo root" is the Space root.
- The five chipset-naming bullets were replaced at the source by a single
  no-chipset bullet ("Device processors and chipsets are NOT PUBLIC for
  any THOX device…"), and the section header was narrowed to the remaining
  internal bullets. Everything else in the file is byte-identical,
  CRLF endings preserved. Space commit `635732da` (root file) and
  `4c02a4ce` (`gate49/` copy); `Thox-ai/thox-training-control` `gate49/`
  copy in commit `f4587910`.
- This local copy was then re-vendored by fresh fetch from the corrected
  Space root (not hand-edited) on 2026-10-30.
- Corrected file: 4,645 B, sha256
  `f4bd8a681a531cadea30a6a4e8853804ea3635ff5e965659f9aef3618fdeb54e` —
  full-content hash, verified identical at the Space root, both Spaces'
  `gate49/` copies, and this local copy. (The 2026-10-28 vendoring had
  verified this file by byte size only; this re-vendor closes that gap.)
- The whitepaper supplement copy is a published historical record and was
  NOT updated. Probe results measured against the pre-correction prompt
  (LFM3 v1–v3, and the Phi-4-mini incumbent's pass) are not like-for-like
  with results against the corrected prompt; any re-run is a new deployed
  configuration and must be labelled as such.
