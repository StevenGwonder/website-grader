from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set
from urllib.parse import urlparse, urljoin
import time
import re
import requests as req
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
                    parsed = urlparse(full_url)
                    if parsed.netloc == self.base_domain:
                        links.add(full_url)
        return links

def _fetch_page(url: str, timeout: int = 10) -> PageData:
    start = time.monotonic()
    try:
        resp = req.get(url, timeout=timeout, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'})
        ttfb_ms = (time.monotonic() - start) * 1000
        return PageData(
            url=url,
            html=resp.text,
            final_url=resp.url,
            status_code=resp.status_code,
            ttfb_ms=ttfb_ms,
            headers=dict(resp.headers),
        )
    except Exception as e:
        return PageData(url=url, html="", final_url=url, status_code=0, ttfb_ms=0, headers={}, error=str(e))

def _extract_internal_links(soup: BeautifulSoup, base_url: str, base_domain: str) -> List[str]:
    links = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        if parsed.netloc == base_domain:
            links.add(full_url)
    return list(links)

def crawl_site(url: str, max_pages: int = 5, timeout: int = 10) -> CrawlResult:
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    result = CrawlResult(base_url=url)

    homepage = _fetch_page(url, timeout)
    if homepage.error:
        result.error = homepage.error
        return result
    result.pages[url] = homepage

    robots_url = urljoin(url, '/robots.txt')
    robots = _fetch_page(robots_url, timeout)
    result.robots_txt = robots.html

    sitemap_url = urljoin(url, '/sitemap.xml')
    sitemap = _fetch_page(sitemap_url, timeout)
    result.sitemap_xml = sitemap.html
    if sitemap.soup:
        try:
            ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            urls = sitemap.soup.find_all('sm:url', namespaces=ns)
            for u in urls:
                loc = u.find('sm:loc', namespaces=ns)
                if loc and loc.text:
                    result.sitemap_urls.append(loc.text)
        except Exception:
            pass

    internal_links = _extract_internal_links(homepage.soup, url, result.base_domain)
    priority_links = [link for link in internal_links if any(p.search(link) for p in PRIORITY_PATHS)]
    remaining_links = [link for link in internal_links if link not in priority_links]

    to_crawl = priority_links + remaining_links
    crawled = set(result.pages.keys())

    while len(result.pages) < max_pages and to_crawl:
        next_url = to_crawl.pop(0)
        if next_url in crawled:
            continue
        page = _fetch_page(next_url, timeout)
        result.pages[next_url] = page
        crawled.add(next_url)
        if not page.error and page.soup:
            new_links = _extract_internal_links(page.soup, next_url, result.base_domain)
            for link in new_links:
                if link not in crawled and link not in to_crawl:
                    to_crawl.append(link)

    return result
