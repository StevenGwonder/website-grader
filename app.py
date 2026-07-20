#!/usr/bin/env python3
"""
Website Grader — Micro-SaaS
A Flask web app that grades any website on 5 quality criteria.
Deploy on Heroku, Railway, PythonAnywhere, or any Python host.

Usage: python app.py (runs on port 5000)
"""

import json
import os
import re
from datetime import datetime
from flask import Flask, request, jsonify
import requests as req
from bs4 import BeautifulSoup
import resend

app = Flask(__name__)

# ─── Resend Configuration ─────────────────────────────────────────
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
resend.api_key = RESEND_API_KEY

# ─── Storage for email captures ──────────────────────────────────
EMAILS_FILE = "data/emails.json"
AUDIENCE_ID = os.environ.get("RESEND_AUDIENCE_ID", "")

def save_email(email, url, score):
    """Save email capture to Resend Contacts API + local JSON fallback."""
    # Always save locally as a fallback
    data = []
    if os.path.exists(EMAILS_FILE):
        with open(EMAILS_FILE) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    data.append({
        "email": email,
        "url": url,
        "score": score,
        "timestamp": datetime.now().isoformat()
    })
    with open(EMAILS_FILE, "w") as f:
        json.dump(data, f, indent=2)

    # Push to Resend Contacts if configured
    if RESEND_API_KEY and AUDIENCE_ID:
        try:
            resend.Contacts.create({
                "audience_id": AUDIENCE_ID,
                "email": email,
                "first_name": "",
                "last_name": "",
                "unsubscribed": False,
            })
        except Exception as e:
            print(f"Resend contact save failed (non-fatal): {e}")

# ─── Website Grading Engine ──────────────────────────────────────────

def fetch_page(url):
    """Fetch a webpage, trying HTTPS then HTTP. Returns (html, final_url, error)."""
    if not url.startswith("http"):
        url = "https://" + url
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    last_error = None
    for candidate in (url, url.replace("https://", "http://", 1)):
        try:
            resp = req.get(candidate, headers=headers, timeout=10, allow_redirects=True)
            return resp.text, resp.url, None
        except Exception as e:
            last_error = e
            continue
    return "", url, str(last_error)

