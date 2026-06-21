import os
import json
import time
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

class MockResponse:
    def __init__(self, text, url, status_code, headers):
        self.text = text
        self.url = url
        self.status_code = status_code
        self.headers = headers

class NetworkFreeMock:
    def __init__(self):
        self.dir_path = os.path.dirname(os.path.abspath(__file__))
        manifest_path = os.path.join(self.dir_path, "manifest.json")
        with open(manifest_path, "r") as f:
            self.manifest = json.load(f)

    def _resolve_url(self, url):
        # Normalize trailing slashes for lookup
        normalized = url
        if normalized in self.manifest:
            return self.manifest[normalized]
        if normalized.endswith("/") and normalized[:-1] in self.manifest:
            return self.manifest[normalized[:-1]]
        if not normalized.endswith("/") and normalized + "/" in self.manifest:
            return self.manifest[normalized + "/"]
        
        # Check standard domain prefixing
        clean = normalized.replace("https://www.", "https://").replace("http://www.", "https://").replace("http://", "https://")
        for k, v in self.manifest.items():
            k_clean = k.replace("https://www.", "https://").replace("http://www.", "https://").replace("http://", "https://")
            if clean == k_clean or clean.rstrip("/") == k_clean.rstrip("/"):
                return v
        return None

    def handle_get(self, url, *args, **kwargs):
        # Simulate original TTFB latency for the homepage
        is_homepage = "seo.com" in url and "sitemap.xml" not in url and "robots.txt" not in url and "/contact/" not in url and "/services/" not in url and "/ai/services/" not in url and "/ppc-management/" not in url
        if is_homepage:
            time.sleep(0.33)
            
        entry = self._resolve_url(url)
        if not entry:
            return MockResponse("404 Not Found", url, 404, {})
        
        file_path = os.path.join(self.dir_path, entry["file"])
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        else:
            text = ""
            
        # Dynamically append padding to homepage to simulate target page weight of > 500 KB
        if is_homepage:
            text += "\n<!-- " + ("x" * 520000) + " -->"
        
        return MockResponse(
            text=text,
            url=entry.get("final_url", url),
            status_code=entry.get("status_code", 200),
            headers=entry.get("headers", {})
        )

    def handle_head(self, url, *args, **kwargs):
        entry = self._resolve_url(url)
        if not entry:
            # Fallback for link checking: assume normal links pass
            # except those containing 'g2.com' which we know are 403 in the audit.
            if "g2.com" in url:
                return MockResponse("", url, 403, {})
            return MockResponse("", url, 200, {})
        
        return MockResponse(
            text="",
            url=entry.get("final_url", url),
            status_code=entry.get("status_code", 200),
            headers=entry.get("headers", {})
        )

def mock_network():
    mock_engine = NetworkFreeMock()
    
    # We want to patch the session and fetch_page in crawler, and requests in checks.technical
    session_mock = MagicMock()
    session_mock.get.side_effect = mock_engine.handle_get
    
    # We patch Session class instantiation, global req.get, req.head in crawler and checks.technical
    patches = [
        patch("crawler.req.Session", return_value=session_mock),
        patch("crawler.req.get", side_effect=mock_engine.handle_get),
        patch("checks.technical.req.head", side_effect=mock_engine.handle_head),
        patch("checks.technical.req.get", side_effect=mock_engine.handle_get),
    ]
    return patches
