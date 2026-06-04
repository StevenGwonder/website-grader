import unittest
from unittest.mock import patch, MagicMock
from crawler import CrawlResult, crawl_site, PageData

class TestCrawler(unittest.TestCase):
    @patch('crawler.req.get')
    def test_crawl_result_defaults(self, mock_get):
        mock_get.return_value = MagicMock(text="", url="https://example.com", status_code=200, headers={})
        result = crawl_site("https://example.com", max_pages=1)
        self.assertEqual(result.base_domain, "example.com")
        self.assertEqual(len(result.pages), 1)

    @patch('crawler.req.get')
    def test_crawl_extracts_internal_links(self, mock_get):
        mock_get.return_value = MagicMock(
            text='<html><body><a href="/about">About</a></body></html>',
            url="https://example.com",
            status_code=200,
            headers={}
        )
        result = crawl_site("https://example.com", max_pages=1)
        self.assertIn("https://example.com", result.pages)
        self.assertIn("https://example.com/about", result.all_links())

    @patch('crawler.req.get')
    def test_external_links_not_crawled(self, mock_get):
        mock_get.return_value = MagicMock(
            text='<html><body><a href="https://external.com">External</a></body></html>',
            url="https://example.com",
            status_code=200,
            headers={}
        )
        result = crawl_site("https://example.com", max_pages=1)
        self.assertNotIn("https://external.com", result.pages)

    @patch('crawler.req.get')
    def test_dead_site_handled(self, mock_get):
        mock_get.side_effect = Exception("Connection error")
        result = crawl_site("https://dead.com", max_pages=1)
        self.assertIsNotNone(result.error)
        self.assertEqual(len(result.pages), 0)

if __name__ == '__main__':
    unittest.main()
