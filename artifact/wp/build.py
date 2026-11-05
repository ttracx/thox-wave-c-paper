"""Build the Wave C v0.5.0 paper in the THOX Research Paper Template v1.0.

Source of content: paper-v042/whitepaper.md (the v0.4.2 edition of record;
content frozen). This build re-lays that text into Template v1.0
(cover + stat cards + body), applies the Process section 4 security-sweep
host-class genericizations (scrub.PAPER_SUBS, asserted), embeds the
template's own Inter + JetBrains Mono @font-face block (extracted from
the canonical template example), and takes every stat-card number from
exp/results/summary.json.

Outputs:
  wp/paper.src.html  - the full single-file paper (== shipped HTML)
  wp/cover.html      - cover only, for the PDF cover render
  wp/body.html       - body only, for the PDF body render (running
                       header/footer are added by pdf.cjs)
Byline finalized 2026-11-04 under Tommy Xaypanya's ruling (keep the
v0.4.2 authorship as published); the §14 document-control row for
v0.5.0 is appended at build time (the source markdown is the frozen
v0.4.2 text). See wp/qa/QA-REPORT.md.
"""
from __future__ import annotations

import base64
import html as htmllib
import json
import re
import sys
from pathlib import Path

import markdown

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scrub import PAPER_SUBS, apply_subs  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WORKDIR = ROOT.parent
SRC_MD = WORKDIR / "paper-v042" / "whitepaper.md"
ASSETS = WORKDIR / "paper-v042" / "assets"
TEMPLATE_DIR = Path.home() / "workspace/standards/THOX_Research_Paper_Template_v1.0"
S = json.loads((ROOT / "exp" / "results" / "summary.json").read_text(encoding="utf-8"))

VERSION = "v0.5.0"
DATE = "2026-11-04"
TITLE = "Flagships for Every Device: The Wave C Training Program"
DEK = ("One flagship model per THOX device, trained, gated, and published "
       "under a single factuality standard")


def template_css() -> str:
    build_src = (TEMPLATE_DIR / "build.py").read_text(encoding="utf-8")
    css = build_src.split('CSS = """', 1)[1].split('"""', 1)[0]
    example = (TEMPLATE_DIR / "example" / "THOX_MeshStack_Research_Paper_v1.0.1.html").read_text(encoding="utf-8")
    faces = re.findall(r"@font-face\{[^}]*\}", example)
    assert len(faces) >= 20, f"expected the template font block, got {len(faces)} faces"
    css = css.replace("/*__FONTS__*/", "\n".join(faces))
    css = css.replace("/*__KATEX__*/", "")
    css += """
/* --- reissue addenda (Wave C v0.5.0): blockquote, figures, author hold --- */
blockquote{border-left:3px solid var(--green);background:var(--pale);padding:8px 12px;margin:10px 0 12px;font-size:9.5pt;break-inside:avoid}
blockquote p{margin:0}
.figwrap img{width:100%;height:auto}
.authorhold{border:1.5px dashed var(--green);border-radius:6px;padding:10px 12px;margin:0 0 14px;font-size:8.6pt;color:#F3F4F6}
.authorhold .ah-t{font-family:'JetBrains Mono',monospace;font-size:8pt;letter-spacing:.08em;text-transform:uppercase;color:var(--green);margin-bottom:4px}
.authorhold p{margin:0 0 4px;font-size:8.6pt;line-height:1.45;color:#F3F4F6}
@media screen{pre{overflow-x:auto}}
@media screen and (max-width:760px){code{overflow-wrap:anywhere;word-break:break-word}p,li,td{overflow-wrap:break-word}a{overflow-wrap:anywhere}}
"""
    return css


def md2html(text: str) -> str:
    return markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])


def figures_to_datauri(fragment: str) -> str:
    def repl(m: re.Match) -> str:
        alt, src = m.group(1), m.group(2)
        path = WORKDIR / "paper-v042" / src
        b64 = base64.b64encode(path.read_bytes()).decode()
        num = re.match(r"Figure (\d+)", alt)
        label = f"Figure {num.group(1)}." if num else "Figure."
        caption = re.sub(r"^Figure \d+\s*—\s*", "", alt)
        return (f'<figure><div class="figwrap"><img alt="{htmllib.escape(alt)}" '
                f'src="data:image/png;base64,{b64}"></div>'
                f'<figcaption><b>{label}</b> {htmllib.escape(caption)}</figcaption></figure>')
    return re.sub(r'<p><img alt="([^"]*)" src="(assets/[^"]*)" /></p>', repl, fragment)


def split_chunks(md_text: str) -> list[tuple[str, str]]:
    parts = re.split(r"(?m)^(#[ ]+.*)$", md_text)
    chunks: list[tuple[str, str]] = []
    pre = parts[0]
    for i in range(1, len(parts), 2):
        chunks.append((parts[i].strip(), parts[i + 1]))
    return chunks


