from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set, Any
from urllib.parse import urlparse, urljoin, urlunparse, parse_qsl, urlencode
import time
import re
import gzip
import hashlib
import json
from curl_cffi import requests as req
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

PRIORITY_PATHS = [
    re.compile(r'/about'),
    re.compile(r'/contact'),
    re.compile(r'/services'),
    re.compile(r'/service'),
    re.compile(r'/team'),
    re.compile(r'/faq'),
    re.compile(r'/blog'),
    re.compile(r'/portfolio'),
]

def normalize_url(url: str) -> str:
    if not url:
        return url
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    
    # Strip default ports (80 for http, 443 for https)
    if ":" in netloc:
        host, port = netloc.rsplit(":", 1)
        if (scheme == "http" and port == "80") or (scheme == "https" and port == "443"):
            netloc = host
            
    # Remove duplicate trailing slashes (except root)
    path = parsed.path
    if path:
        while path.endswith("//"):
            path = path[:-1]
            
    # Clean tracking parameters like utm_* or gclid while preserving functional ones
    query_params = []
    if parsed.query:
        for k, v in parse_qsl(parsed.query, keep_blank_values=True):
            if k.lower().startswith('utm_') or k.lower() == 'gclid':
                continue
            query_params.append((k, v))
    query = urlencode(query_params) if query_params else ''
    
    # Fragment is removed
    return urlunparse((scheme, netloc, path, parsed.params, query, ''))