def grade_website(url):
    """Grade a website on 5 criteria. Returns a report dict."""
    html, final_url, error = fetch_page(url)
    
    if error:
        return {
            "url": url,
            "final_url": url,
            "error": f"Could not reach website: {error}",
            "score": -1,
            "grade": "F",
            "checks": [],
            "recommendations": [],
            "timestamp": datetime.now().isoformat()
        }
    
    soup = BeautifulSoup(html, "html.parser")
    checks = []
    recommendations = []
    score = 0
    
    # ─── Check 1: Mobile Viewport ──────────────────────
    viewport = soup.find("meta", attrs={"name": "viewport"})
    viewport_pass = bool(viewport and viewport.get("content", ""))
    if viewport_pass:
        score += 1
        checks.append({"name": "Mobile Responsive", "icon": "✅", "detail": "Viewport meta tag detected — your site adapts to mobile screens."})
    else:
        checks.append({"name": "Mobile Responsive", "icon": "❌", "detail": "No viewport meta tag found. Google penalizes non-mobile sites and 60% of visitors are on mobile."})
        recommendations.append({
            "title": "Add a Mobile Viewport Tag",
            "detail": "Add this to your <head>: <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">. Without it, your site looks tiny and broken on phones. Google ranks mobile-friendly sites higher.",
            "difficulty": "Easy (1 min)",
            "impact": "Critical — affects 60%+ of visitors and Google ranking"
        })
    
    # ─── Check 2: Click-to-Call ─────────────────────────
    tel_links = soup.find_all("a", href=re.compile(r"^tel:"))
    tel_pass = len(tel_links) > 0
    if tel_pass:
        score += 1
        checks.append({"name": "Click-to-Call", "icon": "✅", "detail": f"Found {len(tel_links)} tap-to-call link(s). Mobile visitors can call you with one tap."})
    else:
        checks.append({"name": "Click-to-Call", "icon": "❌", "detail": "No tel: links found. Mobile visitors have to copy-paste your phone number to call you — most won't bother."})
        recommendations.append({
            "title": "Add Click-to-Call Links",
            "detail": "Make your phone number a clickable link: <a href=\"tel:+19515551234\">(951) 555-1234</a>. This is critical for service businesses — 70% of mobile searchers call directly from search results.",
            "difficulty": "Easy (5 min)",
            "impact": "High — can increase call volume 20-40%"
        })
    
    # ─── Check 3: Contact Page ──────────────────────────
    contact_links = soup.find_all("a", href=re.compile(r"contact", re.I))
    contact_section = soup.find(id=re.compile(r"contact", re.I))
    contact_class = soup.find(class_=re.compile(r"contact", re.I))
    contact_pass = len(contact_links) > 0 or contact_section or contact_class
    if contact_pass:
        score += 1
        checks.append({"name": "Contact Page", "icon": "✅", "detail": "Contact page or section found. Visitors can reach you."})
    else:
        checks.append({"name": "Contact Page", "icon": "❌", "detail": "No visible contact page link found. If customers can't find how to reach you, they'll go to a competitor."})
        recommendations.append({
            "title": "Add a Clear Contact Page",
            "detail": "Create a /contact page with your phone number, email, address, and a contact form. Link to it from your main navigation menu. Make it the easiest thing to find on your site.",
            "difficulty": "Medium (30 min)",
            "impact": "Critical — missing contact info = lost customers"
        })
    
    # ─── Check 4: Content Depth ─────────────────────────
    text = soup.get_text(strip=True)
    word_count = len(text.split())
    content_pass = word_count >= 200
    if content_pass:
        score += 1
        checks.append({"name": "Content Depth", "icon": "✅", "detail": f"{word_count} words of content found. Enough for Google to understand what you do."})
    else:
        checks.append({"name": "Content Depth", "icon": "❌", "detail": f"Only {word_count} words found. Thin content ranks poorly on Google and doesn't answer customer questions."})
        recommendations.append({
            "title": "Add More Content",
            "detail": f"Your site has only {word_count} words. Add at least 200-500 words describing your services, service area, hours, pricing, and FAQ. Google needs text to rank you — each page should answer 'What do you do? Where? How much? How fast?'",
            "difficulty": "Medium (1-2 hours)",
            "impact": "High — directly affects Google ranking"
        })
    
    # ─── Check 5: Booking or Live Chat ─────────────────
    booking_keywords = re.compile(r"book|schedule|appointment|reserve|booking|calendly|squarespace.*scheduling", re.I)
    chat_keywords = re.compile(r"chat|live.?chat|intercom|tawk|crisp|drift|olark|zendesk|messenger", re.I)
    booking_links = soup.find_all("a", href=booking_keywords)
    booking_text = soup.find_all(string=booking_keywords)
    chat_scripts = soup.find_all("script", src=re.compile(r"intercom|tawk|crisp|drift|olark|zendesk", re.I))
    chat_divs = soup.find_all(class_=re.compile(r"chat|widget", re.I))
    
    booking_pass = len(booking_links) > 0 or len(booking_text) > 0 or len(chat_scripts) > 0 or len(chat_divs) > 0
    if booking_pass:
        score += 1
        checks.append({"name": "Booking / Live Chat", "icon": "✅", "detail": "Found booking or chat functionality. Visitors can take action immediately."})
    else:
        checks.append({"name": "Booking / Live Chat", "icon": "❌", "detail": "No booking system or live chat detected. Visitors can browse but can't take action — you're losing leads to competitors with online booking."})
        recommendations.append({
            "title": "Add Online Booking or Live Chat",
            "detail": "Install a booking system (Calendly is free) or live chat widget (Tawk.to is free). Let visitors schedule an appointment or ask a question without picking up the phone. This alone can increase conversions 30-50%.",
            "difficulty": "Easy (15 min with Calendly or Tawk.to)",
            "impact": "High — captures visitors who won't call"
        })
    
    # ─── Grade Letter ──────────────────────────────────
    grade_map = {
        5: ("A", "Excellent — your website is working hard for you"),
        4: ("B", "Good — one improvement away from great"),
        3: ("C", "Average — several issues are costing you leads"),
        2: ("D", "Below average — your website is losing customers"),
        1: ("F", "Failing — your website is a liability, not an asset"),
        0: ("F", "Failing — your website is a liability, not an asset"),
        -1: ("F", "Website is down — you're invisible online"),
    }
    grade, summary = grade_map.get(score, ("F", "Website issues detected"))
    
    # Extract meta description and title for bonus info
    meta_desc = soup.find("meta", attrs={"name": "description"})
    page_title = soup.find("title")
    
    bonus_info = {
        "title": page_title.get_text(strip=True) if page_title else "No title found",
        "meta_description": meta_desc.get("content", "")[:200] if meta_desc else "No meta description found",
        "word_count": word_count,
        "has_ssl": final_url.startswith("https://"),
    }
    
    return {
        "url": url,
        "final_url": final_url,
        "error": None,
        "score": score,
        "grade": grade,
        "summary": summary,
        "checks": checks,
        "recommendations": recommendations,
        "bonus_info": bonus_info,
        "timestamp": datetime.now().isoformat()
    }

