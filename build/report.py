#!/usr/bin/env python3
"""A shareable progress page: level over time, practice, and where it's hard.

    ./english report             writes me/reports/progress-<date>.html and opens it
    ./english report --json      the same numbers, for scripts

Safe to send to anyone: it carries numbers and grammar-point names only — never
journal text, never the sentences in errors.md. One self-contained HTML file
with no external requests, so it opens anywhere, offline, as an attachment.
"""

import argparse
import html
import json
import subprocess
import sys
from datetime import date, timedelta

from paths import CEFR, REPORTS, load_profile
from progress import (
    anki_stats, current_level, errors_per_100_by_month, journal_words, level_value,
    load_history, top_error_points,
)
from status import anki_state, compute

RETENTION_TARGET = 90  # FSRS's default desired retention


def gather() -> dict:
    profile = load_profile()
    today = date.today()
    status = compute()
    month_ago = today - timedelta(days=30)
    review_days = {d for d in anki_state(today)["review_days"] if d >= month_ago.isoformat()}
    writing_days = {d.isoformat() for d, n in journal_words().items() if d >= month_ago and n >= 30}
    return {
        "name": profile.get("name") or "",
        "date": today.isoformat(),
        "level": current_level(),
        "history": [{**e, "date": str(e["date"])} for e in load_history()],
        "streak": status["streak"],
        "practised_days_30": len(review_days | writing_days),
        "anki": anki_stats(30),
        "errors_per_100": errors_per_100_by_month(),
        "top_errors": top_error_points(60),
    }


# --- svg pieces --------------------------------------------------------------

esc = html.escape


def bar_path(x: float, y: float, w: float, h: float, r: float = 4, horizontal=False) -> str:
    """A bar with only its data end rounded, so it stays anchored to the baseline."""
    r = max(0, min(r, w / 2, h / 2) if not horizontal else min(r, h / 2, w / 2))
    if horizontal:  # baseline on the left, rounded at the right
        return (f"M{x},{y} H{x + w - r} Q{x + w},{y} {x + w},{y + r} V{y + h - r} "
                f"Q{x + w},{y + h} {x + w - r},{y + h} H{x} Z")
    return (f"M{x},{y + h} V{y + r} Q{x},{y} {x + r},{y} H{x + w - r} "
            f"Q{x + w},{y} {x + w},{y + r} V{y + h} Z")


def level_chart(history: list[dict]) -> str:
    W, H, L, R, T, B = 640, 230, 44, 16, 14, 30
    pw, ph = W - L - R, H - T - B
    days = [date.fromisoformat(e["date"]) for e in history]
    lo, hi = min(days), max(days)
    span = max((hi - lo).days, 1)

    def x(d: date) -> float:
        return L + pw / 2 if lo == hi else L + (d - lo).days / span * pw

    def y(level: str) -> float:
        return T + ph - (level_value(level) - 1) / (len(CEFR) - 1) * ph

    parts = []
    for lv in CEFR:
        parts.append(f'<line class="grid" x1="{L}" x2="{W - R}" y1="{y(lv):.1f}" y2="{y(lv):.1f}"/>')
        parts.append(f'<text class="axis" x="{L - 10}" y="{y(lv) + 4:.1f}" text-anchor="end">{lv}</text>')
    for d in sorted({lo, hi}):
        anchor = "middle" if lo == hi else ("start" if d == lo else "end")
        parts.append(f'<text class="axis" x="{x(d):.1f}" y="{H - 8}" text-anchor="{anchor}">'
                     f'{d.strftime("%-d %b %Y")}</text>')
    if len(history) > 1:
        pts = " ".join(f"{x(d):.1f},{y(e['overall']):.1f}" for d, e in zip(days, history))
        parts.append(f'<polyline class="line" points="{pts}"/>')
    for d, e in zip(days, history):
        cx, cy = x(d), y(e["overall"])
        if e["source"] == "efset":
            tip = f"{e['date']} · {e['overall']} · EF SET score {e.get('score')}"
            mark = (f'<rect class="mark" x="{cx - 5.5:.1f}" y="{cy - 5.5:.1f}" width="11" height="11" '
                    f'transform="rotate(45 {cx:.1f} {cy:.1f})"/>')
        else:
            tip = f"{e['date']} · {e['overall']} · estimate from /level"
            mark = f'<circle class="mark" cx="{cx:.1f}" cy="{cy:.1f}" r="5.5"/>'
        parts.append(f'<g data-tip="{esc(tip)}">{mark}'
                     f'<circle class="hit" cx="{cx:.1f}" cy="{cy:.1f}" r="14"/></g>')
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Level over time">'
            + "".join(parts) + "</svg>")


