import re
import json
from collections import Counter
from .base import CheckResult, Severity, CheckCategory

class ContentChecks(CheckCategory):
    category_name = "Content Quality"
    category_weight = 15

    def run(self, crawl_result):
        homepage = crawl_result.homepage
        if not homepage or not homepage.soup:
            return []
        all_pages = [p for p in crawl_result.pages.values() if p.soup]

        results = []
        results.append(self._check_word_count(homepage))
        results.append(self._check_keyword_density(homepage))
        results.append(self._check_readability(homepage))
        results.append(self._check_faq(all_pages, crawl_result))
        results.append(self._check_eeat(all_pages))
        results.append(self._check_content_uniqueness(crawl_result))
        results.append(self._check_title_alignment(homepage))

        # Inject raw-vs-rendered disparities for word count
        disparities = getattr(homepage, "raw_vs_rendered_disparities", {})
        if disparities and "word_count" in disparities:
            for r in results:
                if r.check_id == "content_word_count":
                    r.data["raw_vs_rendered_disparity"] = disparities["word_count"]

        return results

    def _check_word_count(self, page):
        text = page.soup.get_text(strip=True)
        words = text.split()
        word_count = len(words)

        if word_count < 200:
            score = 0
            passed = False
            detail = f"{word_count} words found"
            recommendation = "Add more high-quality content to provide value to users and improve search rankings."
        elif word_count < 800:
            score = 70
            passed = True
            detail = f"{word_count} words found"
            recommendation = "Consider expanding your content to provide more comprehensive information."
        else:
            score = 100
            passed = True
            detail = f"{word_count} words found"
            recommendation = "Good content length. Maintain high-quality, relevant information."

        return CheckResult(
            check_id="content_word_count",
            check_name="Content Word Count",
            category=self.category_name,
            severity=Severity.HIGH,
            passed=passed,
            score=score,
            detail=detail,
            recommendation=recommendation,
            fix_difficulty="Medium",
            impact_estimate="High"
        )

    def _check_keyword_density(self, page):
        text = page.soup.get_text(strip=True)
        words = re.findall(r'\b\w+\b', text.lower())
        stopwords = {
            'the','a','an','is','are','was','were','be','been','being','have','has','had','do','does','did',
            'will','would','could','should','may','might','must','can','to','of','in','for','on','at','by',
            'with','from','as','it','its','this','that','these','those','i','you','he','she','we','they','me',
            'him','her','us','them','my','your','his','our','their','and','or','but','not','no','if','then',
            'when','where','why','how','all','any','both','each','few','more','most','other','some','such',
            'only','own','same','so','than','too','very'
        }
        filtered_words = [w for w in words if w not in stopwords and len(w) > 2]
        total_words = len(filtered_words)

        if total_words == 0:
            return CheckResult(
                check_id="content_keyword_density",
                check_name="Keyword Density",
                category=self.category_name,
                severity=Severity.MEDIUM,
                passed=False, score=0,
                detail="No content words found",
                recommendation="Add meaningful content to your page.",
            )

        word_counts = Counter(filtered_words)
        top_words = word_counts.most_common(10)
        keyword_stuffing = any(count/total_words > 0.05 for word, count in top_words)

        if keyword_stuffing:
            score = 30
            passed = False
            detail = f"Keyword stuffing detected. Top words: {', '.join([f'{w} ({c})' for w, c in top_words[:5]])}"
            recommendation = "Reduce keyword repetition and focus on natural, valuable content."
        else:
            score = 100
            passed = True
            detail = f"Good keyword distribution. Top words: {', '.join([f'{w} ({c})' for w, c in top_words[:5]])}"
            recommendation = "Maintain natural keyword usage and content quality."

        return CheckResult(
            check_id="content_keyword_density",
            check_name="Keyword Density",
            category=self.category_name,
            severity=Severity.MEDIUM,
            passed=passed, score=score,
            detail=detail, recommendation=recommendation,
            data={"top_words": top_words, "total_words": total_words}
        )

    def _check_readability(self, page):
        text = page.soup.get_text(strip=True)
        sentences = re.findall(r'[.!?]+', text)
        words = re.findall(r'\b\w+\b', text)
        num_sentences = len(sentences)
        num_words = len(words)

        if num_sentences == 0 or num_words == 0:
            return CheckResult(
                check_id="content_readability",
                check_name="Content Readability",
                category=self.category_name, severity=Severity.MEDIUM,
                passed=False, score=0,
                detail="No readable content found",
                recommendation="Add well-structured, readable content to your page.",
            )

        syllables = 0
        for word in words:
            syllables += len(re.findall(r'[aeiouAEIOU]+', word))

        score = 206.835 - 1.015 * (num_words / num_sentences) - 84.6 * (syllables / num_words)

        if score >= 60:
            interpretation = "Easy to read"
            passed = True
            score_value = 100
            recommendation = "Excellent readability. Maintain clear and simple language."
        elif score >= 30:
            interpretation = "Fairly difficult"
            passed = True
            score_value = 70
            recommendation = "Content is readable but could be simplified for better user experience."
        else:
            interpretation = "Difficult to read"
            passed = False
            score_value = 30
            recommendation = "Improve readability by using shorter sentences and simpler words."

        return CheckResult(
            check_id="content_readability",
            check_name="Content Readability",
            category=self.category_name, severity=Severity.MEDIUM,
            passed=passed, score=score_value,
            detail=f"Flesch score: {score:.1f} ({interpretation})",
            recommendation=recommendation,
        )

    def _check_faq(self, pages, crawl_result):
        """Check ALL crawled pages for FAQ sections, and check for /faq page in URL paths."""
        faq_found = False
        faq_location = ""

        # Check if any crawled URL contains /faq
        for url in crawl_result.pages.keys():
            if '/faq' in url.lower():
                faq_found = True
                faq_location = url
                break

        # Check all pages for FAQ class/section
        if not faq_found:
            for page in pages:
                # Check for FAQ class
                if page.soup.find(class_=re.compile('faq', re.I)):
                    faq_found = True
                    faq_location = page.url
                    break
                # Check for FAQ heading
                for tag in page.soup.find_all(['h1', 'h2', 'h3']):
                    if tag.get_text(strip=True).lower() in ('faq', 'frequently asked questions', 'f.a.q.'):
                        faq_found = True
                        faq_location = page.url
                        break
                if faq_found:
                    break

        # Check all pages for FAQPage schema
        if not faq_found:
            for page in pages:
                for script in page.soup.find_all('script', type='application/ld+json'):
                    try:
                        data = json.loads(script.string or script.get_text() or "{}")
                        items = []
                        if isinstance(data, dict):
                            if '@graph' in data:
                                items = data['@graph'] if isinstance(data['@graph'], list) else [data['@graph']]
                            else:
                                items = [data]
                        elif isinstance(data, list):
                            items = data
                        for item in items:
                            if isinstance(item, dict) and item.get('@type') == 'FAQPage':
                                faq_found = True
                                faq_location = page.url
                                break
                    except (json.JSONDecodeError, TypeError):
                        continue
                if faq_found:
                    break

        if faq_found:
            short_url = faq_location.replace("https://", "").replace("http://", "")[:50]
            return CheckResult(
                check_id="content_faq", check_name="FAQ Section",
                category=self.category_name, severity=Severity.MEDIUM,
                passed=True, score=100,
                detail=f"FAQ section found on {short_url}",
                recommendation="Good practice. Keep FAQ section updated with relevant questions.",
            )
        return CheckResult(
            check_id="content_faq", check_name="FAQ Section",
            category=self.category_name, severity=Severity.MEDIUM,
            passed=False, score=0,
            detail="No FAQ section found on any crawled page",
            recommendation="Consider adding an FAQ section to address common user questions and improve SEO.",
            fix_code='''<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [{
    "@type": "Question",
    "name": "Example Question 1",
    "acceptedAnswer": {
      "@type": "Answer",
      "text": "Example answer text here."
    }
  }]
}
</script>''',
        )

    def _check_eeat(self, pages):
        """Scan ALL crawled pages for E-E-A-T signals with expanded detection."""
        signals = []
        for page in pages:
            text = page.soup.get_text().lower()
            # Author bio
            if page.soup.find(class_=re.compile(r'author')) or page.soup.find(id=re.compile(r'author')):
                if "author bio" not in signals:
                    signals.append("author bio")
            # About page link
            if page.soup.find('a', string=re.compile(r'about', re.I)):
                if "about page link" not in signals:
                    signals.append("about page link")
            # License number
            if re.search(r'licen[sc]e.*?#?\d+', text):
                if "license number" not in signals:
                    signals.append("license number")
            # Licensed / bonded / insured
            if re.search(r'licen[sc]ed|bonded|insured', text):
                if "licensed/bonded/insured" not in signals:
                    signals.append("licensed/bonded/insured")
            # Certified / accredited
            if re.search(r'certified|accredited', text):
                if "certifications" not in signals:
                    signals.append("certifications")
            # BBB
            if re.search(r'\bbb\b|better business bureau', text):
                if "BBB accreditation" not in signals:
                    signals.append("BBB accreditation")
            # BuildZoom
            if re.search(r'buildzoom', text):
                if "BuildZoom score" not in signals:
                    signals.append("BuildZoom score")
            # Years in business / generations
            if re.search(r'since\s+19\d{2}|since\s+20\d{2}|\d+\s+years', text):
                if "years in business" not in signals:
                    signals.append("years in business")
            if re.search(r'\d+\s+generations', text):
                if "generations of experience" not in signals:
                    signals.append("generations of experience")
            # Reviews / testimonials
            if re.search(r'\d+\+?\s*(?:reviews?|testimonials?)|five.?star|★★★★★|5.?star', text):
                if "reviews/testimonials" not in signals:
                    signals.append("reviews/testimonials")
            # Awards
            if re.search(r'award|winner|recognized', text):
                if "awards" not in signals:
                    signals.append("awards")
            # Portfolio / gallery
            if re.search(r'portfolio|gallery|our\s+work', text):
                if "portfolio/gallery" not in signals:
                    signals.append("portfolio/gallery")
            # Warranty / guarantee
            if re.search(r'warranty|guarantee', text):
                if "warranty/guarantee" not in signals:
                    signals.append("warranty/guarantee")

        passed = len(signals) >= 2
        score = min(100, len(signals) * 20) if signals else 0
        detail = f"Found {len(signals)} E-E-A-T signals: {', '.join(signals)}" if signals else "No E-E-A-T signals found"
        return CheckResult(
            check_id="content_eeat", check_name="E-E-A-T Signals",
            category=self.category_name, severity=Severity.MEDIUM,
            passed=passed, score=score,
            detail=detail,
            recommendation="Add author bios, certifications, and business history to build trust." if not passed else "",
            data={"signals": signals}
        )

    def _check_content_uniqueness(self, crawl_result):
        import hashlib
        hashes = {}
        similarities = []
        pages = list(crawl_result.pages.values())
        for page in pages:
            text = page.soup.get_text(strip=True) if page.soup else ""
            hashes[page.url] = hashlib.md5(text.encode()).hexdigest()[:8]
        for i in range(len(pages)):
            for j in range(i+1, len(pages)):
                t1 = set((pages[i].soup.get_text(strip=True) or "").lower().split())
                t2 = set((pages[j].soup.get_text(strip=True) or "").lower().split())
                if t1 and t2:
                    sim = int(len(t1 & t2) / len(t1 | t2) * 100)
                    if sim > 80:
                        similarities.append((pages[i].url, pages[j].url, sim))
        passed = not similarities
        detail = f"Content unique across {len(pages)} pages" if passed else f"Found {len(similarities)} similar page pairs"
        return CheckResult(
            check_id="content_uniqueness", check_name="Content Uniqueness",
            category=self.category_name, severity=Severity.MEDIUM,
            passed=passed, score=100 if passed else 0,
            detail=detail,
            recommendation="Ensure each page has unique, valuable content.",
            data={"hashes": hashes, "similarities": similarities}
        )

    def _check_title_alignment(self, page):
        soup = page.soup
        title = soup.title.string if soup.title else ""
        h1 = soup.h1.get_text() if soup.h1 else ""
        body_text = soup.get_text().lower()
        stopwords = {'a','an','the','and','or','but','in','on','at','to','for','of','with','by','is','are','was','were','it','that','this','as','be','been','being'}
        title_words = [w.lower() for w in re.findall(r'\w+', title + " " + h1) if w.lower() not in stopwords and len(w) > 2]
        if not title_words:
            return CheckResult(
                check_id="content_title_alignment", check_name="Title Alignment",
                category=self.category_name, severity=Severity.LOW,
                passed=False, score=0,
                detail="No keywords found in title/h1",
                recommendation="Add descriptive keywords to title and h1 tags."
            )
        found = sum(1 for w in title_words if w in body_text)
        pct = int(found / len(title_words) * 100)
        passed = pct >= 50
        detail = f"{found} of {len(title_words)} title keywords found in body content ({pct}%)"
        return CheckResult(
            check_id="content_title_alignment", check_name="Title Alignment",
            category=self.category_name, severity=Severity.LOW,
            passed=passed, score=pct,
            detail=detail,
            recommendation="Ensure title and h1 keywords appear in the body content."
        )