class RobotsParser:
    # ponytail: custom robots parser translates glob wildcards to regexes. If regex compiles incorrectly, falls back to basic prefix match.
    def __init__(self, content: str):
        self.content = content
        self.rules = {}  # agent -> list of (allow/disallow, path_regex)
        self._parse()

    def _parse(self):
        current_agents = []
        last_was_agent = False
        for line in self.content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '#' in line:
                line = line.split('#', 1)[0].strip()
            if ':' not in line:
                continue
            key, val = line.split(':', 1)
            key = key.strip().lower()
            val = val.strip()
            
            if key == 'user-agent':
                if not last_was_agent:
                    current_agents = []
                current_agents.append(val.lower())
                last_was_agent = True
            elif key in ('allow', 'disallow'):
                last_was_agent = False
                if not current_agents:
                    continue
                is_allow = (key == 'allow')
                
                path = val
                if key == 'disallow' and not path:
                    is_allow = True
                    path = '/'
                
                regex_str = re.escape(path).replace(r'\*', '.*')
                if regex_str.endswith(r'\$'):
                    regex_str = regex_str[:-2] + '$'
                regex_str = '^' + regex_str
                
                try:
                    pattern = re.compile(regex_str)
                except Exception:
                    pattern = re.compile('^' + re.escape(path))
                
                for agent in current_agents:
                    if agent not in self.rules:
                        self.rules[agent] = []
                    self.rules[agent].append((is_allow, pattern))

    def can_fetch(self, user_agent: str, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path or '/'
        user_agent = user_agent.lower()
        
        agents_to_check = [user_agent, '*']
        applicable_rules = None
        for agent in agents_to_check:
            if agent in self.rules:
                applicable_rules = self.rules[agent]
                break
        
        if not applicable_rules:
            return True
            
        matching_rules = []
        for is_allow, pattern in applicable_rules:
            if pattern.search(path):
                matching_rules.append((is_allow, pattern.pattern))
        
        if not matching_rules:
            return True
            
        matching_rules.sort(key=lambda x: len(x[1]), reverse=True)
        return matching_rules[0][0]

@dataclass
class PageData:
    url: str
    html: str
    final_url: str
    status_code: int
    ttfb_ms: float
    headers: Dict[str, str]
    soup: Optional[BeautifulSoup] = None
    error: Optional[str] = None
    redirect_hops: List[Dict] = field(default_factory=list)
    redirect_type: Optional[str] = None
    raw_content: bytes = b""
    content_hash: str = ""
    # Rendering results
    rendered_html: Optional[str] = None
    console_logs: List[str] = field(default_factory=list)
    screenshot_bytes: Optional[bytes] = None
    render_error: Optional[str] = None
    raw_vs_rendered_disparities: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.soup = BeautifulSoup(self.html, 'html.parser')

@dataclass
class CrawlResult:
    base_url: str
    base_domain: str = field(init=False)
    pages: Dict[str, PageData] = field(default_factory=dict)
    robots_txt: str = ""
    sitemap_xml: str = ""
    sitemap_urls: List[str] = field(default_factory=list)
    error: Optional[str] = None
    discovered_urls: Set[str] = field(default_factory=set)
    crawled_urls: Set[str] = field(default_factory=set)
    excluded_urls: Set[str] = field(default_factory=set)
    fetch_failures: Dict[str, str] = field(default_factory=dict)
    robots_parser: Optional[RobotsParser] = None

    def __post_init__(self):
        self.base_domain = urlparse(self.base_url).netloc

    @property
    def homepage(self):
        return self.pages.get(self.base_url)

    def all_links(self) -> Set[str]:
        links = set()
        for page in self.pages.values():
            if page.soup:
                for a in page.soup.find_all('a', href=True):
                    href = a['href']
                    full_url = urljoin(page.url, href)
                    full_url = normalize_url(full_url)
                    parsed = urlparse(full_url)
                    if parsed.netloc == self.base_domain:
                        links.add(full_url)
        return links

def _fetch_page(url: str, timeout: int = 15, session=None, max_redirects: int = 10, headers=None) -> PageData:
    current_url = url
    hops = []
    visited = set()
    start_time = time.monotonic()
    
    for _ in range(max_redirects + 1):
        current_url = normalize_url(current_url)
        if current_url in visited:
            hops.append({
                "url": current_url,
                "status_code": 310,
                "protocol": urlparse(current_url).scheme,
            })
            break
        visited.add(current_url)
        
        try:
            start_hop = time.monotonic()
            if session:
                resp = session.get(current_url, timeout=timeout, allow_redirects=False, headers=headers)
            else:
                resp = req.get(current_url, timeout=timeout, impersonate="chrome", allow_redirects=False, headers=headers)
            
            status = resp.status_code
            hops.append({
                "url": current_url,
                "status_code": status,
                "protocol": urlparse(current_url).scheme,
            })
            
            if 300 <= status < 400 and 'Location' in resp.headers:
                next_url = resp.headers['Location']
                next_url = urljoin(current_url, next_url)
                current_url = next_url
            else:
                ttfb_ms = (time.monotonic() - start_time) * 1000
                redirect_type = None
                if len(hops) > 1:
                    if len(hops) == 2:
                        redirect_type = "redirect"
                    else:
                        redirect_type = "redirect_chain"
                if hops and hops[-1].get("status_code") == 310:
                    redirect_type = "loop"
                
                raw_bytes = getattr(resp, "content", None)
                if not isinstance(raw_bytes, (bytes, bytearray)):
                    raw_text = getattr(resp, "text", "")
                    if not isinstance(raw_text, str):
                        raw_text = ""
                    raw_bytes = raw_text.encode("utf-8")
                content_hash = hashlib.sha256(raw_bytes).hexdigest()
                
                resp_text = getattr(resp, "text", "")
                if not isinstance(resp_text, str):
                    resp_text = ""

                return PageData(
                    url=url,
                    html=resp_text,
                    final_url=current_url,
                    status_code=status,
                    ttfb_ms=ttfb_ms,
                    headers=dict(getattr(resp, "headers", {}) or {}),
                    redirect_hops=hops,
                    redirect_type=redirect_type,
                    raw_content=raw_bytes,
                    content_hash=content_hash,
                )
        except Exception as e:
            ttfb_ms = (time.monotonic() - start_time) * 1000
            redirect_type = "loop" if "loop" in str(e).lower() or len(hops) > max_redirects else None
            return PageData(
                url=url,
                html="",
                final_url=current_url,
                status_code=0,
                ttfb_ms=ttfb_ms,
                headers={},
                error=str(e),
                redirect_hops=hops,
                redirect_type=redirect_type,
            )
            
    redirect_type = "loop" if len(visited) < max_redirects else "redirect_chain"
    return PageData(
        url=url,
        html="",
        final_url=current_url,
        status_code=0,
        ttfb_ms=(time.monotonic() - start_time) * 1000,
        headers={},
        error="Max redirects exceeded",
        redirect_hops=hops,
        redirect_type=redirect_type,
    )

def _extract_internal_links(soup: BeautifulSoup, base_url: str, base_domain: str) -> List[str]:
    links = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        full_url = urljoin(base_url, href)
        full_url = normalize_url(full_url)
        parsed = urlparse(full_url)
        if parsed.netloc == base_domain:
            links.add(full_url)
    return list(links)

def _parse_sitemap_xml(content_bytes: bytes, url: str, timeout: int, session, result: CrawlResult, crawled_sitemaps: Set[str]):
    if content_bytes.startswith(b'\x1f\x8b'):
        try:
            content_bytes = gzip.decompress(content_bytes)
        except Exception as e:
            result.fetch_failures[url] = f"Gzip decompress error: {e}"
            return
            
    try:
        try:
            xml_text = content_bytes.decode('utf-8', errors='replace')
        except Exception:
            xml_text = content_bytes.decode('latin-1', errors='replace')
            
        root = ET.fromstring(xml_text)
    except Exception:
        # regex fallback for loc tags
        locs = re.findall(r'<loc>(.*?)</loc>', xml_text, re.DOTALL | re.IGNORECASE)
        is_index = '<sitemapindex' in xml_text.lower()
        for loc in locs:
            loc = loc.strip()
            if not loc:
                continue
            if is_index:
                _fetch_and_parse_sitemap(loc, timeout, session, result, crawled_sitemaps)
            else:
                result.sitemap_urls.append(normalize_url(loc))
        return

    def clean_tag(tag):
        if '}' in tag:
            return tag.split('}', 1)[1]
        return tag

    root_tag = clean_tag(root.tag).lower()
    is_index = (root_tag == 'sitemapindex')
    
    for elem in root.iter():
        elem_tag = clean_tag(elem.tag).lower()
        if is_index and elem_tag == 'sitemap':
            for child in elem:
                if clean_tag(child.tag).lower() == 'loc' and child.text:
                    _fetch_and_parse_sitemap(child.text.strip(), timeout, session, result, crawled_sitemaps)
        elif not is_index and elem_tag == 'url':
            for child in elem:
                if clean_tag(child.tag).lower() == 'loc' and child.text:
                    result.sitemap_urls.append(normalize_url(child.text.strip()))

def _fetch_and_parse_sitemap(url: str, timeout: int, session, result: CrawlResult, crawled_sitemaps: Set[str]):
    url = normalize_url(url)
    if url in crawled_sitemaps:
        return
    crawled_sitemaps.add(url)
    
    try:
        if session:
            resp = session.get(url, timeout=timeout)
        else:
            resp = req.get(url, timeout=timeout, impersonate="chrome")
        
        if resp.status_code != 200:
            result.fetch_failures[url] = f"HTTP {resp.status_code}"
            return
            
        content = getattr(resp, "content", None)
        if not isinstance(content, (bytes, bytearray)):
            raw_text = getattr(resp, "text", "")
            if not isinstance(raw_text, str):
                raw_text = ""
            content = raw_text.encode("utf-8")
        if not result.sitemap_xml:
            try:
                result.sitemap_xml = content.decode('utf-8', errors='replace')
            except Exception:
                result.sitemap_xml = content.decode('latin-1', errors='replace')
                
        _parse_sitemap_xml(content, url, timeout, session, result, crawled_sitemaps)
    except Exception as e:
        result.fetch_failures[url] = str(e)

def render_page_with_playwright(url: str, timeout_ms: int = 10000) -> dict:
    # ponytail: playwright rendering is optional; falls back gracefully to static fetch if not installed or fails
    result = {
        "html": "",
        "console_logs": [],
        "screenshot": None,
        "error": None
    }
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        result["error"] = "Playwright is not installed"
        return result

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            context = browser.new_context()
            page = context.new_page()
            
            page.on("console", lambda msg: result["console_logs"].append(f"[{msg.type}] {msg.text}"))
            
            page.goto(url, timeout=timeout_ms)
            try:
                page.wait_for_load_state("networkidle", timeout=timeout_ms)
            except Exception:
                pass
                
            result["html"] = page.content()
            try:
                result["screenshot"] = page.screenshot(type="png")
            except Exception:
                pass
            browser.close()
    except Exception as e:
        result["error"] = str(e)
    return result

def compare_raw_vs_rendered(page: PageData) -> dict:
    disparities = {}
    if not page.rendered_html:
        return disparities

    raw_soup = page.soup or BeautifulSoup(page.html, 'html.parser')
    rendered_soup = BeautifulSoup(page.rendered_html, 'html.parser')

    # 1. Compare Page Titles
    raw_title_tag = raw_soup.find("title")
    raw_title = raw_title_tag.get_text(strip=True) if raw_title_tag else ""
    rendered_title_tag = rendered_soup.find("title")
    rendered_title = rendered_title_tag.get_text(strip=True) if rendered_title_tag else ""
    if raw_title != rendered_title:
        disparities["title"] = {"raw": raw_title, "rendered": rendered_title}

    # 2. Compare Canonical Tags
    raw_canonical = raw_soup.find("link", rel="canonical")
    raw_canonical_url = raw_canonical.get("href", "") if raw_canonical else ""
    rendered_canonical = rendered_soup.find("link", rel="canonical")
    rendered_canonical_url = rendered_canonical.get("href", "") if rendered_canonical else ""
    if raw_canonical_url != rendered_canonical_url:
        disparities["canonical"] = {"raw": raw_canonical_url, "rendered": rendered_canonical_url}

    # 3. Compare Robots Meta Tags
    raw_robots = raw_soup.find("meta", attrs={"name": "robots"})
    raw_robots_content = raw_robots.get("content", "") if raw_robots else ""
    rendered_robots = rendered_soup.find("meta", attrs={"name": "robots"})
    rendered_robots_content = rendered_robots.get("content", "") if rendered_robots else ""
    if raw_robots_content.lower() != rendered_robots_content.lower():
        disparities["robots"] = {"raw": raw_robots_content, "rendered": rendered_robots_content}

    # 4. Compare Heading Outlines
    raw_headings = [h.name for h in raw_soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])]
    rendered_headings = [h.name for h in rendered_soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])]
    if raw_headings != rendered_headings:
        disparities["headings"] = {"raw": raw_headings, "rendered": rendered_headings}

    # 5. Compare Word Counts
    def get_word_count(soup):
        texts = soup.find_all(string=True)
        visible_texts = [t for t in texts if t.parent.name not in ('style', 'script', 'head', 'title', 'meta', '[document]')]
        return len(" ".join(visible_texts).split())

    raw_word_count = get_word_count(raw_soup)
    rendered_word_count = get_word_count(rendered_soup)
    if raw_word_count != rendered_word_count:
        disparities["word_count"] = {"raw": raw_word_count, "rendered": rendered_word_count}

    # 6. Compare Structured Schemas (JSON-LD)
    def get_schemas(soup):
        schemas = soup.find_all("script", type="application/ld+json")
        types = []
        for s in schemas:
            try:
                data = json.loads(s.string or s.get_text() or "{}")
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            t = item.get("@type", "")
                            if t: types.append(t)
                elif isinstance(data, dict):
                    t = data.get("@type", "")
                    if t: types.append(t)
            except Exception:
                pass
        return sorted(types)

    raw_schemas = get_schemas(raw_soup)
    rendered_schemas = get_schemas(rendered_soup)
    if raw_schemas != rendered_schemas:
        disparities["structured_data"] = {"raw": raw_schemas, "rendered": rendered_schemas}

    return disparities