def errors_chart(months: list[dict]) -> str:
    W, H, L, R, T, B = 640, 200, 44, 16, 22, 30
    pw, ph = W - L - R, H - T - B
    top = max(m["rate"] for m in months) * 1.15 or 1
    slot = pw / len(months)
    bw = min(36, slot * 0.6)
    parts = [f'<line class="baseline" x1="{L}" x2="{W - R}" y1="{T + ph}" y2="{T + ph}"/>']
    for i, m in enumerate(months):
        h = m["rate"] / top * ph
        bx = L + i * slot + (slot - bw) / 2
        tip = f"{m['month']} · {m['rate']} per 100 words · {m['errors']} errors in {m['words']} words"
        parts.append(f'<g data-tip="{esc(tip)}"><path class="bar" d="{bar_path(bx, T + ph - h, bw, h)}"/>'
                     f'<rect class="hit" x="{L + i * slot:.1f}" y="{T}" width="{slot:.1f}" height="{ph}"/></g>')
        label = date.fromisoformat(m["month"] + "-01").strftime("%b %y")
        parts.append(f'<text class="axis" x="{bx + bw / 2:.1f}" y="{H - 8}" text-anchor="middle">{label}</text>')
        if i == len(months) - 1:  # label only the latest; hover gives the rest
            parts.append(f'<text class="value" x="{bx + bw / 2:.1f}" y="{T + ph - h - 6:.1f}" '
                         f'text-anchor="middle">{m["rate"]}</text>')
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Errors per 100 words by month">'
            + "".join(parts) + "</svg>")


def retention_chart(topics: list[dict]) -> str:
    row, L, R, T = 26, 230, 52, 18
    W = 640
    pw = W - L - R
    H = T + row * len(topics) + 8
    tx = L + RETENTION_TARGET / 100 * pw
    # Reference line first, so bars and value labels paint over it.
    parts = [f'<line class="ref" x1="{tx:.1f}" x2="{tx:.1f}" y1="{T - 4}" y2="{H - 4}"/>']
    for i, t in enumerate(topics):
        y0 = T + i * row
        w = t["retention"] / 100 * pw
        name = t["topic"] if len(t["topic"]) <= 34 else t["topic"][:33] + "…"
        tip = f"{t['topic']} · {t['retention']}% passed · {t['reviews']} reviews"
        parts.append(f'<text class="label" x="{L - 10}" y="{y0 + 15}" text-anchor="end">{esc(name)}</text>')
        parts.append(f'<g data-tip="{esc(tip)}"><path class="bar" d="{bar_path(L, y0 + 5, w, 14, horizontal=True)}"/>'
                     f'<rect class="hit" x="0" y="{y0}" width="{W}" height="{row}"/></g>')
        parts.append(f'<text class="value" x="{L + w + 6:.1f}" y="{y0 + 16}">{t["retention"]:.0f}%</text>')
    parts.append(f'<text class="axis" x="{tx:.1f}" y="{T - 7}" text-anchor="middle">target {RETENTION_TARGET}%</text>')
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Review success by topic">'
            + "".join(parts) + "</svg>")


# --- page --------------------------------------------------------------------

