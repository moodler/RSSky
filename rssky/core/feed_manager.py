"""
Feed Manager module for RSSky

This module handles loading feeds from OPML files and fetching feed entries.
It provides methods to parse OPML files, fetch and parse RSS feeds,
and filter feed entries by date.
"""

import os
import logging
import datetime
import xml.etree.ElementTree as ET
import requests
from urllib.parse import urlparse

import feedparser
from dateutil import parser as date_parser

from rssky.utils.helpers import safe_filename

logger = logging.getLogger("rssky.feeds")

class FeedManager:
    """Manages RSS feeds for RSSky"""
    
    def __init__(self, opml_file, cache_manager):
        """Initialize with OPML file path and cache manager"""
        self.opml_file = opml_file
        self.cache_manager = cache_manager
        self.user_agent = "RSSky Feed Reader/1.0"
    
    def load_feeds(self):
        """Load feeds from OPML file"""
        if not os.path.exists(self.opml_file):
            logger.error(f"OPML file not found: {self.opml_file}")
            return []
        
        try:
            # Parse the OPML file
            tree = ET.parse(self.opml_file)
            root = tree.getroot()
            
            # Find all outline elements with xmlUrl attribute
            feeds = []
            
            # Process outlines recursively
            def process_outline(outline, category=None):
                # Check if this is a feed
                xml_url = outline.get('xmlUrl')
                if xml_url:
                    feed = {
                        'url': xml_url,
                        'title': outline.get('title') or outline.get('text', 'Untitled Feed'),
                        'html_url': outline.get('htmlUrl', ''),
                        'category': category
                    }
                    feeds.append(feed)
                
                # If this is a category (no xmlUrl), process its children
                elif outline.get('text'):
                    cat_name = outline.get('text')
                    for child in outline:
                        process_outline(child, cat_name)
            
            # Start processing from the body element
            body = root.find('body')
            if body is not None:
                for outline in body:
                    process_outline(outline)
            
            logger.info(f"Loaded {len(feeds)} feeds from OPML")
            return feeds
            
        except Exception as e:
            logger.error(f"Error parsing OPML file: {e}")
            return []
    
    def get_feed_entries(self, feed, since_date=None):
        """Get entries from a feed, optionally filtered by date"""
        feed_url = feed['url']
        feed_title = feed.get('title', 'Untitled Feed')
        feed_id = self.cache_manager.generate_feed_id(feed_url, feed_title)
        
        # Check if we have a valid cached feed
        cached_feed = self.cache_manager.get_cached_feed(feed_id)
        
        if not cached_feed:
            # Fetch and parse the feed
            try:
                logger.info(f"Fetching feed: {feed['title']} ({feed_url})")
                feed_data = self._fetch_feed(feed_url)
                cached_feed = self.cache_manager.cache_feed(feed_id, feed_data)
            except Exception as e:
                logger.error(f"Error fetching feed {feed_url}: {e}")
                return []
        
        # Process the entries
        entries = cached_feed.get('entries', [])
        filtered_entries = []
        
        for entry in entries:
            # Add feed metadata to the entry
            entry['feed_title'] = feed['title']
            entry['feed_url'] = feed_url
            entry['feed_link'] = feed['html_url']
            entry['feed_id'] = feed_id
            entry['category'] = feed.get('category', '')
            
            # Process entry date
            entry_date = self._parse_entry_date(entry)
            entry['parsed_date'] = entry_date
            
            # Filter by date if needed
            if since_date and entry_date:
                if entry_date.date() < since_date:
                    continue
            
            filtered_entries.append(entry)
        
        logger.info(f"Got {len(filtered_entries)} entries from feed: {feed['title']}")
        return filtered_entries
    
    def _fetch_feed(self, feed_url):
        """Fetch and parse an RSS feed"""
        # Configure feedparser to follow redirects and use our user agent
        headers = {'User-Agent': self.user_agent}
        
        # First make a HEAD request to check for redirects
        try:
            response = requests.head(feed_url, headers=headers, allow_redirects=True, timeout=10)
            if response.status_code == 200 and response.url != feed_url:
                logger.info(f"Feed URL redirected: {feed_url} -> {response.url}")
                feed_url = response.url
        except Exception as e:
            logger.warning(f"Error checking feed redirects, continuing with original URL: {e}")
        
        # Parse the feed
        feed_data = feedparser.parse(feed_url, agent=self.user_agent)
        
        # Check for errors
        if feed_data.get('bozo', 0) == 1:
            exception = feed_data.get('bozo_exception')
            if exception:
                logger.warning(f"Feed parsing warning: {exception}")
        
        # Check if we got a valid feed
        if not feed_data.get('feed') or not feed_data.get('entries'):
            logger.error(f"Failed to parse feed: {feed_url}")
            raise ValueError(f"Invalid feed format: {feed_url}")
        
        return feed_data
    
    def _parse_entry_date(self, entry):
        """Extract and parse the publication date from an entry"""
        # Try various date fields
        date_fields = ['published', 'updated', 'pubDate', 'date']
        
        for field in date_fields:
            if field in entry and entry[field]:
                try:
                    return date_parser.parse(entry[field])
                except (ValueError, TypeError):
                    pass
        
        # If no valid date found, look in extension elements
        for field_name in entry:
            if field_name.endswith('_parsed') and field_name.startswith(('published', 'updated')):
                if isinstance(entry[field_name], tuple) and len(entry[field_name]) >= 9:
                    # Handle feedparser's time_struct format
                    try:
                        return datetime.datetime(*entry[field_name][:6])
                    except (ValueError, TypeError):
                        pass
        
        # Fallback to current date
        logger.warning(f"Could not parse date for entry: {entry.get('title', 'Unknown title')}")
        return datetime.datetime.now() 