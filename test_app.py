#!/usr/bin/env python3
"""
Smoke tests for website-grader app.py
Tests all routes and the grading engine without real network calls.
"""
import json
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

import pytest

# Make sure we import from this dir
sys.path.insert(0, os.path.dirname(__file__))
import app as wg


# ─── Fixtures ───────────────────────────────────────────────────

SAMPLE_HTML_GOOD = """
<!DOCTYPE html><html><head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="A great plumbing service in Murrieta.">
<title>Best Plumbing — Murrieta CA</title>
</head><body>
<nav><a href="/contact">Contact Us</a></nav>
<main>
<h1>Welcome to Best Plumbing — Murrieta's Trusted Plumbers Since 2010</h1>
<p>We are the best plumbers in Murrieta, California. Serving the area since 2010.
We fix leaks, install water heaters, and handle emergencies 24/7.
Call us today for a free quote. Our team is licensed and insured.
We serve all of Riverside County including Temecula, Wildomar, and Lake Elsinore.
Our services include drain cleaning, pipe repair, water heater installation,
leak detection, sewer line repair, bathroom remodeling, kitchen plumbing,
garbage disposal repair, faucet installation, toilet repair, and more.
We offer competitive pricing and same-day service in most cases.
Our trucks are fully stocked so we can complete most jobs in one visit.
We are family owned and operated. Licensed #12345 bonded and insured.</p>
<h2>Our Services</h2>
<p>We offer a full range of residential and commercial plumbing services.
From simple faucet repairs to complete sewer line replacements, we do it all.
Our experienced technicians use the latest tools and technology to diagnose
and fix problems fast. We stand behind every job with a satisfaction guarantee.
Emergency plumbing service is available 24 hours a day, 7 days a week.
No job is too big or too small. We serve homeowners, businesses, and
property managers throughout the Inland Empire. Free estimates available.</p>
<h2>Service Area</h2>
<p>We proudly serve Murrieta, Temecula, Wildomar, Lake Elsinore, Menifee,
Sun City, Winchester, French Valley, Elsinore, Canyon Lake, and surrounding
areas in Riverside County, California. Fast response times and fair prices.</p>
<p>Call us at <a href="tel:+195****1234">(951) 555-1234</a> for a free estimate.</p>
</main>
<script src="https://www.tawk.to/widget.js"></script>
</body></html>
"""

SAMPLE_HTML_BAD = """
<!DOCTYPE html><html><head><title>Bad Site</title></head><body>
<p>Hi</p>
</body></html>
"""

