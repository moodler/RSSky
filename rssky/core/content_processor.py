"""
Content Processor module for RSSky

This module handles the extraction and processing of content from feed entries,
including regular articles and YouTube videos. It also handles HTML cleaning
and text truncation.
"""

import logging
import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from rssky.utils.helpers import is_youtube_url, clean_html, extract_youtube_id
from rssky.core.cache_manager import CacheManager

logger = logging.getLogger("rssky.content")

class ContentProcessor:
    """Processes content from feed entries"""
    
    def __init__(self, cache_manager):
        """Initialize with cache manager"""
        self.cache_manager = cache_manager
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def process_entry(self, entry):
        """Process a feed entry and extract its content"""
        # Generate IDs for caching
        # Get Feed ID passed into the entry object by FeedManager
        feed_id = entry.get('feed_id')
        if not feed_id:
             logger.error(f"Missing feed_id in entry: {entry.get('title')}. Cannot process.")
             return None # Cannot cache without feed_id

        # Use the new consistent method for entry cache key
        try:
            entry_id = CacheManager.create_entry_cache_key(entry)
        except Exception as e:
            logger.error(f"Failed to create entry cache key for '{entry.get('title', 'Unknown')}': {e}", exc_info=True)
            return None # Cannot process without entry_id

        # Check if content is already cached using the new entry_id
        cached_content = self.cache_manager.get_cached_content(feed_id, entry_id)
        if cached_content:
            logger.debug(f"Using cached content for entry: {feed_id}/{entry_id}")
            return cached_content
        
        # Extract content based on entry type
        content = None
        link = entry.get('link')
        
        if link and is_youtube_url(link):
            # Extract YouTube transcript
            content = self._process_youtube_entry(entry)
        else:
            # Extract article content
            content = self._process_article_entry(entry)
        
        # Cache the content using the new entry_id
        if content:
            try:
                self.cache_manager.cache_content(feed_id, entry_id, content)
            except Exception as e:
                logger.error(f"Failed caching content for {feed_id}/{entry_id}: {e}", exc_info=True)
                # Decide if we should return None or the content even if caching failed
                # Returning content might be better, as it can still be processed

        return content
    
    def _process_article_entry(self, entry):
        """Process a regular article entry"""
        # Try to use content from feed first
        content = ""
        
        # Check various content fields
        content_fields = ['content', 'summary', 'description']
        for field in content_fields:
            if field in entry and entry[field]:
                if isinstance(entry[field], list):
                    # Some feeds provide content as a list of dicts with a 'value' key
                    for content_item in entry[field]:
                        if isinstance(content_item, dict) and 'value' in content_item:
                            content = content_item['value']
                            break
                else:
                    content = entry[field]
                
                if content:
                    break
        
        # If no content in feed, try to fetch from URL
        if not content and 'link' in entry:
            content = self._fetch_article_content(entry['link'])
        
        # Clean the content
        if content:
            content = clean_html(content)
            # No longer truncating content for cache storage
        else:
            # If no content found, create a minimal representation
            title = entry.get('title', 'Untitled')
            logger.warning(f"No content found for entry: {title}")
            content = f"Title: {title}\nNo content available."
        
        return content
    
    def _process_youtube_entry(self, entry):
        """Process a YouTube entry by fetching its transcript"""
        video_url = entry.get('link', '')
        video_id = extract_youtube_id(video_url)
        
        if not video_id:
            logger.error(f"Could not extract YouTube ID from URL: {video_url}")
            return f"Title: {entry.get('title', 'YouTube Video')}\n[Could not extract YouTube video ID]"
        
        try:
            # Try to get transcript
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            
            # Format transcript text
            transcript_text = ""
            for segment in transcript_list:
                text = segment.get('text', '').strip()
                if text:
                    transcript_text += f"{text}\n"
            
            # Add video metadata
            title = entry.get('title', 'YouTube Video')
            content = f"Title: {title}\nURL: {video_url}\n\nTranscript:\n{transcript_text}"
            
            # No longer truncating content for cache storage
            return content
            
        except (NoTranscriptFound, TranscriptsDisabled) as e:
            logger.warning(f"No transcript available for YouTube video: {video_id} - {e}")
            # Get video title and make a simple content representation
            return f"Title: {entry.get('title', 'YouTube Video')}\nURL: {video_url}\n\n[No transcript available]"
            
        except Exception as e:
            logger.error(f"Error fetching YouTube transcript: {e}")
            return f"Title: {entry.get('title', 'YouTube Video')}\nURL: {video_url}\n\n[Error fetching transcript]"
    
    def _fetch_article_content(self, url):
        """Fetch and extract the main content from an article URL"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch URL: {url} (Status: {response.status_code})")
                return ""
            
            # Use BeautifulSoup to extract the main content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for tag in soup.select('script, style, nav, footer, header, .sidebar, .comments, .ad, .advertisement'):
                tag.decompose()
            
            # Try to find the main article content using common patterns
            article_content = None
            
            # Try article tag first
            article = soup.find('article')
            if article:
                article_content = article
            
            # Try common content div patterns
            if not article_content:
                for selector in ['.content', '.post-content', '.entry-content', '.article-content', 
                                '#content', '.main-content', '.post', '.article', '.story',
                                '[itemprop="articleBody"]']:
                    content_div = soup.select_one(selector)
                    if content_div:
                        article_content = content_div
                        break
            
            # If still no content, use body as fallback
            if not article_content:
                article_content = soup.body
            
            # Extract all paragraphs from the content
            if article_content:
                paragraphs = article_content.find_all('p')
                content = "\n\n".join(p.get_text() for p in paragraphs if p.get_text().strip())
                
                # If no paragraphs found, just use the whole content
                if not content and article_content:
                    content = article_content.get_text()
                
                return content
                
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting content from URL: {url} - {e}")
            return "" 