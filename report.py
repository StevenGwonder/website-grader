#!/usr/bin/env python3
"""HTML report generator — self-contained, NWP branded, printable."""
from checks.base import Severity

# NWP brand colors
BG = "#0a0a0a"
CARD = "#1a1a2e"
BORDER = "#2a2a4e"
ORANGE = "#D97548"
BLUE = "#60CFF4"
TEXT = "#e0e0e8"
MUTED = "#888"

SEVERITY_COLORS = {
    Severity.CRITICAL: "#ef4444",
    Severity.HIGH: "#f59e0b",
    Severity.MEDIUM: "#60CFF4",
    Severity.LOW: "#888",
    Severity.INFO: "#555",
}

def _score_color(score):
    if score >= 80: return "#22c55e"
    if score >= 60: return "#f59e0b"
    if score >= 40: return ORANGE
    return "#ef4444"

def _grade_color(grade):
    return {"A": "#22c55e", "B": "#84cc16", "C": "#f59e0b", "D": ORANGE, "F": "#ef4444"}.get(grade, "#ef4444")

def _bar(label, score, weight):
    color = _score_color(score)
    return f"""
    <div class="bar-row">
      <span class="bar-label">{label} <small>({weight}%)</small></span>
      <div class="bar-track"><div class="bar-fill" style="width:{score}%;background:{color}"></div></div>
      <span class="bar-score">{score}</span>
    </div>"""

def _check_row(r):
    icon = "✅" if r.passed else "❌"
    color = SEVERITY_COLORS.get(r.severity, "#888")
    fix = ""
    if r.fix_code and not r.passed:
        fix = f'<details class="fix"><summary>Fix code</summary><pre>{r.fix_code}</pre></details>'
    return f"""
    <div class="check">
      <span class="check-icon">{icon}</span>
      <div>
        <div class="check-name"><span class="sev-dot" style="background:{color}"></span>{r.check_name}</div>
        <div class="check-detail">{r.detail}</div>
        {f'<div class="check-rec">{r.recommendation}</div>' if r.recommendation and not r.passed else ''}
        {fix}
      </div>
    </div>"""

def _nap_table(crawl_result, all_results):
    """NAP consistency table from local SEO check data."""
    nap_result = next((r for r in all_results if r.check_id == "local_seo_nap_consistency"), None)
    if not nap_result or not nap_result.data.get("nap_per_page"):
        return ""
    rows = ""
    for url, nap in nap_result.data["nap_per_page"].items():
        short_url = url.replace("https://", "").replace("http://", "")[:40]
        rows += f"<tr><td>{short_url}</td><td>{nap.get('name') or '—'}</td><td>{nap.get('phone') or '—'}</td><td>{nap.get('address') or '—'[:40]}</td></tr>"
    return f"""
    <h2>NAP Consistency</h2>
    <table class="nap-table"><tr><th>Page</th><th>Name</th><th>Phone</th><th>Address</th></tr>{rows}</table>"""

def _perf_table(crawl_result):
    """Performance metrics from homepage."""
    hp = crawl_result.homepage
    if not hp:
        return ""
    size_kb = len(hp.html) // 1024
    encoding = hp.headers.get("content-encoding", "none")
    cache = "yes" if hp.headers.get("cache-control") else "no"
    return f"""
    <h2>Performance Metrics</h2>
    <table class="perf-table">
      <tr><td>TTFB</td><td>{hp.ttfb_ms:.0f}ms</td></tr>
      <tr><td>Page Weight</td><td>{size_kb}KB</td></tr>
      <tr><td>Compression</td><td>{encoding}</td></tr>
      <tr><td>Cache Headers</td><td>{cache}</td></tr>
    </table>"""

def _action_plan(all_results):
    """Top 10 prioritized fixes sorted by severity weight / effort."""
    sev_weight = {Severity.CRITICAL: 4, Severity.HIGH: 3, Severity.MEDIUM: 2, Severity.LOW: 1, Severity.INFO: 0.5}
    failed = [r for r in all_results if not r.passed]
    # Sort by severity weight descending
    failed.sort(key=lambda r: sev_weight.get(r.severity, 0), reverse=True)
    top = failed[:10]
    if not top:
        return '<div class="card"><p style="color:#22c55e;font-size:1.2em">🎉 No critical issues found!</p></div>'
    items = ""
    for i, r in enumerate(top, 1):
        items += f'<div class="action-item"><span class="action-num">{i}</span><div><strong>{r.check_name}</strong> — {r.detail}<br><small>{r.recommendation}</small></div></div>'
    return f'<h2>Prioritized Action Plan</h2><div class="action-list">{items}</div>'

