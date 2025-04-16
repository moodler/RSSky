# RSSky

RSSky is a Python-based RSS feed aggregator that helps you stay updated with your favorite websites and blogs through their RSS feeds. It uses AI (configurable, defaults to Gemini 2.5 Pro or OpenAI) to analyze articles, rate their importance, and create a daily digest of the most significant stories.

## Features

- Read and aggregate multiple RSS feeds from OPML files
- Extract full article content from RSS feed entries
- Fetch YouTube video transcripts for video entries
- AI-powered rating and summarization of articles (strict JSON output enforced)
- Group similar stories together in the digest
- Generate beautiful HTML reports with a responsive design
- Maintain an index of all generated reports
- Smart caching system to minimize bandwidth usage (default cache expiry: 6 hours)
- Robust error handling and retry logic for AI calls

## Installation

1. Clone this repository:

```bash
git clone https://github.com/yourusername/RSSky.git  # Replace with your repository URL
```

2. Navigate to the project directory:

```bash
cd RSSky
```

3. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

1. Copy `config.ini.example` to `config.ini` and edit with your API credentials and preferences:

    ```ini
    [API]
    api_url = https://ai.moodle.com/v1/chat/completions  # Or your OpenAI endpoint
    api_key = your-api-key-here
    model = gemini-2.5-pro  # Or gpt-4, etc.
    temperature = 0.0
    max_tokens = 128000

    [Settings]
    importance_criteria = Focus on technological breakthroughs, scientific discoveries, major political events, and significant market movements.

    [PROMPTS]
    # Optional: You can customize the prompts if you want
    ```

2. Prepare your OPML file containing your RSS feed subscriptions. You can either:
   - Use an existing OPML file exported from another RSS reader
   - Create a new OPML file manually
   - Use the provided `Feeds.opml` file as a starting point (not tracked in git)

**Sensitive files like `config.ini`, `Feeds.opml`, logs, cache, and debug data are excluded from git via `.gitignore`.**

## Usage

1. Run the main script:

```bash
python rssky.py [--days N] [--clear-cache] [--config PATH] [--opml PATH]
```

Options:
- `--days N`: Process feeds from the last N days (default: 1)
- `--clear-cache`: Clear the cache before running
- `--config PATH`: Path to configuration file (default: config.ini)
- `--opml PATH`: Path to OPML file (default: any .opml file in current directory)

2. The script will:
   - Load your feeds from the OPML file
   - Fetch and process new entries
   - Generate AI summaries for each article (using strict response schemas)
   - Create a daily digest of important stories (AI output only, no manual fallback)
   - Generate an HTML report (importance ratings and layout improved)
   - Update the index

## AI Output Format & Robustness

- **Strict JSON output:** All AI calls for summaries and reports use response schemas to enforce the required JSON structure.
- **No manual fallback:** The system always uses AI-generated content, with retries and error handling if the format is invalid.
- **Formatting robustness:** The system cleans AI responses to remove markdown code blocks and other wrappers before parsing.

## Troubleshooting

- If you encounter issues with AI output format, check the logs and the `debug/` directory for raw prompts and responses.
- Make sure your API key, endpoint, and model are correct in `config.ini`.
- If you want to change the cache expiry, edit the `max_age_hours` parameter in `rssky/core/cache_manager.py` (default: 6 hours).

## Contributing

Pull requests and issues are welcome! Please ensure you do not commit sensitive files or credentials.

## License

MIT License