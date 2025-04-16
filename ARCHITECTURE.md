# RSSky Architecture

This document outlines the architecture of the RSSky system, explaining the design choices, module organization, and implementation details.

## Overview

RSSky is designed as a modular, pipeline-oriented system that processes RSS feeds through several distinct stages:

1. Feed collection and parsing
2. Content extraction
3. AI-powered analysis and summarization 
4. Summary aggregation and digest generation
5. HTML report generation

The system follows a clean, modular architecture with clear separation of concerns and minimal coupling between components. This design allows for easy modification, extension, and testing of individual components.

## Directory Structure

```
rssky/
├── rssky.py                  # Main application entry point
├── config.ini.example        # Example configuration template
├── requirements.txt          # Python dependencies
├── README.md                 # Documentation
├── rssky/                    # Main package
│   ├── __init__.py           # Package initialization
│   ├── core/                 # Core functionality 
│   │   ├── __init__.py
│   │   ├── config.py         # Configuration management
│   │   ├── feed_manager.py   # Feed fetching and parsing
│   │   ├── content_processor.py # Content extraction
│   │   ├── ai_processor.py   # AI summarization
│   │   ├── cache_manager.py  # Caching system
│   │   └── report_generator.py # HTML generation
│   ├── utils/                # Utility functions
│   │   ├── __init__.py
│   │   └── helpers.py        # Common utility functions
│   ├── cache/                # Cache directory (generated)
│   └── output/               # Output directory (generated)
```

## Module Responsibilities

### Main Application (`rssky.py`)

The main application orchestrates the entire process, initializing components, managing the processing pipeline, and handling errors. It:
- Parses command-line arguments
- Sets up logging
- Initializes all components
- Coordinates the processing flow
- Handles high-level errors

### Configuration (`config.py`)

Manages loading and validating configuration from config.ini files. Design choices:
- Default configurations are embedded, making the application work out-of-the-box
- Configuration is validated on startup
- Typed accessors (getint, getfloat) for type safety
- Section-specific getters to abstract away configuration structure

### Cache Manager (`cache_manager.py`)

Handles caching of feed data, article content, and AI summaries. Key design decisions:
- Hierarchical caching structure for feeds, entries, and associated data
- MD5 hashing for safe, unique identifiers
- Cache invalidation based on retention period (7 days by default)
- Feed caches expire after 1 hour (configurable)
- Content and summary caches are permanent unless manually cleared
- Clear separation of caching logic from processing logic

### Feed Manager (`feed_manager.py`)

Handles loading feeds from OPML files and retrieving entries. Key features:
- Recursive OPML parsing preserving category structure
- Handling of feed redirects
- Multiple date field parsing strategies
- HTTP error recovery
- Metadata enrichment (adding feed information to entries)

### Content Processor (`content_processor.py`)

Extracts full content from feed entries. Design choices:
- Special handling for YouTube videos (transcript extraction)
- Fallback strategies for content extraction:
  1. Try feed-provided content first
  2. If insufficient, fetch from URL
  3. BeautifulSoup-based extraction using common patterns
- Content cleaning and truncation
- Content type detection (YouTube vs. articles)

### AI Processor (`ai_processor.py`)

Handles AI analysis of content and generation of summaries and digests. Design decisions:
- Two-stage AI processing:
  1. Individual article summarization and rating
  2. Digest generation with article grouping
- Response validation and error recovery
- JSON parsing with fallback mechanisms
- Debug output saving for troubleshooting
- Model-agnostic API interface
- Configurable prompts with importance criteria injection

### Report Generator (`report_generator.py`)

Generates HTML reports and maintains the report index. Features:
- Responsive HTML design
- Automatic index maintenance
- Date-based file organization
- Styling based on importance ratings

### Utilities (`helpers.py`)

Common utility functions used across modules:
- Safe filename generation
- Text truncation
- HTML cleaning
- Date formatting
- YouTube URL detection and ID extraction

## Data Flow

1. **Feed Collection**:
   - Load OPML file → Parse feeds → Fetch feed data → Cache feed data

2. **Entry Processing**:
   - For each feed → Get entries → For each entry → Extract content → Generate AI summary

3. **Digest Generation**:
   - Collect all processed entries → Filter by importance (≥5) → Group and analyze → Generate digest

4. **Report Generation**:
   - Format digest as HTML → Create daily report file → Update index

## Key Design Decisions

### Caching Strategy

- **Why**: To minimize bandwidth usage, reduce API costs, and improve performance.
- **Implementation**: Three-level caching (feeds, content, summaries) with different invalidation strategies.
- **Benefit**: Allows for incremental processing and handles network/API failures gracefully.

### Pipeline Architecture

- **Why**: To maintain separation of concerns and allow for easy modification of individual steps.
- **Implementation**: Each stage is handled by a dedicated class with clear interfaces.
- **Benefit**: Easy to extend, modify, or replace individual components without affecting others.

### Configuration Management

- **Why**: To allow customization without code changes while providing sensible defaults.
- **Implementation**: INI-based configuration with embedded defaults and section-specific accessors.
- **Benefit**: Works out-of-the-box but allows for deep customization.

### Error Handling and Fallbacks

- **Why**: To ensure the system continues to function even when components fail.
- **Implementation**: Extensive error catching with graceful degradation and fallback mechanisms.
- **Benefit**: Robust operation even with missing or invalid data.

### Model Agnostic AI Interface

- **Why**: To support different AI providers without changing the core logic.
- **Implementation**: Generic API interface with configurable endpoint, model, and authentication.
- **Benefit**: Easy to switch between OpenAI, Groq, or other compatible providers.

## Extensibility Points

The architecture was designed with several extension points in mind:

1. **New Content Sources**: 
   - Add new handlers in ContentProcessor for different content types
   - Current implementation handles articles and YouTube; can be extended for podcasts, social media, etc.

2. **Alternative AI Providers**:
   - Configurable API URL and parameters
   - JSON response parsing is designed to be flexible

3. **Output Formats**:
   - The Report Generator can be extended to support different output formats (PDF, JSON, email, etc.)

4. **Custom Importance Rating**:
   - Configurable importance criteria passed to the AI
   - Prompt templates can be customized

## Performance Considerations

1. **Caching**: Reduces unnecessary network requests and AI API calls
2. **Parallel Processing**: The architecture supports potential parallel processing of feeds and entries
3. **Incremental Processing**: Only processes new or updated entries, not the entire feed history
4. **Resource Management**: Configurable control of AI token usage and memory footprint

## Challenges and Trade-offs

1. **Cache vs. Freshness**: 
   - Trade-off: Feed caches expire after 1 hour, balancing freshness against bandwidth usage
   - Content and summary caches are permanent to reduce API costs

2. **HTML Extraction Quality**:
   - Challenge: Extracting the main content from arbitrary web pages is difficult
   - Solution: Multi-stage fallback approach but still imperfect

3. **Dependency on External AI**:
   - Trade-off: Relying on external API for intelligence vs. local processing
   - Mitigation: Fallback mechanisms when AI fails

4. **YouTube Transcript Availability**:
   - Challenge: Not all YouTube videos have transcripts
   - Solution: Graceful degradation when transcripts are unavailable

## Future Improvement Areas

1. **Parallel Processing**: Implement concurrent feed fetching and processing
2. **Enhanced Content Extraction**: More sophisticated techniques for extracting article content
3. **Similarity Detection**: Better mechanisms for identifying similar stories
4. **User Interface**: Web interface for configuration and viewing reports
5. **Feed Discovery**: Automatic feed discovery from website URLs
6. **Notification System**: Email or other notification methods for new digests 