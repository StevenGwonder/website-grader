# Cloudflare & Bot-Blocking Detection Strategy

## The Problem
When curl_cffi hits a Cloudflare-protected site with JS challenge enabled, it receives
challenge HTML instead of the real page. The grader then parses this challenge page
as if it were the actual site content, finding no meta tags, no content, no schema,
and failing nearly every check — producing an F grade for a perfectly healthy site.

## Detection Strategy (3 layers)

### Layer 1: Response Body Detection
Check the HTML body for known Cloudflare challenge signatures:
- `cf-browser-verification` (Cloudflare JS challenge)
- `challenge-platform` (Cloudflare Turnstile)
- `cf_chl_opt` (Cloudflare challenge options)
- `/_cf_chl_` (Cloudflare challenge path)
- `cdn-cgi/challenge-platform` (Cloudflare challenge platform)
- `just a moment...` (Cloudflare generic challenge text)
- `Checking your browser` (Cloudflare generic challenge text)
- `DDoS protection by` (Cloudflare DDoS page)
- `Attention Required! | Cloudflare` (Cloudflare block page)

### Layer 2: Response Header Detection
Check response headers for:
- `cf-ray` header (present on all Cloudflare proxied responses)
- `cf-chl-bypass` header
- `server: cloudflare` header

### Layer 3: Status Code Detection
- HTTP 403 with Cloudflare body signatures
- HTTP 503 with Cloudflare body signatures

## Retry Strategy
When Cloudflare is detected:
1. Try `impersonate="chrome"` (default)
2. Try `impersonate="chrome110"`
3. Try `impersonate="safari15_5"`
4. Try `impersonate="edge99"`
5. If all fail, mark page as `blocked` in CrawlResult

## Scoring Impact
When a page is blocked:
- All checks that require page content → UNVERIFIED status
- UNVERIFIED checks are excluded from Health Score (like NOT_APPLICABLE)
- Coverage Score drops proportionally to blocked pages
- Overall grade shows "Limited Assessment" indicator
- The report clearly states the site was partially blocked