CSS = """
:root {
  color-scheme: light;
  --surface: #fcfcfb; --card: #ffffff; --border: #e6e5e0;
  --text-primary: #0b0b0b; --text-secondary: #52514e; --text-muted: #77766f;
  --series-1: #2a78d6; --grid: #ecebe7;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --surface: #1a1a19; --card: #222220; --border: #34332f;
    --text-primary: #ffffff; --text-secondary: #c3c2b7; --text-muted: #9a998f;
    --series-1: #3987e5; --grid: #2e2d2a;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --surface: #1a1a19; --card: #222220; --border: #34332f;
  --text-primary: #ffffff; --text-secondary: #c3c2b7; --text-muted: #9a998f;
  --series-1: #3987e5; --grid: #2e2d2a;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--surface); color: var(--text-primary);
  font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }
main { max-width: 720px; margin: 0 auto; padding: 32px 16px 48px; }
h1 { font-size: 26px; margin: 0 0 4px; letter-spacing: -0.01em; }
h2 { font-size: 16px; margin: 0 0 2px; }
.sub, .caption { color: var(--text-secondary); margin: 0; }
.caption { font-size: 13px; margin-bottom: 12px; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 12px; margin: 24px 0; }
.tile, section { background: var(--card); border: 1px solid var(--border); border-radius: 12px; }
.tile { padding: 14px 16px; }
.tile .k { font-size: 12px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: .05em; }
.tile .v { font-size: 28px; font-weight: 650; margin-top: 2px; font-variant-numeric: tabular-nums; }
.tile .n { font-size: 12px; color: var(--text-muted); }
section { padding: 18px 18px 14px; margin-bottom: 16px; }
svg { width: 100%; height: auto; display: block; overflow: visible; }
svg text { font: 12px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.axis { fill: var(--text-muted); }
.label { fill: var(--text-secondary); }
.value { fill: var(--text-primary); font-weight: 600;
  paint-order: stroke; stroke: var(--card); stroke-width: 4px; stroke-linejoin: round; }
.grid { stroke: var(--grid); stroke-width: 1; }
.baseline { stroke: var(--border); stroke-width: 1; }
.ref { stroke: var(--text-muted); stroke-width: 1; stroke-dasharray: 3 3; }
.line { fill: none; stroke: var(--series-1); stroke-width: 2; }
.mark { fill: var(--series-1); stroke: var(--card); stroke-width: 2; }
.bar { fill: var(--series-1); }
.hit { fill: transparent; }
[data-tip] { cursor: default; }
.legend { display: flex; gap: 18px; font-size: 13px; color: var(--text-secondary); margin: 0 0 8px; }
.legend svg { width: 12px; height: 12px; display: inline-block; vertical-align: -1px; margin-right: 6px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; font-variant-numeric: tabular-nums; }
td, th { text-align: left; padding: 6px 0; border-top: 1px solid var(--border); }
th { color: var(--text-secondary); font-weight: 500; }
td.num, th.num { text-align: right; }
details { margin-top: 10px; font-size: 13px; color: var(--text-secondary); }
summary { cursor: pointer; }
.empty { color: var(--text-muted); font-size: 14px; margin: 8px 0 4px; }
footer { color: var(--text-muted); font-size: 12px; margin-top: 24px; }
#tip { position: fixed; pointer-events: none; background: var(--text-primary); color: var(--surface);
  font-size: 12px; padding: 6px 8px; border-radius: 6px; opacity: 0; transition: opacity .1s;
  max-width: 260px; z-index: 10; }
"""

TOOLTIP_JS = """
const tip = document.getElementById('tip');
document.querySelectorAll('[data-tip]').forEach(el => {
  el.addEventListener('mousemove', e => {
    tip.textContent = el.dataset.tip; tip.style.opacity = 1;
    const x = Math.min(e.clientX + 14, innerWidth - tip.offsetWidth - 8);
    tip.style.left = x + 'px'; tip.style.top = (e.clientY + 14) + 'px';
  });
  el.addEventListener('mouseleave', () => { tip.style.opacity = 0; });
});
"""


