import unittest
from unittest.mock import patch, MagicMock
import json
import os
import shutil
from pathlib import Path

# Ensure the project root is in the Python path
import sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from rssky.core.ai_processor import AIProcessor
from rssky.core.cache_manager import CacheManager
from rssky.core.config import Config

class TestAIProcessor(unittest.TestCase):

    def setUp(self):
        """Set up a test environment."""
        self.test_cache_dir = Path("./test_cache_ai")
        self.test_cache_dir.mkdir(exist_ok=True)
        
        self.cache_manager = CacheManager(cache_dir=str(self.test_cache_dir))
        
        # Create a mock config object
        self.mock_config = MagicMock(spec=Config)
        self.mock_config.get_api_config.return_value = {
            'api_url': 'https://api.test.com/v1/chat/completions',
            'api_key': 'test_key',
            'model': 'test-model',
            'temperature': 0.5,
            'max_tokens': 1000
        }
        self.mock_config.get_summary_prompt.return_value = "Summarize: {article_content}"
        self.mock_config.get_report_prompt.return_value = "Digest: {summaries_json}"

        self.ai_processor = AIProcessor(config=self.mock_config, cache_manager=self.cache_manager)

        self.test_feed_url = "http://test.com/feed"
        self.test_feed_title = "Test Feed"
        self.test_feed_id = self.cache_manager.generate_feed_id(self.test_feed_url, self.test_feed_title)
        self.test_entry = {
            'title': 'Test Entry',
            'link': 'http://test.com/entry',
            'id': '12345',
            'published': '2023-01-01T12:00:00Z',
            'feed_title': self.test_feed_title,
            'feed_id': self.test_feed_id
        }
        self.test_entry_id = self.cache_manager.create_entry_cache_key(self.test_entry)
        
        # Cache some mock content for the entry
        self.cache_manager.cache_content(self.test_feed_id, self.test_entry_id, "This is the article content.")

    def tearDown(self):
        """Clean up the test environment."""
        if self.test_cache_dir.exists():
            shutil.rmtree(self.test_cache_dir)
        debug_dir = Path("debug")
        if debug_dir.exists():
            shutil.rmtree(debug_dir)

    @patch('rssky.core.ai_processor.AIProcessor._make_ai_request')
    def test_summarize_entry_success(self, mock_make_ai_request):
        """Test successful summarization of an entry."""
        mock_response = {
            "importance": 8,
            "summary": "This is a test summary.",
            "impact": "High",
            "date": "2023-01-01"
        }
        mock_make_ai_request.return_value = (json.dumps(mock_response), mock_response)

        result = self.ai_processor.summarize_entry(self.test_entry, self.test_feed_id, self.test_feed_title)

        self.assertEqual(result['summary'], "This is a test summary.")
        self.assertEqual(result['importance'], 8)
        mock_make_ai_request.assert_called_once()
        
        # Verify that the summary was cached
        cached_summary = self.cache_manager.get_entry_summary(self.test_feed_id, self.test_entry_id)
        self.assertIsNotNone(cached_summary)
        self.assertEqual(cached_summary['summary'], "This is a test summary.")

    @patch('rssky.core.ai_processor.AIProcessor._make_ai_request')
    def test_summarize_entry_retry_and_fail(self, mock_make_ai_request):
        """Test that summarize_entry retries on failure and eventually returns a fallback."""
        # Simulate failure on all attempts
        mock_make_ai_request.return_value = (None, None)

        result = self.ai_processor.summarize_entry(self.test_entry, self.test_feed_id, self.test_feed_title)

        self.assertEqual(mock_make_ai_request.call_count, 3)
        self.assertIn("could not be extracted", result['summary'])
        self.assertEqual(result['importance'], 5) # Fallback importance

        # Verify that the fallback summary was cached
        cached_summary = self.cache_manager.get_entry_summary(self.test_feed_id, self.test_entry_id)
        self.assertIsNotNone(cached_summary)
        self.assertIn("could not be extracted", cached_summary['summary'])

    @patch('rssky.core.ai_processor.AIProcessor._make_ai_request')
    def test_generate_digest_success(self, mock_make_ai_request):
        """Test successful generation of a daily digest."""
        # Setup: Create a cached summary for an entry
        summary_data = {
            "importance": 9,
            "summary": "A very important summary.",
            "impact": "Critical",
            "date": "2023-01-01",
            "title": "Test Entry",
            "url": "http://test.com/entry",
            "feed": self.test_feed_title
        }
        self.cache_manager.cache_summary(self.test_feed_id, self.test_entry_id, summary_data)

        # Mock the AI response for the digest
        mock_digest_response = {
            "stories": [{
                "title": "Digested: Test Entry",
                "importance_rating": 9,
                "summary": "This is the digested summary.",
                "date": "2023-01-01",
                "sources": [{"name": self.test_feed_title, "title": "Test Entry", "url": "http://test.com/entry"}]
            }]
        }
        mock_make_ai_request.return_value = (json.dumps(mock_digest_response), mock_digest_response)

        digest = self.ai_processor.generate_digest("20230101", [self.test_entry])

        self.assertIn("stories", digest)
        self.assertEqual(len(digest['stories']), 1)
        self.assertEqual(digest['stories'][0]['title'], "Digested: Test Entry")
        mock_make_ai_request.assert_called_once()

    @patch('rssky.core.ai_processor.AIProcessor._make_ai_request')
    def test_generate_digest_no_significant_entries(self, mock_make_ai_request):
        """Test digest generation when there are no entries with high enough importance."""
        # Setup: Create a cached summary with low importance
        summary_data = {"importance": 3, "summary": "Not very important."}
        self.cache_manager.cache_summary(self.test_feed_id, self.test_entry_id, summary_data)

        digest = self.ai_processor.generate_digest("20230101", [self.test_entry])

        self.assertEqual(digest, {"high_impact": [], "significant": []})
        mock_make_ai_request.assert_not_called()

    @patch('rssky.core.ai_processor.AIProcessor._make_ai_request')
    def test_generate_digest_ai_failure(self, mock_make_ai_request):
        """Test that digest generation raises an error if the AI call fails repeatedly."""
        # Setup: Create a valid cached summary to trigger the digest process
        summary_data = {"importance": 8, "summary": "Important stuff."}
        self.cache_manager.cache_summary(self.test_feed_id, self.test_entry_id, summary_data)

        # Simulate AI failure
        mock_make_ai_request.return_value = (None, None)

        with self.assertRaises(RuntimeError):
            self.ai_processor.generate_digest("20230101", [self.test_entry])
        
        self.assertEqual(mock_make_ai_request.call_count, 3)

if __name__ == '__main__':
    unittest.main()