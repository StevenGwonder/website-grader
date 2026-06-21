# Sprint Plan: Fix Remaining Check Accuracy Issues

## Target: 6 tasks, each <150 lines, Devstral 24b compatible

---

## Task 1: Fix readability — content-only extraction + better syllable counting

**File**: `checks/content.py` — `_check_readability()`

**Problem**: Flesch score 18.9 is absurdly low for standard construction site copy.
Root cause: `soup.get_text()` includes navigation labels, button text, footer links,
and short fragments like "Get Started", "View Our Work", "BBB A+" that inflate the
word count without adding sentences. These fragments dilute the sentence count and
make avg-words-per-sentence look worse than it is. Also, the syllable counter uses
raw vowel-group counting which overcounts (e.g. "reality" = 2 groups but 3 syllables).

**Fix**:
1. Extract text only from content tags: `['p', 'h1', 'h2', 'h3', 'h4', 'li', 'td', 'blockquote']`
2. Filter sentences to require >= 3 words (drop UI fragments)
3. Improve syllable counting: add silent-e heuristic, count consecutive vowels as 1 syllable
4. Use `re.split(r'[.!?]+', text)` instead of `re.findall(r'[.!?]+', text)` for sentence count

**Expected**: Score moves from ~30 to ~45-55 for this content (fairly difficult, not impossible)

---

## Task 2: Fix FAQ detection — Elementor accordion + /faq URL crawling

**Files**: `checks/content.py` — `_check_faq()`, `crawler.py`

**Problem**: The /faq/ page exists with 13 Q&A pairs in an Elementor accordion but
the grader reports "No FAQ section found". Two issues: (a) the crawler's 5-page
limit may not include /faq/, and (b) Elementor accordions use specific class names
and structures that the FAQ checker doesn't recognize.

**Fix**:
1. Add `/faq` as first priority in PRIORITY_PATHS (already done for contact, need to
   verify faq is high enough)
2. Detect Elementor accordion FAQ patterns:
   - `class*="accordion"`, `class*="elementor-accordion"`, `class*="faq-item"`
   - `<details>`/`<summary>` elements (native HTML accordion)
   - Any element with class containing "faq" (case-insensitive) — already done but
     may not match Elementor's nested structure
3. Detect Q&A pattern: look for elements where a heading/label is immediately followed
   by a text block (heuristic for accordion items without explicit FAQ classes)
4. Check for "Frequently Asked Questions" or "FAQ" in any heading text on any page

**Expected**: FAQ check passes when /faq/ is crawled

---

## Task 3: Fix city targeting — partial credit for content presence

**File**: `checks/local_seo.py` — `_check_city_targeting()`

**Problem**: Score 0 when city "San Marcos" is in page content but not in title/h1/meta.
The check correctly identifies the city but gives 0 credit for content presence.

**Fix**:
1. If city found in title/h1/meta: score 100, passed=True
2. If city found in body content (but not title/h1/meta): score 50, passed=False
   with recommendation "Add city name to title, h1, or meta description for better local SEO"
3. If city not found anywhere: score 0, passed=False

**Expected**: Score moves from 0 to 50 for this site

---

## Task 4: Fix LocalBusiness vs Organization schema clarity

**File**: `checks/local_seo.py` — `_check_localbusiness_schema()`

**Problem**: The check says "LocalBusiness schema: 1/5 required fields present" but
the site has Organization schema, not LocalBusiness. The check may be conflating the
two. It should clearly distinguish and give appropriate messaging.

**Fix**:
1. Separate the detection: look for LocalBusiness specifically, not Organization
2. If Organization found but no LocalBusiness: score 20, detail "Organization schema
   found but LocalBusiness schema missing. Organization is valid but LocalBusiness
   enables local search features (maps, hours, reviews in search results)."
3. If LocalBusiness found: count required fields as before
4. If neither found: score 0, detail "No LocalBusiness or Organization schema found"

**Expected**: Clearer messaging, score stays ~20 but detail explains why

---

## Task 5: Fix redirect chain detection — don't penalize standard redirects

**File**: `checks/technical.py` — `_check_redirect_chains()`

**Problem**: Score 50 for "2 redirects" but these are http→https and sitemap.xml→
sitemap_index.xml — both standard WordPress/SEO practices that should not be penalized.

**Fix**:
1. Don't count http→https redirects as problematic (universal best practice)
2. Don't count sitemap.xml→sitemap_index.xml as problematic (standard Yoast behavior)
3. Only flag actual redirect CHAINS (A→B→C, 3+ hops) or unexpected redirects on
   content pages
4. Change threshold: 0-2 standard redirects = pass (100), 3+ = investigate (50)

**Expected**: Score moves from 50 to 100

---

## Task 6: Fix broken link detail — show which URL is broken

**File**: `checks/technical.py` — `_check_broken_links()`

**Problem**: "Checked 79 links, found 1 broken" but doesn't tell you which link.
The broken link is http://northwebpro.com (403) — a footer credit link, not a
content link. The detail should list the broken URL(s) so the user can act on them.

**Fix**:
1. Include broken URL(s) in the detail string (up to 5)
2. Distinguish between internal broken links (critical) and external (informational)
3. Don't fail for external 403s that are likely rate-limiting or bot-blocking
   (403 from external sites doesn't mean the link is truly broken — could be
   blocking our user agent)
4. Only count 404 and 500+ as truly broken for external links
5. For internal links, any non-200 is broken

**Expected**: Detail shows the actual broken URL, external 403s not counted as broken

---

## Sprint Execution Order
1. Task 5 (redirects) — simplest, ~20 lines
2. Task 6 (broken links) — ~30 lines
3. Task 3 (city targeting) — ~15 lines
4. Task 4 (LocalBusiness schema) — ~25 lines
5. Task 1 (readability) — ~50 lines
6. Task 2 (FAQ detection) — ~40 lines

## Verification
- Run full test suite (33 tests must pass)
- Regenerate report for billbarberconstruction.com
- Compare before/after scores
- Send report to Telegram