def table(headers: list[str], rows: list[list], numeric: set[int] = frozenset()) -> str:
    head = "".join(f'<th class="{"num" if i in numeric else ""}">{esc(h)}</th>' for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(f'<td class="{"num" if i in numeric else ""}">{esc(str(c))}</td>'
                         for i, c in enumerate(r)) + "</tr>"
        for r in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def render(d: dict) -> str:
    lv, anki = d["level"], d["anki"]
    who = f"{esc(d['name'])}’s English" if d["name"] else "English progress"
    if lv:
        level_note = f"EF SET score {lv['score']}" if lv["source"] == "efset" else "estimate from /level"
        level_tile = (lv["overall"], level_note)
    else:
        level_tile = ("—", "not measured yet")
    learned = f"{anki['learned']}" if not anki["error"] else "—"
    tiles = [
        ("Level", *level_tile),
        ("Streak", f"{d['streak']}", "days in a row, all three steps"),
        ("Practised", f"{d['practised_days_30']}", "of the last 30 days"),
        ("Cards learned", learned, f"of {anki['total']} in the deck" if anki["total"] else ""),
        ("Reviews passed", f"{anki['retention']:.0f}%" if anki["retention"] is not None else "—",
         "last 30 days"),
    ]
    out = [f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>English Progress Report</title><style>{CSS}</style></head><body><main>
<h1>{who}</h1><p class="sub">Progress report · {date.fromisoformat(d['date']).strftime('%-d %B %Y')}</p>
<div class="tiles">"""]
    for k, v, n in tiles:
        out.append(f'<div class="tile"><div class="k">{k}</div><div class="v">{esc(v)}</div>'
                   f'<div class="n">{esc(n)}</div></div>')
    out.append("</div>")

    # Level over time
    out.append('<section><h2>Level over time</h2>'
               '<p class="caption">CEFR, from A1 (beginner) to C2 (mastery).</p>')
    if d["history"]:
        out.append('<div class="legend">'
                   '<span><svg viewBox="0 0 12 12"><circle cx="6" cy="6" r="5" fill="var(--series-1)"/></svg>estimate from /level</span>'
                   '<span><svg viewBox="0 0 12 12"><rect x="2" y="2" width="8" height="8" fill="var(--series-1)" transform="rotate(45 6 6)"/></svg>EF SET test score</span>'
                   '</div>')
        out.append(level_chart(d["history"]))
        out.append("<details><summary>Show as a table</summary>" + table(
            ["Date", "Level", "Source"],
            [[e["date"], e["overall"],
              f"EF SET {e.get('score')}" if e["source"] == "efset" else "/level estimate"]
             for e in d["history"]]) + "</details>")
    else:
        out.append('<p class="empty">No level recorded yet. Run /level in Claude Code, or take the free '
                   'EF SET test and record it with ./english level --efset &lt;score&gt;.</p>')
    out.append("</section>")

    # Writing accuracy
    months = d["errors_per_100"]
    out.append('<section><h2>Errors per 100 words written</h2>'
               '<p class="caption">From corrected journal entries. Lower is better — though more '
               'ambitious writing pushes it up, so read the trend, not one month.</p>')
    if months:
        out.append(errors_chart(months))
        out.append("<details><summary>Show as a table</summary>" + table(
            ["Month", "Words", "Errors", "Per 100 words"],
            [[m["month"], m["words"], m["errors"], m["rate"]] for m in months], {1, 2, 3}) + "</details>")
    else:
        out.append('<p class="empty">Not enough corrected writing yet (needs 100+ words in a month).</p>')
    out.append("</section>")

    # Retention by topic
    topics = [t for t in anki["by_topic"] if t["reviews"] >= 10]
    out.append('<section><h2>Review success by topic</h2>'
               '<p class="caption">Share of Anki reviews answered correctly in the last 30 days, '
               'hardest first. Topics with fewer than 10 reviews are left out.</p>')
    if topics:
        out.append(retention_chart(topics))
        out.append("<details><summary>Show as a table</summary>" + table(
            ["Topic", "Passed", "Reviews"],
            [[t["topic"], f"{t['retention']}%", t["reviews"]] for t in topics], {1, 2}) + "</details>")
    else:
        out.append(f'<p class="empty">{esc(anki["error"] or "Not enough reviews in the last 30 days yet.")}</p>')
    out.append("</section>")

    # Recurring errors
    out.append('<section><h2>What keeps coming back</h2>'
               '<p class="caption">Grammar points with the most corrections in the last 60 days.</p>')
    if d["top_errors"]:
        out.append(table(["Grammar point", "Corrections"],
                         [[p, n] for p, n in d["top_errors"]], {1}))
    else:
        out.append('<p class="empty">No corrections logged in the last 60 days.</p>')
    out.append("</section>")

    out.append("<footer>Contains numbers and topic names only — no journal text or corrected "
               "sentences. Levels marked “estimate” come from a short Claude-run placement "
               "(about ±half a band); EF SET scores are test results.</footer>")
    out.append(f'</main><div id="tip" role="tooltip"></div><script>{TOOLTIP_JS}</script></body></html>')
    return "".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="print the numbers instead")
    ap.add_argument("--no-open", action="store_true", help="write the file, don't open it")
    args = ap.parse_args()

    data = gather()
    if args.json:
        print(json.dumps(data, indent=2, default=str))
        return 0
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / f"progress-{data['date']}.html"
    path.write_text(render(data))
    print(f"Wrote {path}")
    print("It holds numbers and topic names only — safe to send as an attachment.")
    if not args.no_open:
        subprocess.run(["open", str(path)], check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
