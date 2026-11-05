"""Build the Wave C v0.5.0 companion demo: a GATE49 explorer.

Single self-contained HTML file. All data comes from the pack's own
evidence files (exp/results/*.json, consolidated in summary.json):
per-question verdicts for the ten program runs and the null policy,
category aggregates + recorded answers for the served-path runs, and
the flagship probe checks. Everything renders client-side; no network.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "exp" / "results"
S = json.loads((RES / "summary.json").read_text(encoding="utf-8"))


def load(rel: str) -> dict:
    return json.loads((RES / rel).read_text(encoding="utf-8"))


def verdict_list(rel: str) -> list[dict]:
    d = load(rel)
    out = []
    for v in d.get("verdicts") or []:
        out.append({
            "id": v.get("id"), "cat": v.get("category"), "passed": bool(v.get("passed")),
            "score": v.get("score"), "hard": bool(v.get("hard_failure")),
            "answer": (v.get("answer") or "")[:220],
        })
    return out


def answers_map(rel: str) -> dict:
    d = load(rel)
    ans = d.get("answers") or {}
    if isinstance(ans, dict):
        return {k: str(v)[:220] for k, v in ans.items()}
    return {}


def run_entry(group: str, label: str, slot: str, cycle: str, rec: dict,
              verdicts=None, answers=None, ruling: str = "") -> dict:
    return {
        "group": group, "label": label, "slot": slot, "cycle": cycle,
        "model": rec.get("model"), "passed": rec.get("passed_count"),
        "total": rec.get("total"), "mean": rec.get("mean_score"),
        "hard": rec.get("hard_failures"), "soft": rec.get("soft_failures"),
        "cats": {c: [v.get("passed"), v.get("total")] for c, v in (rec.get("by_category") or {}).items()},
        "ruling": ruling, "host": rec.get("host_class", ""),
        "verdicts": verdicts, "answers": answers,
    }


def main() -> None:
    runs: list[dict] = []
    files = {
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
    cyc_label = {"wave_c": "Wave C", "wave_c1": "Wave C.1", "wave_c2": "Wave C.2"}
    slot_label = {"air": "ThoxAir-0.5B", "edge": "ThoxEdge-0.8B", "mini": "ThoxMini-Phi4Mini", "clip": "ThoxClip-Qwen3-0.6B"}
    for (slot, cyc), rel in files.items():
        rec = S["program_runs"][slot][cyc]
        runs.append(run_entry("Program runs (merged weights, Transformers)",
                              f"{slot_label[slot]} — {cyc_label[cyc]}", slot, cyc, rec,
                              verdicts=verdict_list(rel), ruling=rec.get("ruling", "")))
    nullp = S["null_policies"]["prescribed_decline"]
    runs.append(run_entry("Null policy", "Constant decline responder (prescribed form)",
                          "null", "null", nullp,
                          verdicts=verdict_list("null-policy/factuality-report.json"),
                          ruling="The floor every publish bar is read against (paper section 7.3)."))
    sp = S["served_path"]
    served_files = {
        "as_served_pre_fix": ("gate49-A-{}-gate.json", "Served, pre-fix"),
        "as_served_post_fix": ("gate49-postfix-A-{}-gate.json", "Served, post-fix"),
        "bases_bare": ("gate49-B-{}-gate.json", "Base, bare"),
        "bases_grounded": ("gate49-C-{}-gate.json", "Base, grounded"),
    }
    tag_files = {"air": "air", "clip": "clip", "edge": "edge", "mini": "mini",
                 "phi4mini": "phi4mini", "qwen25": "qwen25", "qwen3": "qwen3", "qwen35": "qwen35"}
    for group_key, (pat, glabel) in served_files.items():
        for tag, rec in sp[group_key].items():
            rel = "served-path/" + pat.format(tag_files[tag])
            runs.append(run_entry("Served path & base baselines (Ollama, as served)",
                                  f"{rec.get('model')} — {glabel}", tag, group_key, rec,
                                  answers=answers_map(rel),
                                  ruling="Content channel scored; thinking-channel diagnostic in summary.json."))
    probes = {
        "program_mini": {c: {"passed": r["passed_count"], "total": r["total"],
                             "checks": r["checks"]}
                         for c, r in S["probes_flagship_mini"].items()},
        "served": {g: {k: {"passed": v["passed_count"], "total": v["total"]}
                       for k, v in runs_.items()} for g, runs_ in S["served_probes"].items()},
    }
    data = {"runs": runs, "probes": probes,
            "served_pairs": {tag: {"pre": sp["as_served_pre_fix"][tag]["passed_count"],
                                   "post": sp["as_served_post_fix"][tag]["passed_count"],
                                   "model": sp["as_served_pre_fix"][tag]["model"]}
                             for tag in ("air", "edge", "mini", "clip")},
            "tally": S["program_tally"]["slots"],
            "corpus": S["corpus"]}

    demo = HTML.replace("/*__DATA__*/", json.dumps(data))
    out = ROOT / "dist" / "WaveC_Demo_v0.5.0.html"
    out.write_text(demo, encoding="utf-8")
    print("wrote", out, len(demo), "bytes")


HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GATE49 Explorer — Wave C Flagship Program (THOX Whitepaper v0.5.0)</title>
<meta name="description" content="Interactive explorer for the Wave C whitepaper's GATE49 results: every program run, the null policy, and the served-path measurements, rendered client-side from the paper's evidence bundle (summary.json).">
<style>
:root{--bg:#FFFFFF;--fg:#111827;--muted:#6B7280;--rule:#E5E7EB;--card:#F9FAFB;--green:#047C3D;--green-ink:#047C3D;--pale:#E6F4EC;--bad:#B91C1C;--amber:#B45309;--mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,monospace;--sans:Inter,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0B0F14;--fg:#F3F4F6;--muted:#9CA3AF;--rule:#1F2937;--card:#111827;--green:#05A451;--green-ink:#05A451;--pale:#0F2A1B;--bad:#F87171;--amber:#FBBF24}}
:root[data-theme="dark"]{--bg:#0B0F14;--fg:#F3F4F6;--muted:#9CA3AF;--rule:#1F2937;--card:#111827;--green:#05A451;--green-ink:#05A451;--pale:#0F2A1B;--bad:#F87171;--amber:#FBBF24}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font-family:var(--sans);line-height:1.5;font-size:15px}
.wrap{max-width:960px;margin:0 auto;padding:24px 16px 48px}
header{border-bottom:2px solid var(--green);padding-bottom:10px;margin-bottom:18px}
.eyebrow{font-family:var(--mono);font-size:11px;color:var(--green);text-transform:uppercase;letter-spacing:.08em}
h1{font-size:24px;margin:6px 0 4px;line-height:1.2}
h2{font-size:18px;margin:26px 0 8px;border-bottom:1px solid var(--rule);padding-bottom:4px}
p{margin:0 0 10px}
.note{font-size:13px;color:var(--muted)}
.card{background:var(--card);border:1px solid var(--rule);border-radius:8px;padding:14px;margin:10px 0}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:10px 0}
.kpi{border:1px solid var(--rule);border-top:3px solid var(--green);border-radius:6px;padding:10px;background:var(--card)}
.kv{font-family:var(--mono);font-size:22px;font-weight:700;color:var(--green-ink)}
.kl{font-size:12px;color:var(--muted);margin-top:3px}
.kt{font-family:var(--mono);font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-top:6px}
select{font-family:var(--mono);font-size:13px;padding:7px 8px;border:1px solid var(--rule);border-radius:6px;background:var(--bg);color:var(--fg);max-width:100%}
.rungrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px;margin:10px 0}
.run{border:1px solid var(--rule);border-radius:8px;padding:12px;background:var(--card);cursor:pointer;text-align:left;width:100%;color:var(--fg);font-family:var(--sans)}
.run.sel{border-color:var(--green);border-top:3px solid var(--green)}
.run .rs{font-family:var(--mono);font-size:24px;font-weight:700;color:var(--green-ink)}
.run .rm{font-size:12px;color:var(--muted)}
.bar{height:8px;background:var(--rule);border-radius:4px;overflow:hidden;margin:6px 0}
.bar>i{display:block;height:100%;background:var(--green)}
.catbar{display:flex;height:10px;border-radius:4px;overflow:hidden;margin:4px 0;border:1px solid var(--rule)}
.catbar>i{display:block;height:100%}
.qgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(30px,1fr));gap:4px;margin:10px 0}
.q{aspect-ratio:1;border-radius:4px;border:1px solid var(--rule);font-family:var(--mono);font-size:9px;display:flex;align-items:center;justify-content:center;cursor:pointer;color:var(--fg);background:var(--card);padding:0}
.q.pass{background:var(--pale);border-color:var(--green)}
.q.hard{background:#FEE2E2;border-color:var(--bad);color:var(--bad);font-weight:700}
.q.soft{background:#FEF3C7;border-color:var(--amber)}
.q.fail{background:var(--card);color:var(--muted)}
.q.ans{cursor:pointer}
.legend{font-size:12px;color:var(--muted)}
.legend b{display:inline-block;width:10px;height:10px;border-radius:2px;margin:0 3px 0 10px;vertical-align:middle}
pre,.out{font-family:var(--mono);font-size:12.5px;white-space:pre-wrap;word-break:break-word;background:var(--bg);border:1px solid var(--rule);border-radius:6px;padding:10px;margin:8px 0 0;overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:13px;margin:8px 0}
th,td{text-align:left;padding:5px 6px;border-bottom:1px solid var(--rule)}
th{color:var(--muted);font-weight:600}
footer{margin-top:30px;font-size:12px;color:var(--muted);border-top:1px solid var(--rule);padding-top:10px}
.theme{float:right;font-size:12px;background:transparent;color:var(--muted);border:1px solid var(--rule);padding:4px 8px;margin:0;cursor:pointer}
.pair{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}
</style>
</head>
<body>
<div class="wrap">
<header>
  <button class="theme" id="themeBtn" type="button">Theme: auto</button>
  <div class="eyebrow">THOX.ai Research &middot; companion demo to whitepaper v0.5.0</div>
  <h1>GATE49 explorer: the Wave C flagship program, run by run</h1>
  <p class="note">Every number below is rendered in your browser from the paper's own evidence bundle — the same per-run JSON reports consolidated in <b>exp/results/summary.json</b>. GATE49 is the fleet's 49-question factuality gate (verified 12 / unknown 26 / known_false 10 / pricing 1) scored by the program's own scorer. Program runs were measured on merged weights in a cloud GPU job; served-path runs were measured exactly as shipped, through Ollama on a CPU cloud VM. Nothing here is a device-hardware result — no adapter in this program has been qualified on physical device hardware.</p>
</header>

<h2>Program tally (paper section 9.5)</h2>
<div class="kpis" id="kpis"></div>

<h2>Explore the runs</h2>
<p><label class="note" for="groupSel">Run group</label><br>
<select id="groupSel"></select></p>
<div class="rungrid" id="runGrid"></div>
<div class="card" id="detail">
  <div class="note">Select a run card to see its category splits and per-question record.</div>
</div>

<h2>Served path: before / after the serving-configuration fix</h2>
<p class="note">The shipped Ollama tags, gated exactly as served (section 8.6). The fix was native templates, declared capabilities, and the facts block one Modelfile had lacked — a configuration change, not a model change.</p>
<div class="pair" id="pairs"></div>

<h2>Flagship probe (ThoxMini slot)</h2>
<div id="probes"></div>

<footer>
Evidence classes: program and served-path results are MEASURED on the host classes named in summary.json; corpus counts are CALCULATED from the construction record. Demo data: exp/results/summary.json and the per-run reports in the artifact bundle for "Flagships for Every Device: The Wave C Training Program" (whitepaper v0.5.0, Process v1.0 reissue of v0.4.2).<br>
Your AI. Your Data. Your Rules.&trade; &middot; THOX.ai LLC
</footer>
</div>
<script type="application/json" id="data">/*__DATA__*/</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const CATCOLORS = {verified:'#047C3D', unknown:'#6B7280', known_false:'#B91C1C', pricing:'#B45309'};
const $ = s => document.querySelector(s);

const tally = D.tally;
const kpiDefs = [
  ['2 promoted', 'ThoxAir (Wave C.2) and ThoxEdge (Wave C) end promoted; Mini ships as a documented baseline; Clip stands on its prior baseline', 'Measured · program tally'],
  ['25/49', 'Null-policy floor: a constant decline responder passes the gate at 25/49 with zero hard failures — every bar is read against it', 'Measured · program scorer'],
  ['982 rows', 'One factuality corpus for all four flagships (Wave C.1: 1,082; Wave C.2: 1,246)', 'Calculated · construction record'],
  ['12 → 40/49', 'ThoxClip served-path score before / after the serving-configuration fix (section 8.6)', 'Measured · served path'],
];
$('#kpis').innerHTML = kpiDefs.map(([v,l,t]) =>
  `<div class="kpi"><div class="kv">${v}</div><div class="kl">${l}</div><div class="kt">${t}</div></div>`).join('');

const groups = [...new Set(D.runs.map(r => r.group))];
$('#groupSel').innerHTML = groups.map(g => `<option>${g}</option>`).join('');

function catBar(cats) {
  const tot = Object.values(cats).reduce((a,[p,t]) => a + (t||0), 0) || 49;
  return '<div class="catbar">' + Object.entries(cats).map(([c,[p,t]]) =>
    `<i style="width:${(t/tot*100)}%;background:${CATCOLORS[c]||'#999'};opacity:${t ? (0.35 + 0.65*(p/t)) : 0.2}" title="${c}: ${p}/${t}"></i>`).join('') + '</div>';
}
function catLine(cats) {
  return Object.entries(cats).map(([c,[p,t]]) => `${c} ${p}/${t}`).join(' · ');
}

let selRun = null;
function renderRuns() {
  const g = $('#groupSel').value;
  const runs = D.runs.filter(r => r.group === g);
  $('#runGrid').innerHTML = runs.map((r,i) =>
    `<button type="button" class="run${r===selRun?' sel':''}" data-i="${D.runs.indexOf(r)}">
       <div class="rs">${r.passed}/${r.total}</div>
       <div><b>${r.label}</b></div>
       <div class="rm">${r.model || ''}</div>
       <div class="bar"><i style="width:${r.passed/r.total*100}%"></i></div>
       <div class="rm">mean ${r.mean} · hard ${r.hard} · soft ${r.soft}</div>
       <div class="rm">${catLine(r.cats)}</div>
     </button>`).join('');
  document.querySelectorAll('.run').forEach(b => b.addEventListener('click', () => {
    selRun = D.runs[+b.dataset.i]; renderRuns(); renderDetail();
  }));
}
function renderDetail() {
  const r = selRun, el = $('#detail');
  if (!r) return;
  let h = `<div class="eyebrow">${r.group}</div><h3 style="margin:6px 0">${r.label} — ${r.passed}/${r.total}, mean ${r.mean}/5</h3>`;
  h += catBar(r.cats) + `<p class="note">${catLine(r.cats)} · hard failures ${r.hard} · soft failures ${r.soft}</p>`;
  if (r.ruling) h += `<p><b>Ruling / note:</b> ${r.ruling}</p>`;
  if (r.host) h += `<p class="note">Host class: ${r.host}</p>`;
  if (r.verdicts && r.verdicts.length) {
    h += `<div class="qgrid">${r.verdicts.map((v,i) =>
      `<button type="button" class="q ${v.passed?'pass':(v.hard?'hard':'fail')}" data-q="${i}" title="${v.id}">${i+1}</button>`).join('')}</div>
      <p class="legend">Question cells:<b style="background:var(--pale);border:1px solid var(--green)"></b>pass
      <b style="background:#FEE2E2;border:1px solid var(--bad)"></b>hard failure<b style="background:var(--card);border:1px solid var(--rule)"></b>fail (soft). Click a cell for the record.</p>
      <div class="out" id="qOut">Select a question cell.</div>`;
  } else if (r.answers && Object.keys(r.answers).length) {
    const ids = Object.keys(r.answers);
    h += `<p class="note">This served-path run's bundle record carries its 49 recorded answers (the per-question verdicts live in the run's scoring record; category splits above are the scored result). Pick a question id to read the served answer.</p>
      <p><select id="ansSel">${ids.map(id => `<option>${id}</option>`).join('')}</select></p>
      <div class="out" id="qOut"></div>`;
  }
  el.innerHTML = h;
  const qo = $('#qOut');
  if (r.verdicts && r.verdicts.length) {
    el.querySelectorAll('.q').forEach(b => b.addEventListener('click', () => {
      const v = r.verdicts[+b.dataset.q];
      qo.textContent = `${v.id}\ncategory: ${v.cat} · score: ${v.score}/5 · passed: ${v.passed} · hard failure: ${v.hard}\n\nanswer (as recorded, truncated):\n${v.answer || '(no answer text in record)'}`;
    }));
  } else if (r.answers) {
    const sel = $('#ansSel');
    const show = () => { qo.textContent = sel.value + '\n\n' + (r.answers[sel.value] || ''); };
    sel.addEventListener('change', show); show();
  }
}
$('#groupSel').addEventListener('change', () => { selRun = null; renderRuns(); $('#detail').innerHTML = '<div class="note">Select a run card to see its category splits and per-question record.</div>'; });
renderRuns();

$('#pairs').innerHTML = Object.entries(D.served_pairs).map(([tag,p]) =>
  `<div class="card"><b>${p.model}</b>
   <div class="rm note">pre-fix</div><div class="bar"><i style="width:${p.pre/49*100}%"></i></div><div class="rm">${p.pre}/49</div>
   <div class="rm note">post-fix</div><div class="bar"><i style="width:${p.post/49*100}%"></i></div><div class="rm">${p.post}/49</div></div>`).join('');

const pm = D.probes.program_mini;
$('#probes').innerHTML = '<table><tr><th>Run</th><th>Probe</th><th>Checks</th></tr>' +
  Object.entries(pm).map(([cyc,r]) => `<tr><td>ThoxMini program probe — ${cyc.replace('wave_c','Wave C').replace('wave_c1','Wave C.1').replace('wave_c2','Wave C.2')}</td><td>${r.passed}/${r.total}</td><td>${r.checks.map(c => `${c.id}: ${c.passed?'PASS':'FAIL'}`).join(' · ')}</td></tr>`).join('') +
  Object.entries(D.probes.served.as_served_post_fix || {}).map(([k,v]) => `<tr><td>Served probe, post-fix — ${k}</td><td>${v.passed}/${v.total}</td><td></td></tr>`).join('') +
  '</table><p class="note">Promotion for the Mini slot requires the probe at 6/6; it has never been met, which is why the slot ships its Wave C build as a documented baseline.</p>';

const themeBtn = $('#themeBtn');
const themes = ['auto','light','dark']; let ti = 0;
themeBtn.addEventListener('click', () => {
  ti = (ti + 1) % 3; const t = themes[ti];
  themeBtn.textContent = 'Theme: ' + t;
  if (t === 'auto') document.documentElement.removeAttribute('data-theme');
  else document.documentElement.setAttribute('data-theme', t);
});
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
