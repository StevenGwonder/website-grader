import unittest
from unittest.mock import patch, MagicMock
from crawler import CrawlResult, crawl_site, PageData

def _mock_resp(text="<html><body></body></html>", url="https://example.com", status=200):
    return MagicMock(text=text, url=url, status_code=status, headers={})

def _mock_session(resp=None, exc=None):
    """Mock a curl_cffi Session that returns resp or raises exc."""
    session = MagicMock()
    if exc:
        session.get.side_effect = exc
    else:
        session.get.return_value = resp or _mock_resp()
    return session

class TestCrawler(unittest.TestCase):
    @patch('crawler.req.Session')
    def test_crawl_result_defaults(self, mock_session_cls):
        mock_session_cls.return_value = _mock_session(_mock_resp(
            text="<html><body></body></html>", url="https://example.com"))
        result = crawl_site("https://example.com", max_pages=1)
        self.assertEqual(result.base_domain, "example.com")
        self.assertEqual(len(result.pages), 1)

    @patch('crawler.req.Session')
    def test_crawl_extracts_internal_links(self, mock_session_cls):
        mock_session_cls.return_value = _mock_session(_mock_resp(
            text='<html><body><a href="/about">About</a></body></html>',
            url="https://example.com"))
        result = crawl_site("https://example.com", max_pages=1)
        self.assertIn("https://example.com", result.pages)
        self.assertIn("https://example.com/about", result.all_links())

    @patch('crawler.req.Session')
    def test_external_links_not_crawled(self, mock_session_cls):
        mock_session_cls.return_value = _mock_session(_mock_resp(
            text='<html><body><a href="https://external.com">External</a></body></html>',
            url="https://example.com"))
        result = crawl_site("https://example.com", max_pages=1)
        self.assertNotIn("https://external.com", result.pages)

    @patch('crawler.req.Session')
    def test_dead_site_handled(self, mock_session_cls):
        mock_session_cls.return_value = _mock_session(exc=Exception("Connection error"))
        result = crawl_site("https://dead.com", max_pages=1)
        self.assertIsNotNone(result.error)
        self.assertEqual(len(result.pages), 0)

if __name__ == '__main__':
    unittest.main()
