"""
Cache Manager module for RSSky

This module handles caching of feed data, article content, and AI summaries.
It provides methods to read from and write to the cache, check cache validity,
and clear the cache when needed.
"""

import os
import json
import shutil
import logging
import hashlib
import datetime
from pathlib import Path
from rssky.utils.helpers import safe_filename

logger = logging.getLogger("rssky.cache")

class CacheManager:
    """Manages the caching system for RSSky"""
    
    def __init__(self, cache_dir="cache", retention_days=7, clear_cache=False):
        """Initialize the cache manager"""
        self.cache_dir = Path(cache_dir)
        self.retention_days = retention_days
        
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Clear cache if requested
        if clear_cache:
            self.clear_all_cache()
            logger.info("Cache cleared")
        
        # Clean up old cache entries
        self.clean_old_cache() # Updated method name
    
    def generate_feed_id(self, feed_url, feed_title=None):
        """Generate a safe identifier for a feed URL"""
        # If a feed title is provided, use it to create a human-readable identifier
        if feed_title:
            # Create a safe filename from the feed title
            safe_title = safe_filename(feed_title)
            # Ensure uniqueness by appending a shortened hash of the URL
            url_hash = hashlib.sha1(feed_url.encode()).hexdigest()[:8]
            return f"{safe_title}_{url_hash}"
        else:
            # Fallback to the original hash method for backward compatibility
            return hashlib.sha1(feed_url.encode()).hexdigest()
    
    @staticmethod
    def _generate_sanitized_path_component(text):
        """Generate a filesystem-safe component from text, reusing safe_filename."""
        # Reuse the existing utility function
        return safe_filename(text)

    @staticmethod
    def create_entry_cache_key(entry):
        """
        Creates a consistent, filesystem-safe cache key (directory name component)
        for a feed entry, prioritizing the title.
        """
        title = entry.get('title')
        unique_part = entry.get('link') or entry.get('id', '')

        if not title:
            # Fallback if title is missing
            base_key = unique_part if unique_part else 'missing_id'
            if '/' in base_key: # Try to get a filename/video ID from URL
                base_key = base_key.split('/')[-1]
                if '=' in base_key: # Handle youtube ?v= URLs
                    base_key = base_key.split('=')[-1]
            key_hash = hashlib.sha1(base_key.encode('utf-8')).hexdigest()[:8]
            sanitized_key = f"entry_{key_hash}"
            logger.warning(f"Entry missing title, using fallback key: {sanitized_key} (from {unique_part})")
            return sanitized_key
        else:
            # Use sanitized title + hash of unique part
            sanitized_title = CacheManager._generate_sanitized_path_component(title)
            title_hash = hashlib.sha1(unique_part.encode('utf-8')).hexdigest()[:8]
            return f"{sanitized_title}_{title_hash}"

    # Remove or comment out the old generate_entry_id
    # def generate_entry_id(self, entry):
    #     """Generate a safe identifier for a feed entry"""
    #     # Create a hash for uniqueness
    #     entry_id = entry.get('id', '')
    #     if not entry_id and 'link' in entry:
    #         entry_id = entry['link']
    #     
    #     # Add title for extra uniqueness if available
    #     if 'title' in entry:
    #         entry_id += entry.get('title', '')
    #     
    #     entry_hash = hashlib.md5(entry_id.encode()).hexdigest()[:8]
    #     
    #     # Get the entry title to create a human-readable folder name
    #     entry_title = entry.get('title', '')
    #     if entry_title:
    #         # Create a safe filename from the entry title
    #         safe_title = safe_filename(entry_title)
    #         # Limit the length of the title part to 40 characters to avoid very long paths
    #         if len(safe_title) > 40:
    #             safe_title = safe_title[:40]
    #         # Return a combination of the safe title and the hash
    #         return f"{safe_title}_{entry_hash}"
    #     else:
    #         # Fallback to just the hash for entries without a title
    #         return entry_hash
    
    def get_feed_cache_path(self, feed_id):
        """Get the cache path for a feed"""
        return self.cache_dir / feed_id
    
    def _get_entry_dir_path(self, feed_id, entry_id):
        """Helper to get the specific directory path for an entry."""
        feed_path = self.get_feed_cache_path(feed_id)
        return feed_path / entry_id # Directory name is the entry_id
    
    def get_rawfeed_path(self, feed_id):
        """Get the path to the cached raw feed data"""
        feed_dir = self.get_feed_cache_path(feed_id)
        feed_dir.mkdir(parents=True, exist_ok=True)
        return feed_dir / "rawfeed.json"
    
    def get_content_path(self, feed_id, entry_id):
        """Get the path to the cached full text of an entry"""
        entry_dir = self._get_entry_dir_path(feed_id, entry_id)
        return entry_dir / "fulltext.txt"
    
    def get_summary_path(self, feed_id, entry_id):
        """Get the path to the cached AI summary of an entry"""
        entry_dir = self._get_entry_dir_path(feed_id, entry_id)
        return entry_dir / "summary.json"
    
    def cache_feed(self, feed_id, feed_data):
        """Cache the raw feed data"""
        cache_data = {
            "timestamp": datetime.datetime.now().timestamp(),
            "feed_title": feed_data.get('feed', {}).get('title', 'Unknown Feed'),
            "entries": feed_data.get('entries', [])
        }
        
        feed_path = self.get_rawfeed_path(feed_id)
        with open(feed_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"Cached feed data: {feed_id}")
        return cache_data
    
    def get_cached_feed(self, feed_id, max_age_hours=6):
        """Get cached feed data if it exists and is not too old"""
        feed_path = self.get_rawfeed_path(feed_id)
        
        if not feed_path.exists():
            return None
        
        try:
            with open(feed_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Check if cache is too old
            cache_time = cache_data.get('timestamp', 0)
            cache_age = datetime.datetime.now().timestamp() - cache_time
            max_age_seconds = max_age_hours * 3600
            
            if cache_age > max_age_seconds:
                logger.debug(f"Feed cache too old: {feed_id}")
                return None
            
            logger.debug(f"Using cached feed data: {feed_id}")
            return cache_data
            
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error reading cached feed: {e}")
            return None
    
    def cache_content(self, feed_id, entry_id, content):
        """Cache the full text content of an entry"""
        content_path = self.get_content_path(feed_id, entry_id)
        entry_dir = content_path.parent # Use helper
        try:
            os.makedirs(entry_dir, exist_ok=True)
            # Ensure content is string before writing
            with open(content_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
            logger.debug(f"Cached entry content: {feed_id}/{entry_id}")
            return content
            
        except Exception as e:
            logger.error(f"Error caching content {content_path}: {e}")
    
    def get_cached_content(self, feed_id, entry_id):
        """Get cached content if it exists"""
        content_path = self.get_content_path(feed_id, entry_id)
        
        if not content_path.exists():
            return None
        
        try:
            with open(content_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.debug(f"Using cached content: {feed_id}/{entry_id}")
            return content
            
        except IOError as e:
            logger.error(f"Error reading cached content: {e}")
            return None
    
    def cache_summary(self, feed_id, entry_id, summary_data):
        """Cache the AI summary of an entry"""
        summary_path = self.get_summary_path(feed_id, entry_id)
        entry_dir = summary_path.parent # Use helper
        try:
            os.makedirs(entry_dir, exist_ok=True)
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=2)
        
            logger.debug(f"Cached entry summary: {feed_id}/{entry_id}")
            return summary_data
            
        except Exception as e:
            logger.error(f"Error caching summary {summary_path}: {e}")
    
    def get_entry_summary(self, feed_id, entry_id):
        """Get cached summary if it exists"""
        summary_path = self.get_summary_path(feed_id, entry_id)
        
        if not summary_path.exists():
            return None
        
        try:
            with open(summary_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading cached summary: {e}")
            return None
    
    def has_entry_summary(self, feed_id, entry_id):
        """Check if a summary is cached for an entry"""
        summary_path = self.get_summary_path(feed_id, entry_id)
        return summary_path.exists()
    
    def clear_entry_summary(self, feed_id, entry_id):
        """Clear the cached summary for an entry"""
        summary_path = self.get_summary_path(feed_id, entry_id)
        
        if summary_path.exists():
            try:
                summary_path.unlink()
                logger.debug(f"Cleared entry summary: {feed_id}/{entry_id}")
                return True
            except Exception as e:
                logger.error(f"Error clearing entry summary: {e}")
        return False
    
    def clear_feed_cache(self, feed_id):
        """Clear cached data for a specific feed"""
        feed_dir = self.get_feed_cache_path(feed_id)
        if feed_dir.exists():
            shutil.rmtree(feed_dir)
            logger.info(f"Cleared cache for feed: {feed_id}")
    
    def clear_all_cache(self):
        """Clear the entire cache"""
        for item in self.cache_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
        logger.info("Cleared all cache data")
    
    # Renamed method and added optional days_to_keep argument
    def clean_old_cache(self, days_to_keep=None):
        """Clean up cache entries older than the specified retention period."""
        # Use provided days_to_keep or fall back to instance default
        effective_retention_days = days_to_keep if days_to_keep is not None else self.retention_days
        
        cutoff_time = datetime.datetime.now() - datetime.timedelta(days=effective_retention_days)
        cutoff_timestamp = cutoff_time.timestamp()
        logger.info(f"Cleaning cache entries older than {cutoff_time} (Timestamp: {cutoff_timestamp}) using retention {effective_retention_days} days")

        cleaned_count = 0
        try:
            # Iterate through feed directories
            for feed_dir in self.cache_dir.iterdir():
                logger.debug(f"Checking feed directory: {feed_dir}")
                if feed_dir.is_dir():
                    # Iterate through entry directories within each feed directory
                    for entry_dir in feed_dir.iterdir():
                        logger.debug(f"  Checking entry directory: {entry_dir}")
                        if entry_dir.is_dir():
                            try:
                                # Get the modification time of the entry directory
                                entry_mtime = entry_dir.stat().st_mtime
                                entry_mtime_dt = datetime.datetime.fromtimestamp(entry_mtime)
                                is_older = entry_mtime < cutoff_timestamp
                                logger.debug(f"    Entry mtime: {entry_mtime_dt} ({entry_mtime}) | Older than cutoff? {is_older}")
                                if is_older:
                                    logger.info(f"    Attempting to remove old cache directory: {entry_dir}")
                                    shutil.rmtree(entry_dir)
                                    logger.debug(f"    Successfully removed old cache directory: {entry_dir}")
                                    cleaned_count += 1
                            except FileNotFoundError:
                                # Directory might have been removed in a previous run or concurrently
                                logger.warning(f"Cache directory not found during cleanup: {entry_dir}")
                            except Exception as e:
                                logger.error(f"Error cleaning cache directory {entry_dir}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error during cache cleanup iteration: {e}", exc_info=True)
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old cache entries.")
        else:
            logger.info("No old cache entries found to clean.")