# ─── Templates (inline, no external deps) ────────────────────────────

BASE_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0b0f19;
    color: #f3f4f6;
    min-height: 100vh;
}
.gradient-bg {
    background: linear-gradient(135deg, #0b0f19 0%, #111827 50%, #0b0f19 100%);
    min-height: 100vh;
}
.container { max-width: 900px; margin: 0 auto; padding: 40px 20px; }
h1 { font-size: 2.8em; font-weight: 700; margin-bottom: 8px; 
    background: linear-gradient(135deg, #f97316 0%, #38bdf8 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.subtitle { font-size: 1.1em; color: #9ca3af; margin-bottom: 40px; }
.search-box {
    display: flex; gap: 0; margin-bottom: 30px;
    border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.5);
}
.search-box input {
    flex: 1; padding: 18px 24px; font-size: 1.1em;
    background: #111827; border: 1px solid #1f2937; color: #fff;
    border-right: none; border-radius: 12px 0 0 12px;
}
.search-box input:focus { outline: none; border-color: #38bdf8; }
.search-box button {
    padding: 18px 36px; font-size: 1.1em; font-weight: 600;
    background: linear-gradient(135deg, #f97316 0%, #38bdf8 100%);
    color: #0b0f19; border: none; cursor: pointer; transition: opacity 0.2s;
    border-radius: 0 12px 12px 0;
}
.search-box button:hover { opacity: 0.9; }
.search-box button:disabled { opacity: 0.5; cursor: default; }
.result-card {
    background: #111827; border: 1px solid #1f2937; border-radius: 16px;
    padding: 32px; margin-bottom: 24px;
}
.score-display { text-align: center; margin-bottom: 32px; }
.score-circle {
    display: inline-flex; align-items: center; justify-content: center;
    width: 120px; height: 120px; border-radius: 50%; font-size: 3.5em; font-weight: 800;
    margin-bottom: 12px;
}
.score-a { background: linear-gradient(135deg, #10b981, #059669); color: white; }
.score-b { background: linear-gradient(135deg, #84cc16, #65a30d); color: white; }
.score-c { background: linear-gradient(135deg, #f59e0b, #d97706); color: white; }
.score-d, .score-f { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; }
.score-summary { font-size: 1.2em; color: #9ca3af; }
.checks-list { margin-bottom: 32px; }
.check-item {
    display: flex; align-items: flex-start; gap: 14px; padding: 16px;
    border-bottom: 1px solid #1f2937;
}
.check-item:last-child { border-bottom: none; }
.check-icon { font-size: 1.5em; flex-shrink: 0; }
.check-name { font-weight: 600; margin-bottom: 4px; color: #f3f4f6; }
.check-detail { font-size: 0.9em; color: #9ca3af; }
.rec-card {
    background: #0b0f19; border: 1px solid #1f2937; border-left: 4px solid #f97316;
    border-radius: 8px; padding: 20px; margin-bottom: 16px;
}
.rec-title { font-weight: 700; color: #38bdf8; margin-bottom: 8px; }
.rec-detail { color: #9ca3af; line-height: 1.6; margin-bottom: 8px; }
.rec-meta { display: flex; gap: 20px; font-size: 0.85em; }
.rec-difficulty { color: #f97316; }
.rec-impact { color: #38bdf8; }
.email-capture {
    background: #0b0f19; border: 1px solid #1f2937; border-radius: 12px;
    padding: 28px; text-align: center; margin-top: 32px;
}
.email-capture h3 { margin-bottom: 8px; color: #f3f4f6; }
.email-capture p { color: #9ca3af; margin-bottom: 20px; font-size: 0.95em; }
.email-capture input {
    padding: 14px 20px; font-size: 1em; background: #111827;
    border: 1px solid #1f2937; color: #fff; border-radius: 8px; margin-right: 8px;
    width: 280px;
}
.email-capture button {
    padding: 14px 28px; font-size: 1em; font-weight: 600;
    background: linear-gradient(135deg, #f97316, #38bdf8); color: #0b0f19;
    border: none; border-radius: 8px; cursor: pointer;
}
.email-capture button:hover { opacity: 0.9; }
.bonus-info {
    display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 24px;
}
.info-pill {
    background: #0b0f19; border: 1px solid #1f2937; border-radius: 20px;
    padding: 8px 16px; font-size: 0.85em; color: #9ca3af;
}
.info-pill strong { color: #38bdf8; }
.loading { text-align: center; padding: 60px; color: #9ca3af; }
.loading .spinner {
    width: 40px; height: 40px; border: 4px solid #1f2937;
    border-top: 4px solid #f97316; border-radius: 50%;
    animation: spin 1s linear infinite; margin: 0 auto 20px;
}
@keyframes spin { 0% { transform: rotate(0); } 100% { transform: rotate(360deg); } }
.error-box { background: #2a1010; border: 1px solid #ef4444; border-radius: 12px; padding: 24px; margin-bottom: 24px; }
.error-box h3 { color: #ef4444; margin-bottom: 8px; }
footer { text-align: center; padding: 40px; color: #555; font-size: 0.85em; }
a { color: #38bdf8; text-decoration: none; }
a:hover { text-decoration: underline; }
"""

HOME_PAGE = """
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Website Grader — Free Instant Website Quality Report</title>
<style>BASE_CSS</style></head><body><div class="gradient-bg"><div class="container">
    <h1>Website Grader</h1>
    <p class="subtitle">Get an instant quality report for any website. Free.</p>
    <form action="/grade" method="post" class="search-box" id="gradeForm">
        <input type="text" name="url" placeholder="Enter your website URL (e.g., mybusiness.com)" required>
        <button type="submit">Grade It →</button>
    </form>
    <div class="result-card" style="text-align:center; padding:48px;">
        <h2 style="color:#aaa; font-size:1.3em; margin-bottom:24px;">What we check:</h2>
        <div class="bonus-info" style="justify-content:center;">
            <span class="info-pill">📱 Mobile Responsive</span>
            <span class="info-pill">📞 Click-to-Call</span>
            <span class="info-pill">📇 Contact Page</span>
            <span class="info-pill">📝 Content Depth</span>
            <span class="info-pill">💬 Booking / Chat</span>
        </div>
        <p style="color:#666; margin-top:24px; font-size:0.9em;">Powered by AI-driven web analysis. No signup required.</p>
    </div>
</div><footer>© 2026 Website Grader. Built for small businesses.</footer></div></body></html>
""".replace("BASE_CSS", BASE_CSS)

def render_result(report):
    """Render the result page from a report dict."""
    score = report["score"]
    grade = report["grade"].lower()
    score_class = f"score-{grade}"
    
    checks_html = ""
    for c in report["checks"]:
        checks_html += f"""
        <div class="check-item">
            <span class="check-icon">{c['icon']}</span>
            <div><div class="check-name">{c['name']}</div><div class="check-detail">{c['detail']}</div></div>
        </div>"""
    
    recs_html = ""
    if report["recommendations"]:
        recs_html = "<h2 style='color:#aaa; margin-bottom:20px;'>📋 Recommended Fixes</h2>"
        for r in report["recommendations"]:
            recs_html += f"""
            <div class="rec-card">
                <div class="rec-title">{r['title']}</div>
                <div class="rec-detail">{r['detail']}</div>
                <div class="rec-meta">
                    <span class="rec-difficulty">🔧 {r['difficulty']}</span>
                    <span class="rec-impact">📈 {r['impact']}</span>
                </div>
            </div>"""
    else:
        recs_html = "<div class='result-card' style='text-align:center;'><p style='color:#22c55e; font-size:1.2em;'>🎉 No critical issues found! Your website is in great shape.</p></div>"
    
    bi = report.get("bonus_info", {})
    bonus_html = ""
    if bi:
        ssl_text = "Yes" if bi.get("has_ssl") else "No"
        bonus_html = f"""
        <div class="bonus-info">
            <span class="info-pill"><strong>Title:</strong> {bi.get('title', 'N/A')[:50]}</span>
            <span class="info-pill"><strong>Words:</strong> {bi.get('word_count', 0)}</span>
            <span class="info-pill"><strong>SSL:</strong> {ssl_text}</span>
        </div>"""
    
    error_html = ""
    if report.get("error"):
        error_html = f"""
        <div class="error-box"><h3>⚠️ Warning</h3><p>{report['error']}</p></div>"""
    
    return f"""
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Website Grade: {report['grade']} — {report['url']}</title>
<style>BASE_CSS</style></head>
<body><div class="gradient-bg"><div class="container">
    <h1>Website Grader</h1>
    <p class="subtitle">Report for: <strong style="color:#6366f1;">{report['url']}</strong></p>
    {error_html}
    <div class="result-card">
        <div class="score-display">
            <div class="score-circle {score_class}">{report['grade']}</div>
            <div class="score-summary">{report.get('summary', '')}</div>
            <div style="color:#555; margin-top:8px;">Score: {score}/5</div>
        </div>
        {bonus_html}
        <div class="checks-list">
            <h2 style="color:#aaa; margin-bottom:20px;">🔍 Quality Checks</h2>
            {checks_html}
        </div>
    </div>
    {recs_html}
    <div class="email-capture">
        <h3>Want a detailed PDF report?</h3>
        <p>Enter your email and we'll send a full breakdown with fix instructions.</p>
        <form action="/capture" method="post">
            <input type="email" name="email" placeholder="your@email.com" required>
            <input type="hidden" name="url" value="{report['url']}">
            <input type="hidden" name="score" value="{score}">
            <button type="submit">Send Me the Report →</button>
        </form>
    </div>
    <div style="text-align:center; margin-top:30px;">
        <a href="/">← Grade another website</a>
    </div>
</div><footer>© 2026 Website Grader</footer></div></body></html>
""".replace("BASE_CSS", BASE_CSS)

# ─── Routes ──────────────────────────────────────────────────────────

@app.route("/")
def home():
    return HOME_PAGE

@app.route("/grade", methods=["POST"])
def grade():
    url = request.form.get("url", "").strip()
    if not url:
        return HOME_PAGE
    report = grade_website(url)
    return render_result(report)

@app.route("/capture", methods=["POST"])
def capture():
    email = request.form.get("email", "").strip()
    url = request.form.get("url", "")
    score = request.form.get("score", "")
    if email:
        save_email(email, url, score)
    return f"""
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Thanks!</title><style>{BASE_CSS}</style></head><body><div class="gradient-bg"><div class="container">
    <div class="result-card" style="text-align:center; padding:60px;">
        <h1 style="font-size:2em;">✅ Got it!</h1>
        <p style="color:#aaa; margin-top:16px; font-size:1.1em;">We'll send your detailed report to <strong style="color:#6366f1;">{email}</strong> within 24 hours.</p>
        <div style="margin-top:30px;"><a href="/" style="color:#6366f1;">← Grade another website</a></div>
    </div>
</div></div></body></html>"""

@app.route("/api/grade", methods=["GET", "POST"])
def api_grade():
    """API endpoint for programmatic access."""
    url = request.form.get("url") or request.args.get("url")
    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400
    report = grade_website(url)
    return jsonify(report)

@app.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)