def generate_report(crawl_result, all_results, score_data, fixes, url):
    """Generate self-contained HTML report."""
    grade = score_data["grade"]
    score = score_data["overall_score"]
    gcolor = _grade_color(grade)
    cat_bars = "".join(_bar(cat, d["score"], d["weight"]) for cat, d in score_data["categories"].items())
    checks_html = "".join(_check_row(r) for r in all_results)
    nap = _nap_table(crawl_result, all_results)
    perf = _perf_table(crawl_result)
    plan = _action_plan(all_results)
    failed_count = sum(1 for r in all_results if not r.passed)
    total_count = len(all_results)
    date = crawl_result.homepage.headers.get("date", "") if crawl_result.homepage else ""

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Website Audit: {url} — Score {score}/100</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:{BG}; color:{TEXT}; line-height:1.6 }}
.container {{ max-width:900px; margin:0 auto; padding:40px 20px }}
h1 {{ font-size:2.4em; color:{ORANGE}; margin-bottom:4px }}
h2 {{ font-size:1.3em; color:{BLUE}; margin:24px 0 12px }}
.subtitle {{ color:{MUTED}; margin-bottom:24px }}
.card {{ background:{CARD}; border:1px solid {BORDER}; border-radius:12px; padding:24px; margin-bottom:20px }}
.score-box {{ text-align:center; margin-bottom:20px }}
.score-num {{ font-size:3.5em; font-weight:800; color:{gcolor} }}
.score-grade {{ font-size:2em; font-weight:700; color:{gcolor} }}
.score-meta {{ color:{MUTED}; margin-top:8px }}
.bar-row {{ display:flex; align-items:center; gap:12px; margin-bottom:8px }}
.bar-label {{ width:180px; font-size:0.9em; text-align:right }}
.bar-label small {{ color:{MUTED} }}
.bar-track {{ flex:1; background:{BORDER}; border-radius:8px; height:24px; overflow:hidden }}
.bar-fill {{ height:100%; border-radius:8px; transition:width 0.3s }}
.bar-score {{ width:40px; text-align:left; font-weight:600 }}
.check {{ display:flex; gap:14px; padding:14px 0; border-bottom:1px solid {BORDER} }}
.check:last-child {{ border-bottom:none }}
.check-icon {{ font-size:1.4em; flex-shrink:0 }}
.check-name {{ font-weight:600; margin-bottom:4px; display:flex; align-items:center; gap:8px }}
.sev-dot {{ width:8px; height:8px; border-radius:50%; display:inline-block }}
.check-detail {{ font-size:0.9em; color:{MUTED}; margin-bottom:4px }}
.check-rec {{ font-size:0.85em; color:{BLUE}; margin-top:4px }}
.fix {{ margin-top:8px }}
.fix summary {{ cursor:pointer; color:{ORANGE}; font-size:0.85em }}
.fix pre {{ background:{BG}; border:1px solid {BORDER}; border-radius:8px; padding:12px; overflow-x:auto; font-size:0.8em; margin-top:8px }}
table {{ width:100%; border-collapse:collapse; margin-bottom:20px }}
th,td {{ padding:10px; text-align:left; border-bottom:1px solid {BORDER}; font-size:0.9em }}
th {{ color:{BLUE} }}
.nap-table td, .perf-table td {{ font-size:0.85em }}
.action-list {{ margin-top:12px }}
.action-item {{ display:flex; gap:14px; padding:12px 0; border-bottom:1px solid {BORDER} }}
.action-num {{ font-size:1.5em; font-weight:800; color:{ORANGE}; flex-shrink:0; width:30px }}
footer {{ text-align:center; padding:30px; color:#555; font-size:0.85em }}
a {{ color:{BLUE}; text-decoration:none }}
@media print {{ body {{ background:white; color:black }} .card {{ border:1px solid #ccc }} }}
</style></head><body><div class="container">
<h1>Website Audit Report</h1>
<p class="subtitle">{url} — {date or 'Generated ' + __import__('datetime').datetime.now().strftime('%Y-%m-%d')}</p>

<div class="card score-box">
  <div class="score-num">{score}<span style="font-size:0.4em;color:{MUTED}">/100</span></div>
  <div class="score-grade">Grade {grade}</div>
  <div class="score-meta">{total_count - failed_count}/{total_count} checks passed</div>
</div>

<div class="card">
  <h2>Score Breakdown</h2>
  {cat_bars}
</div>

<div class="card">
  {plan}
</div>

{f'<div class="card">{nap}</div>' if nap else ''}
{f'<div class="card">{perf}</div>' if perf else ''}

<div class="card">
  <h2>All Checks ({total_count})</h2>
  {checks_html}
</div>

<footer>Powered by <strong style="color:{ORANGE}">North Web Pro</strong> — Your guide in the digital wilderness</footer>
</div></body></html>"""