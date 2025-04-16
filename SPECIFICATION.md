# RSSky Specification

## Overview
RSSky is a Python-based RSS feed aggregator and AI-powered news summarization system. It collects original articles from multiple RSS feeds, uses AI (configurable, defaults to Gemini 2.5 Pro or OpenAI, via LiteLLM proxy or direct API) to analyze and rate their importance, and generates a daily digest of the most significant stories. If a story is mentioned multiple times across different feeds, then it's summarised into one story. The final digest always cites all relevant sources and provides a link to them so the user can check the source articles directly. The system is designed to run daily, by default processing the last 24 hours of news (although this is configurable via command line options) while maintaining a cache to avoid any duplicate processing.

## Core Functionality

### 1. Feed Management
- Reads RSS feed URLs from any OPML file in the current directory, default is Feeds.opml
- Caches all raw feed data locally (refreshed every 6 hours by default)
- Supports various feed formats and handles redirects
- Uses safe filename generation for cache directories
- Maintains feed metadata including titles and last fetch times
- Handles HTTP redirects and custom user agents for feed fetching
- Supports RSS, Atom, and XML feed formats

### 2. Content Processing
- Fetches full article content from feed URLs
- Processes YouTube videos by fetching transcripts
- Strips HTML and formats text for AI processing
- Caches article content to minimize bandwidth usage
- Handles different date formats and timezones
- Content extraction strategies:
  - Regular articles: BeautifulSoup-based text extraction
  - YouTube: Transcript API with fallback options
  - Character limit handling: Truncates at 15000 chars for AI
- Date normalization:
  - Handles multiple date fields (published, updated)
  - Parses various date formats
  - If the dates in the feed look wrong, then parse the content of article/item for date clues
  - Defaults to current date if parsing fails

### 3. AI Integration
- Uses AI API (configurable, defaults to Gemini 2.5 Pro, OpenAI, or other via config.ini)
- **Strict JSON output is enforced for all AI responses via response schemas**
- Two-stage AI processing:
  1. Individual article analysis:
     - Rates importance (0-10 scale)
     - Generates ~200 word summary
     - Assesses potential impact
     - JSON response format:
       ```json
       {
           "importance": <0-10>,
           "summary": "<text>",
           "impact": "<text>",
           "date": "YYYY-MM-DD",
           "url": "<url>",
           "title": "<article title>",
           "full_content_available": <bool>,
           "feed": "<feed name>"
       }
       ```
  2. Daily digest generation:
     - Combines articles rated 5+
     - Groups by importance
     - Merges duplicate/similar stories into one
     - Maintains source attribution (all feeds and URLs for each story)
     - JSON response format:
       ```json
       {
           "stories": [
               {
                   "title": "<text>",
                   "importance_rating": <0-10>,
                   "summary": "<text>",
                   "date": "YYYY-MM-DD",
                   "sources": [
                       {
                           "name": "<feed_name>",
                           "title": "<article_title>",
                           "url": "<url>"
                       }
                   ]
               }
           ]
       }
       ```
- **No manual/fallback summaries or digests are used; the system always uses AI output with up to 3 retries for errors or invalid output.**
- AI output is cleaned to remove markdown code blocks and other wrappers before parsing.

### 4. Caching System
- Hierarchical cache structure:
  - /cache/[feed_id]/
    - rawfeed.json (feed data)
    - [article_id]/
      - fulltext.txt (article content)
      - summary.json (AI analysis)
- Cache invalidation:
  - Feeds: 6 hours (default, configurable)
  - Content: permanent
  - Summaries: permanent
- Cache file formats:
  - rawfeed.json: Complete feed data
  - summary.json: AI summary for each entry, in strict schema

### 5. Report Generation
- Generates daily HTML digest reports in the `output/` directory
- Each report includes:
  - Top stories (importance 5+)
  - Grouped similar stories
  - Source attributions for each story
  - Responsive, user-friendly layout
- Maintains an index.html linking all reports

## Technical Details

### Configuration
- All settings (API endpoint, model, temperature, importance criteria, etc.) are in `config.ini` (copy from `config.ini.example`)
- Sensitive files (`config.ini`, `Feeds.opml`, logs, cache, debug, output, test files) are excluded from version control via `.gitignore`

### Usage
- Run with:
  ```bash
  python rssky.py [--days N] [--clear-cache] [--config PATH] [--opml PATH]
  ```
- Options:
  - `--days N`: Process feeds from the last N days (default: 1)
  - `--clear-cache`: Clear the cache before running
  - `--config PATH`: Path to configuration file (default: config.ini)
  - `--opml PATH`: Path to OPML file (default: any .opml file in current directory)

## Changelog

- [Unreleased]:
  - Manual/fallback digest generation is fully removed. Digest generation always uses AI output with up to 3 retries; if all fail, the process aborts with an error.
  - Strict JSON schema enforcement for all AI output (summaries and digests)
  - Feed cache expiry is now 6 hours by default
  - Markdown code block and wrapper cleaning for AI output
  - .gitignore excludes sensitive/config files, cache, debug, output, test files