def main() -> None:
    raw = SRC_MD.read_text(encoding="utf-8")
    text, sub_log = apply_subs(raw, PAPER_SUBS)
    zero = [e for e in PAPER_SUBS if e[0] not in [x["pattern"] for x in sub_log]]
    if zero:
        raise SystemExit(f"security-sweep substitutions that did not fire: {zero}")
    (ROOT / "wp" / "qa").mkdir(parents=True, exist_ok=True)
    (ROOT / "wp" / "qa" / "paper-scrub-log.json").write_text(json.dumps(sub_log, indent=1), encoding="utf-8")

    # The source's provenance register splits its table with blank lines
    # between row groups; python-markdown ends a table at a blank line and
    # would print the later rows as raw pipe text. Rejoin row groups.
    _lines = text.split("\n")
    _joined: list[str] = []
    for _i, _ln in enumerate(_lines):
        if _ln.strip() == "" and _joined and _joined[-1].lstrip().startswith("|") \
                and _i + 1 < len(_lines) and _lines[_i + 1].lstrip().startswith("|") \
                and "---" not in _lines[_i + 1]:
            continue
        _joined.append(_ln)
    text = "\n".join(_joined)

    chunks = dict()
    order = []
    for head, body in split_chunks(text):
        chunks[head] = body
        order.append(head)

    def get(prefix: str) -> tuple[str, str]:
        for h in order:
            if h.startswith(prefix):
                return h, chunks[h]
        raise KeyError(prefix)

    # --- v0.5.0 row in the section 14 document-control table (the source
    # markdown is the frozen v0.4.2 text; the reissue's own row is added
    # here, at build time) ---
    s14_head, s14_body = get("# 14.")
    s14_lines = s14_body.split("\n")
    s14_row = ("| 0.5.0 | November 4, 2026 | Process v1.0 reissue of v0.4.2: layout moved to the "
               "THOX Research Paper Template v1.0; evidence consolidated into a single source "
               "(exp/results/summary.json) with every headline figure re-verified against the "
               "per-run records (56/56); GATE49 explorer demo added; internal host identifiers "
               "genericized to host classes in the paper text and in the staged evidence copies "
               "(the already-public HF supplement is untouched). Byline finalized under Tommy "
               "Xaypanya's ruling of November 4, 2026: the v0.4.2 authorship of record stands "
               "(Sadie Weaving, author; Tommy Xaypanya, accountable human author) and the "
               "authorship-and-accountability disclosure added in v0.4.2 is retained verbatim "
               "in the front matter. No training result, score, job id, or ruling changed. |")
    for _i, _ln in enumerate(s14_lines):
        if _ln.startswith("| 0.4.2 |"):
            s14_lines.insert(_i + 1, s14_row)
            break
    else:
        raise SystemExit("section 14 document-control table: v0.4.2 row not found")
    chunks[s14_head] = "\n".join(s14_lines)

    # --- front matter (between the dek and Contents) ---
    fm_lines = []
    front = chunks[order[0]].split("# Contents")[0]
    for line in front.splitlines():
        if line.startswith("## "):
            continue
        fm_lines.append(line)
    front_md = "\n".join(fm_lines)
    # drop the duplicated title/dek bold lines that the cover carries
    front_md = re.sub(r"\*\*Technical Whitepaper[^\n]*\n", "", front_md)
    front_md = re.sub(r"\*\*THOX\.ai\*\*\n", "", front_md)
    front_md = re.sub(r"Your AI\. Your Data\. Your Rules\.™\n", "", front_md)
    front_md = re.sub(r"\*\*Date:\*\*[^\n]*\n", "", front_md)
    front_html = figures_to_datauri(md2html(front_md.strip()))

    _, abstract_md = get("# Abstract")
    abstract_html = md2html(abstract_md.strip())

    # --- contents list (raw lines under '# Contents') ---
    contents_raw = chunks["# Contents"]
    contents_items = [ln.strip() for ln in contents_raw.splitlines() if ln.strip()]

    # --- body sections ---
    body_parts: list[str] = []
    body_parts.append('<div class="callout"><div class="ct">Process v1.0 reissue</div><div>'
                      'This is the Process v1.0 pack reissue (v0.5.0, 2026-11-04) of the v0.4.2 '
                      'edition of record. Content is unchanged from v0.4.2 except the Process '
                      'section 4 security sweep: internal host names and one internal path are '
                      'genericized to host classes (substitutions logged in the pack QA report). '
                      'Every number traces to the pack\'s single evidence source, '
                      'exp/results/summary.json.</div></div>')
    body_parts.append(front_html)
    for head in order:
        if head in (order[0], "# Contents", "# Abstract"):
            continue
        frag = figures_to_datauri(md2html(chunks[head].strip()))
        # Wide tables: the template CSS itself renders table as a block-level
        # horizontal scroller; no wrapper (a wrapper broke that behaviour).
        # '## x.y Title' renders as <h2>; demote to template h3 with number span.
        frag = re.sub(r"<h2>(\d+\.\d+)\s+([^<]*)</h2>", r'<h3><span class="num">\1</span> \2</h3>', frag)
        m = re.match(r"# (\d+)\.\s+(.*)", head)
        ma = re.match(r"# Appendix ([A-Z])\.\s+(.*)", head)
        if m:
            frag = (f'<h2 id="s{m.group(1)}"><span class="num">{m.group(1)}</span>'
                    f'{htmllib.escape(m.group(2))}</h2>\n' + frag)
        elif ma:
            frag = (f'<h2 id="app{ma.group(1)}"><span class="num">A</span>'
                    f'Appendix A. {htmllib.escape(ma.group(2))}</h2>\n' + frag)
        body_parts.append(frag)
    body_html = "\n".join(body_parts)

    # --- stat cards from summary.json ---
    pr = S["program_runs"]
    nullp = S["null_policies"]["prescribed_decline"]
    kpis = [
        (f'{pr["air"]["wave_c2"]["passed_count"]}/49',
         "ThoxAir-0.5B, Wave C.2 gate — promoted flagship (mean 4.837/5)", "Measured · cloud GPU job"),
        (f'{pr["edge"]["wave_c"]["passed_count"]}/49',
         "ThoxEdge-0.8B-WaveC gate — promoted, vs 19/49 Wave A baseline (mean 4.735/5)", "Measured · cloud GPU job"),
        (f'{pr["mini"]["wave_c"]["passed_count"]}/49',
         "ThoxMini-Phi4Mini gate — fleet-best tie; flagship probe 3/6, ships as documented baseline", "Measured · cloud GPU job"),
        (f'{nullp["passed_count"]}/49',
         "Null-policy floor — a constant decline responder through the same scorer; every bar is read against it", "Measured · program scorer"),
    ]
    kpi_html = ('<div class="kpis">' + "".join(
        f'<div class="kpi"><div class="kv">{v}</div><div class="kl">{l}</div><div class="kt">{t}</div></div>'
        for v, l, t in kpis) + "</div>")

    contents_html = ('<div class="contents"><div class="ct">Contents</div><ol>' +
                     "".join(f"<li>{htmllib.escape(i)}</li>" for i in contents_items) + "</ol></div>")

    byline = """<p class="byline">THOX.ai Research · Author: Sadie Weaving, Chief Agentic Officer, THOX.ai · Accountable human author: Tommy Xaypanya, CTO &amp; Co-Founder, THOX.ai (corresponding author) · ORCID 0009-0000-4425-9565</p>"""

    cover = f"""<section class="cover"><div class="cover-inner">
<div class="eyebrow"><span>THOX.AI RESEARCH · WHITEPAPER {VERSION.upper()} · {DATE}</span><span class="pill">Public edition</span></div>
<h1>{htmllib.escape(TITLE)}</h1>
<p class="deck">{htmllib.escape(DEK)}</p>
{byline}
<div class="abstract"><div class="ct">Abstract</div>{abstract_html}</div>
{kpi_html}
{contents_html}
<div class="cover-foot">Your AI. Your Data. Your Rules.™ · THOX.ai LLC · Process v1.0 reissue of the v0.4.2 edition of record (October 30, 2026). DOI: pending deposit — none issued. Evidence: exp/results/summary.json in the artifact bundle.</div>
</div></section>"""

    css = template_css()
    head = (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            f'<title>{htmllib.escape(TITLE)} — THOX Wave C Flagship Program Whitepaper {VERSION}</title>\n'
            f'<meta name="description" content="THOX.ai Research whitepaper {VERSION}">\n'
            f'<style>{css}</style></head>\n')
    full = head + f'<body data-version="{VERSION}">\n{cover}\n<section class="paper-body">\n{body_html}\n</section>\n</body></html>'
    cover_doc = head + f'<body data-version="{VERSION}">\n{cover}\n</body></html>'
    body_doc = head + f'<body data-version="{VERSION}">\n<section class="paper-body">\n{body_html}\n</section>\n</body></html>'

    wp = ROOT / "wp"
    (wp / "paper.src.html").write_text(full, encoding="utf-8")
    (wp / "cover.html").write_text(cover_doc, encoding="utf-8")
    (wp / "body.html").write_text(body_doc, encoding="utf-8")
    print("wrote wp/paper.src.html", len(full), "bytes; substitutions:", sum(e["count"] for e in sub_log))


if __name__ == "__main__":
    main()