MOCK_RESPONSE_GOOD = MagicMock(
    text=SAMPLE_HTML_GOOD,
    url="https://bestplumbing.example.com",
    status_code=200,
)
MOCK_RESPONSE_BAD = MagicMock(
    text=SAMPLE_HTML_BAD,
    url="https://badsite.example.com",
    status_code=200,
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Flask test client with emails.json in a temp dir."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(wg, "EMAILS_FILE", str(tmp_path / "emails.json"))
    wg.app.config["TESTING"] = True
    with wg.app.test_client() as c:
        yield c


# ─── Route Tests ────────────────────────────────────────────────

def test_home_page(client):
    """GET / returns 200 and contains the title."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Website Grader" in resp.data
    assert b"Grade It" in resp.data


def test_health(client):
    """GET /health returns JSON ok."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_api_missing_url(client):
    """GET /api/grade without url returns 400."""
    resp = client.get("/api/grade")
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


@patch("app.req.get", return_value=MOCK_RESPONSE_GOOD)
def test_api_grade_good_site(mock_get, client):
    """GET /api/grade?url=... returns JSON report for a good site."""
    resp = client.get("/api/grade?url=bestplumbing.example.com")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["error"] is None
    assert data["score"] == 5
    assert data["grade"] == "A"
    assert len(data["checks"]) == 5
    # Should have 0 recommendations (all pass)
    assert len(data["recommendations"]) == 0
    assert data["bonus_info"]["has_ssl"] is True


@patch("app.req.get", return_value=MOCK_RESPONSE_BAD)
def test_api_grade_bad_site(mock_get, client):
    """GET /api/grade?url=... returns JSON report for a bad site."""
    resp = client.get("/api/grade?url=badsite.example.com")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["error"] is None
    assert data["score"] == 0
    assert data["grade"] == "F"
    # All 5 should fail → 5 recommendations
    assert len(data["recommendations"]) == 5


@patch("app.req.get", side_effect=Exception("Connection refused"))
def test_api_grade_dead_site(mock_get, client):
    """GET /api/grade for unreachable site returns error report."""
    resp = client.get("/api/grade?url=dead.example.com")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["score"] == -1
    assert data["grade"] == "F"
    assert "Could not reach" in data["error"]


@patch("app.req.get", return_value=MOCK_RESPONSE_GOOD)
def test_grade_form_post(mock_get, client):
    """POST /grade returns HTML result page."""
    resp = client.post("/grade", data={"url": "bestplumbing.example.com"})
    assert resp.status_code == 200
    assert b"score-circle" in resp.data
    assert b"score-a" in resp.data


def test_grade_form_empty(client):
    """POST /grade with empty url returns home page."""
    resp = client.post("/grade", data={"url": ""})
    assert resp.status_code == 200
    assert b"Website Grader" in resp.data


def test_capture_email(client):
    """POST /capture saves email and returns thank you page."""
    resp = client.post("/capture", data={
        "email": "test@example.com",
        "url": "https://example.com",
        "score": "3",
    })
    assert resp.status_code == 200
    assert b"test@example.com" in resp.data
    # Verify email was saved
    with open(wg.EMAILS_FILE) as f:
        emails = json.load(f)
    assert len(emails) == 1
    assert emails[0]["email"] == "test@example.com"
    assert emails[0]["url"] == "https://example.com"
    assert emails[0]["score"] == "3"


def test_capture_no_email(client):
    """POST /capture without email still works."""
    resp = client.post("/capture", data={"email": "", "url": "", "score": ""})
    assert resp.status_code == 200


# ─── Grading Engine Unit Tests ─────────────────────────────────

def test_grade_website_all_pass():
    """grade_website returns score 5 for a site passing all checks."""
    with patch("app.req.get", return_value=MOCK_RESPONSE_GOOD):
        report = wg.grade_website("bestplumbing.example.com")
    assert report["score"] == 5
    assert report["grade"] == "A"
    assert report["error"] is None
    assert len(report["checks"]) == 5
    assert all(c["icon"] == "✅" for c in report["checks"])


def test_grade_website_all_fail():
    """grade_website returns score 0 for a minimal site."""
    with patch("app.req.get", return_value=MOCK_RESPONSE_BAD):
        report = wg.grade_website("badsite.example.com")
    assert report["score"] == 0
    assert report["grade"] == "F"
    assert len(report["recommendations"]) == 5


def test_grade_website_unreachable():
    """grade_website handles unreachable URLs gracefully."""
    with patch("app.req.get", side_effect=Exception("timeout")):
        report = wg.grade_website("https://dead.example.com")
    assert report["score"] == -1
    assert report["grade"] == "F"
    assert "Could not reach" in report["error"]


def test_save_email_creates_file(tmp_path, monkeypatch):
    """save_email creates emails.json and appends correctly."""
    email_file = str(tmp_path / "emails.json")
    monkeypatch.setattr(wg, "EMAILS_FILE", email_file)
    wg.save_email("a@test.com", "https://a.com", 5)
    wg.save_email("b@test.com", "https://b.com", 3)
    with open(email_file) as f:
        data = json.load(f)
    assert len(data) == 2
    assert data[0]["email"] == "a@test.com"
    assert data[1]["email"] == "b@test.com"


def test_save_email_corrupt_file(tmp_path, monkeypatch):
    """save_email handles corrupt emails.json gracefully."""
    email_file = str(tmp_path / "emails.json")
    with open(email_file, "w") as f:
        f.write("not valid json{{{")
    monkeypatch.setattr(wg, "EMAILS_FILE", email_file)
    wg.save_email("test@example.com", "https://example.com", 4)
    with open(email_file) as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["email"] == "test@example.com"


# ─── Template Rendering Tests ──────────────────────────────────

@patch("app.req.get", return_value=MOCK_RESPONSE_GOOD)
def test_result_page_has_css(mock_get, client):
    """Result page has actual CSS injected, not literal 'BASE_CSS' string."""
    resp = client.post("/grade", data={"url": "bestplumbing.example.com"})
    assert resp.status_code == 200
    # BASE_CSS should have been replaced — no literal placeholder
    assert b"BASE_CSS" not in resp.data
    # Should have actual CSS rules
    assert b"font-family" in resp.data
    assert b"gradient-bg" in resp.data


def test_home_page_has_css(client):
    """Home page has CSS injected, not literal 'BASE_CSS'."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"BASE_CSS" not in resp.data
    assert b"font-family" in resp.data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])