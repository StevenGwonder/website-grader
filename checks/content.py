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

        results = []
        results.append(self._check_word_count(homepage))
        results.append(self._check_keyword_density(homepage))
        results.append(self._check_readability(homepage))
        results.append(self._check_faq(homepage))
        results.append(self._check_eeat(homepage))
        results.append(self._check_content_uniqueness(crawl_result))
        results.append(self._check_title_alignment(homepage))
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
                passed=False,
                score=0,
                detail="No content words found",
                recommendation="Add meaningful content to your page.",
                fix_difficulty="Medium",
                impact_estimate="Medium"
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
            passed=passed,
            score=score,
            detail=detail,
            recommendation=recommendation,
            fix_difficulty="Medium",
            impact_estimate="Medium",
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
                category=self.category_name,
                severity=Severity.MEDIUM,
                passed=False,
                score=0,
                detail="No readable content found",
                recommendation="Add well-structured, readable content to your page.",
                fix_difficulty="Medium",
                impact_estimate="Medium"
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
            category=self.category_name,
            severity=Severity.MEDIUM,
            passed=passed,
            score=score_value,
            detail=f"Flesch score: {score:.1f} ({interpretation})",
            recommendation=recommendation,
            fix_difficulty="Medium",
            impact_estimate="Medium"
        )

    def _check_faq(self, page):
        soup = page.soup
        faq_found = False

        # Check for FAQ class
        if soup.find(class_=re.compile('faq', re.I)):
            faq_found = True

        # Check for FAQPage schema
        if not faq_found:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('@type') == 'FAQPage':
                        faq_found = True
                        break
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get('@type') == 'FAQPage':
                                faq_found = True
                                break
                except Exception:
                    continue

        if faq_found:
            passed = True
            score = 100
            detail = "FAQ section found"
            recommendation = "Good practice. Keep FAQ section updated with relevant questions."
        else:
            passed = False
            score = 0
            detail = "No FAQ section found"
            recommendation = "Consider adding an FAQ section to address common user questions and improve SEO."
            fix_code = '''<script type="application/ld+json">
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
  },{
    "@type": "Question",
    "name": "Example Question 2",
    "acceptedAnswer": {
      "@type": "Answer",
      "text": "Example answer text here."
    }
  }]
}
</script>'''

        return CheckResult(
            check_id="content_faq",
            check_name="FAQ Section",
            category=self.category_name,
            severity=Severity.MEDIUM,
            passed=passed,
            score=score,
            detail=detail,
            recommendation=recommendation,
            fix_code=fix_code if not faq_found else None,
            fix_difficulty="Easy",
            impact_estimate="Medium"
        )

    def _check_eeat(self, page):
        signals = []
        soup = page.soup
        text = soup.get_text().lower()
        if soup.find(class_=re.compile(r'author')) or soup.find(id=re.compile(r'author')):
            signals.append("author bio")
        if soup.find('a', string=re.compile(r'about', re.I)):
            signals.append("about page link")
        if re.search(r'licen[sc]e.*?#?\d+', text):
            signals.append("license number")
        if re.search(r'certified|accredited|bonded|insured', text):
            signals.append("certifications")
        if re.search(r'since\s+19\d{2}|since\s+20\d{2}|\d+\s+years', text):
            signals.append("years in business")
        passed = len(signals) >= 2
        detail = f"Found {len(signals)} E-E-A-T signals: {', '.join(signals)}" if signals else "No E-E-A-T signals found"
        return CheckResult(
            check_id="content_eeat", check_name="E-E-A-T Signals",
            category=self.category_name, severity=Severity.MEDIUM,
            passed=passed, score=100 if passed else 0,
            detail=detail,
            recommendation="Add author bios, certifications, and business history to build trust.",
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
