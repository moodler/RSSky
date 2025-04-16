# RSSky Specification

## Overview
RSSky is a Python-based RSS feed aggregator and AI-powered news summarization system. It collects original articles from multiple RSS feeds, uses AI to analyze and rate their importance, and generates a daily digest of the most significant stories.  If a story is mentioned multiple times across different feeds, then it's summarised into one story. The final digest always cites all reelevant sources provides a link to them so the user can check the source articles directly.  The system is designed to run daily, by default processing the last 24 hours of news (although this is configurable via command line options) while maintaining a cache to avoid any duplicate processing.  

## Core Functionality

### 1. Feed Management
- Reads RSS feed URLs from any OPML file in the current directory, default is Feeds.opml
- Caches all raw feed data locally (refreshed hourly)
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
  - if the dates in the feed look wrong, then parse the content of article/item for date clues
  - Defaults to current date if parsing fails

### 3. AI Integration
- Uses AI API (configurable, defaults to Groq/Qwen model)
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
           "date": "YYYY-MM-DD"
       }
       ```
  2. Daily digest generation:
     - Combines articles rated 5+
     - Groups by importance 
     - Merges duplicate/similar stories into one
     - Maintains source attribution
     - JSON response format:
       ```json
       {
           "stories": [{
               "title": "<text>",
               "url": "<url>",
               "feed": "<feed_name>",
               "importance": <0-10>,
               "summary": "<text>",
               "impact": "<text>",
               "date": "YYYY-MM-DD"
           }]
       }
       ```

### 4. Caching System
- Hierarchical cache structure:
  - /cache/[feed_id]/
    - rawfeed.json (feed data)
    - [article_id]/
      - fulltext.txt (article content)
      - summary.json (AI analysis)
- Cache invalidation:
  - Feeds: 1 hour
  - Content: permanent
  - Summaries: permanent
- Cache file formats:
  - rawfeed.json:
    ```json
    {
        "timestamp": <unix_timestamp>,
        "feed_title": "<text>",
        "entries": [/* feed entries */]
    }
    ```
  - summary.json:
    ```json
    {
        "importance": <0-10>,
        "summary": "<text>",
        "impact": "<text>",
        "date": "YYYY-MM-DD",
        "url": "<url>",
        "title": "<text>"
    }
    ```

### 5. Report Generation
- Creates daily HTML reports
- Single section:
  - Stories
- Each story includes:
  - Title
  - Importance rating
  - Date
  - Summary
  - Impact assessment
  - Sources list with links
- Maintains an index of daily reports
- HTML styling:
  - Responsive layout
  - Story cards with importance-based highlighting
  - Source attribution with feed names
  - Clean typography and spacing
  - Visual hierarchy for importance levels
- File naming: YYYYMMDD.html format
- Index generation for browsing past reports

## JSON Digest Structure (as of latest changes)

- The daily digest JSON now contains a single top-level key `stories`, which is a list of story objects sorted by importance (descending).
- Each story object contains:
  - `title`: The story headline
  - `url`: The original article or source URL
  - `feed`: The name of the feed/source
  - `importance`: Numeric importance rating
  - `summary`: AI-generated summary of the story
  - `impact`: AI-generated impact assessment
  - `date`: Date of the story

- The previous structure with `high_impact` and `significant` lists is deprecated. All stories are now returned in a single, flattened list to avoid redundancy.

## Changelog
- [Unreleased]: Manual digest structure now returns a single `stories` list (see above).
- [Unreleased]: Manual/fallback digest generation is fully removed. Digest generation always uses AI output with up to 3 retries; if all fail, the process aborts with an error.

## Technical Details

### Configuration
- config.ini file controls:
  - API credentials
  - Model selection
  - Temperature/token settings
  - AI prompts
- Required sections:
  - [API]
    - api_key
    - model
    - temperature
    - max_tokens
  - [PROMPTS]
    - summary_prompt
    - report_prompt

### Error Handling
- Graceful degradation on network errors
- Cached content fallback
- JSON validation and cleaning
- API error recovery
- Specific error cases:
  - Feed fetch failures: Skip feed, continue others
  - Content extraction: Use cached or partial content
  - AI API errors: Return safe defaults
  - JSON parsing: Clean and retry, fallback format
  - Cache corruption: Rebuild from source
- Logging and debugging:
  - AI prompts saved to reportprompt.txt
  - AI responses saved to reportoutput.txt
  - Console progress and error reporting

## Command Line Interface
- Arguments:
  - --days: Number of days to process (default: 1)
  - --clear-cache: Clear all cache before running
- Exit codes:
  - 0: Success
  - 1: Configuration error
  - 2: API error
  - 3: Fatal processing error

## Usage Flow
1. Load OPML file
2. For each feed:
   - Check cache age
   - Fetch if needed
   - Process new entries
3. For each article:
   - Fetch & cache content
   - Generate AI summary
   - Store analysis
4. Daily compilation:
   - Collect recent summaries
   - Generate comprehensive digest
   - Create HTML report
5. Update index

## Output Format
- Daily HTML files (YYYYMMDD.html)
- Responsive design
- Story categorization
- Source attribution
- Navigation index 