def crawl_site(url: str, max_pages: int = 5, timeout: int = 15, enable_playwright: bool = False, max_depth: int = 5, max_time: float = 30.0) -> CrawlResult:
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    url = normalize_url(url)
    
    result = CrawlResult(base_url=url)
    session = req.Session(impersonate="chrome")
    start_time = time.monotonic()

    homepage = _fetch_page(url, timeout, session)
    if homepage.error:
        result.error = homepage.error
        result.fetch_failures[url] = homepage.error
        return result
    if homepage.status_code >= 400:
        result.fetch_failures[url] = f"HTTP {homepage.status_code}"
    
    if enable_playwright:
        render_res = render_page_with_playwright(url, timeout_ms=timeout * 1000)
        homepage.rendered_html = render_res["html"]
        homepage.console_logs = render_res["console_logs"]
        homepage.screenshot_bytes = render_res["screenshot"]
        homepage.render_error = render_res["error"]
        if homepage.rendered_html:
            homepage.raw_vs_rendered_disparities = compare_raw_vs_rendered(homepage)

    result.pages[url] = homepage
    result.crawled_urls.add(url)

    robots_url = urljoin(url, '/robots.txt')
    robots = _fetch_page(robots_url, timeout, session)
    result.robots_txt = robots.html
    if result.robots_txt:
        result.robots_parser = RobotsParser(result.robots_txt)

    # Read Sitemap: directive from robots.txt, fall back to /sitemap.xml
    sitemap_urls_to_try = []
    if result.robots_txt:
        for line in result.robots_txt.splitlines():
            if line.lower().startswith('sitemap:'):
                sm_url = line.split(':', 1)[1].strip()
                if sm_url:
                    sitemap_urls_to_try.append(sm_url)
    default_sitemap = urljoin(url, '/sitemap.xml')
    if default_sitemap not in sitemap_urls_to_try:
        sitemap_urls_to_try.append(default_sitemap)

    crawled_sitemaps = set()
    for sm_url in sitemap_urls_to_try:
        _fetch_and_parse_sitemap(sm_url, timeout, session, result, crawled_sitemaps)
        if result.sitemap_urls:
            break

    def record_discovered_links(page):
        if page.soup:
            for a in page.soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(page.url, href)
                full_url = normalize_url(full_url)
                result.discovered_urls.add(full_url)

    record_discovered_links(homepage)

    internal_links = _extract_internal_links(homepage.soup, url, result.base_domain)
    filtered_links = []
    for link in internal_links:
        if result.robots_parser and not result.robots_parser.can_fetch("WebsiteGrader", link):
            result.excluded_urls.add(link)
            continue
        filtered_links.append(link)

    priority_links = [link for link in filtered_links if any(p.search(link) for p in PRIORITY_PATHS)]
    remaining_links = [link for link in filtered_links if link not in priority_links]

    to_crawl = [(link, 1) for link in (priority_links + remaining_links)]
    crawled = {url}

    while len(result.pages) < max_pages and to_crawl:
        if time.monotonic() - start_time > max_time:
            break
            
        next_url, depth = to_crawl.pop(0)
        if depth > max_depth:
            continue
        if next_url in crawled:
            continue
        crawled.add(next_url)
        
        page = _fetch_page(next_url, timeout, session)
        if time.monotonic() - start_time > max_time:
            break
            
        if page.error or page.status_code >= 400:
            result.fetch_failures[next_url] = page.error or f"HTTP {page.status_code}"
            continue

        if enable_playwright:
            render_res = render_page_with_playwright(next_url, timeout_ms=timeout * 1000)
            page.rendered_html = render_res["html"]
            page.console_logs = render_res["console_logs"]
            page.screenshot_bytes = render_res["screenshot"]
            page.render_error = render_res["error"]
            if page.rendered_html:
                page.raw_vs_rendered_disparities = compare_raw_vs_rendered(page)

        result.pages[next_url] = page
        result.crawled_urls.add(next_url)
        record_discovered_links(page)
        
        if page.soup and depth < max_depth:
            new_links = _extract_internal_links(page.soup, next_url, result.base_domain)
            for link in new_links:
                if link not in crawled and not any(item[0] == link for item in to_crawl):
                    if result.robots_parser and not result.robots_parser.can_fetch("WebsiteGrader", link):
                        result.excluded_urls.add(link)
                        continue
                    to_crawl.append((link, depth + 1))

    for link in result.discovered_urls:
        parsed = urlparse(link)
        if parsed.netloc == result.base_domain and link not in result.crawled_urls and link not in result.fetch_failures:
            result.excluded_urls.add(link)

    return result
