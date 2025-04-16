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
git clone https://github.com/moodler/RSSky.git  
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
    api_url = https://your.ai.provider/v1/chat/completions 
    api_key = your-api-key-here
    model = gemini-2.5-pro  # Or gpt-4, etc.
    temperature = 0.5
    max_tokens = 128000

    [Settings]
    importance_criteria = Focus on technological breakthroughs, scientific discoveries, major political events, and significant market movements.

    [PROMPTS]
    # Optional: You can customize the prompts if you want
    ```

2. Prepare your OPML file containing your RSS feed subscriptions. 
   - The best way to make this is to export one from your RSS reader, or 
   - Create a new OPML file manually

## Usage

1. Run the main script:

```bash
python rssky.py [--days N] [--clear-cache] [--config PATH] [--opml PATH]
```

Options:
- `--days N`: Process feeds from the last N days (default: 1)
- `--clear-cache`: Clear the cache before running
- `--config PATH`: Path to configuration file (default: config.ini)
- `--opml PATH`: Path to OPML file (default: the first .opml file in current directory)

2. The script will:
   - Load your feeds from the OPML file
   - Fetch all the feeds and process new entries
   - Uses AI to Generate AI summaries for each recent article in each feed
   - Uses AI to create a daily digest of important stories
   - Generate an HTML report (importance ratings and layout improved)
   - Update the index and an outgoing RSS feed for easy consumption


## Troubleshooting

- If you encounter issues with AI output format, check the logs and the `debug/` directory for raw prompts and responses.
- Make sure your API key, endpoint, and model are correct in `config.ini`.

## Contributing

Pull requests and issues are welcome! Please ensure you do not commit sensitive files or credentials.

## License

Martin Dougiamas, GPL v3 License
