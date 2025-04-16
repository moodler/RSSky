"""
Helper utilities for RSSky

This module provides utility functions used throughout the application.
"""

import re
import unicodedata
import logging

logger = logging.getLogger("rssky.utils")

def safe_filename(text):
    """
    Convert a string to a safe filename by removing unsafe characters
    and replacing spaces with underscores.
    """
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    
    # Remove non-alphanumeric characters (except underscores, hyphens, and periods)
    text = re.sub(r'[^\w\-\.]', '_', text)
    
    # Replace multiple consecutive underscores with a single one
    text = re.sub(r'_{2,}', '_', text)
    
    # Trim leading/trailing underscores
    text = text.strip('_')
    
    # Ensure the filename is not empty
    if not text:
        text = "untitled"
    
    # Truncate if too long
    if len(text) > 100:
        text = text[:100]
    
    return text

def truncate_text(text, max_length=15000):
    """
    Truncate text to a maximum length, ensuring it doesn't cut off in the middle of a word.
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    # Find the last space within the limit
    last_space = text.rfind(' ', 0, max_length)
    if last_space != -1:
        truncated = text[:last_space]
    else:
        # If no space found, just cut at the limit
        truncated = text[:max_length]
    
    # Add ellipsis to indicate truncation
    truncated += "... [text truncated]"
    
    return truncated

def clean_html(html_text):
    """
    Remove HTML tags from text, preserving important whitespace.
    This is a very simple implementation that could be replaced with a more
    sophisticated one using BeautifulSoup.
    """
    if not html_text:
        return ""
    
    # Replace common block elements with newlines
    for tag in ['</p>', '</div>', '</h1>', '</h2>', '</h3>', '</h4>', '</h5>', '</h6>', '</li>', '</tr>']:
        html_text = html_text.replace(tag, tag + '\n\n')
    
    # Replace <br> tags with newlines
    html_text = html_text.replace('<br>', '\n')
    html_text = html_text.replace('<br/>', '\n')
    html_text = html_text.replace('<br />', '\n')
    
    # Remove all HTML tags
    html_text = re.sub(r'<[^>]*>', '', html_text)
    
    # Convert HTML entities
    html_text = html_text.replace('&nbsp;', ' ')
    html_text = html_text.replace('&amp;', '&')
    html_text = html_text.replace('&lt;', '<')
    html_text = html_text.replace('&gt;', '>')
    html_text = html_text.replace('&quot;', '"')
    html_text = html_text.replace('&#39;', "'")
    
    # Normalize whitespace
    html_text = re.sub(r'\n{3,}', '\n\n', html_text)
    html_text = re.sub(r' {2,}', ' ', html_text)
    
    return html_text.strip()

def format_date(date_obj, format_str="%Y-%m-%d"):
    """
    Format a datetime object as a string.
    """
    if not date_obj:
        return ""
    
    try:
        return date_obj.strftime(format_str)
    except (ValueError, TypeError):
        logger.warning(f"Error formatting date: {date_obj}")
        return ""

def is_youtube_url(url):
    """
    Check if a URL is from YouTube.
    """
    if not url:
        return False
    
    youtube_patterns = [
        r'(youtube\.com\/watch\?v=)',
        r'(youtu\.be\/)',
        r'(youtube\.com\/shorts\/)'
    ]
    
    for pattern in youtube_patterns:
        if re.search(pattern, url):
            return True
    
    return False

def extract_youtube_id(url):
    """
    Extract the YouTube video ID from a URL.
    """
    if not url:
        return None
    
    # Match standard YouTube watch URLs
    match = re.search(r'youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)
    
    # Match short YouTube URLs
    match = re.search(r'youtu\.be\/([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)
    
    # Match YouTube Shorts URLs
    match = re.search(r'youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)
    
    return None 