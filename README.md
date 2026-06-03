# Website Grader

A micro-SaaS web app that grades any website on 5 quality criteria. Users enter their URL and get an instant report with actionable recommendations.

## What It Does

Enter any URL → get an instant grade (A-F) based on:
- 📱 Mobile responsive (viewport meta tag)
- 📞 Click-to-call (tel: links)
- 📇 Contact page present
- 📝 Content depth (200+ words)
- 💬 Booking or live chat functionality

Each failed check comes with a specific, actionable recommendation.

## Revenue Model

- **Free tier:** Grade any site, see score + pass/fail
- **Email capture:** Collect emails for "detailed PDF report" (lead gen)
- **Upsell:** Offer website fixes, SEO services, AI employee setup
- **API access:** Charge $9-29/mo for API access (programmatic grading)

## Quick Start

```bash
cd website-grader
pip install -r requirements.txt
python app.py
```

App runs on http://localhost:5000

## Deploy

### Heroku
```bash
cd website-grader
heroku create my-website-grader
git init && git add . && git commit -m "initial"
heroku git:push main
```

### Railway
```bash
cd website-grader
railway init
railway up
```

### PythonAnywhere
1. Upload files to /home/yourusername/website-grader/
2. Create a new web app (Flask)
3. Point WSGI to app.py

## API

```
GET /api/grade?url=example.com
POST /api/grade with form data: url=example.com

Returns JSON with score, grade, checks, recommendations.
```

## Tech Stack

- Flask (Python web framework)
- BeautifulSoup4 (HTML parsing)
- Requests (HTTP client)
- No database needed (emails stored in JSON file)

## License

Commercial — © 2026 North Web Pro