# RSSky

RSSky is a Python-based RSS feed aggregator that helps you stay updated with your favorite websites and blogs through their RSS feeds. It uses AI to analyze articles, rate their importance, and create a daily digest of the most significant stories.

## Features

- Read and aggregate multiple RSS feeds from OPML files
- Extract full article content from RSS feed entries
- Fetch YouTube video transcripts for video entries
- AI-powered rating and summarization of articles
- Group similar stories together in the digest
- Generate beautiful HTML reports with a responsive design
- Maintain an index of all generated reports
- Smart caching system to minimize bandwidth usage

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

1. Create a `config.ini` file in the project root directory with the following structure:

    ```ini
    [API]
    api_url = https://api.openai.com/v1/chat/completions
    api_key = your-api-key-here
    model = gpt-4
    temperature = 0.7
    max_tokens = 1000

    [Settings]
    importance_criteria = Focus on technological breakthroughs, scientific discoveries, major political events, and significant market movements.

    [PROMPTS]
    # Optional: You can customize the prompts if you want
    ```

2. Prepare your OPML file containing your RSS feed subscriptions. You can either:
   - Use an existing OPML file exported from another RSS reader
   - Create a new OPML file manually
   - Use the provided `Feeds.opml` file as a starting point

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
   - Generate AI summaries for each article
   - Create a daily digest of important stories
   - Generate an HTML report
   - Update the index

3. The output HTML reports will be saved in the `output` directory:
   - Daily reports in YYYYMMDD.html format
   - index.html linking to all reports

## Customization

### Importance Criteria

You can customize what the AI considers "important" by modifying the `importance_criteria` setting in the config.ini file. For example:

```ini
[Settings]
importance_criteria = Focus on technology trends, startup news, and venture capital funding.
```

### AI Provider

By default, RSSky is configured to use OpenAI's API, but you can change the API endpoint, model, and parameters:

```ini
[API]
api_url = https://api.groq.com/openai/v1/chat/completions
api_key = your-groq-api-key
model = llama3-8b-8192
temperature = 0.5
max_tokens = 2000
```

## Changelog

### [Unreleased]
- Changed the manual digest structure in `AIProcessor._create_manual_digest` to return a single `stories` list instead of separate `high_impact` and `significant` categories, eliminating redundancy and flattening the report data structure. This aligns with the new prompt and report requirements.
- Manual/fallback digest generation is now fully removed. The system will always use the AI output for the daily digest. If the AI output is invalid or fails, the system will retry up to 3 times and abort with an error if all attempts fail.

## Troubleshooting

- Check the log file `rssky.log` for detailed logs
- Examine the debug files `summaryprompt.txt` and `reportprompt.txt` to see the prompts sent to the AI
- If you encounter API issues, verify your API key and model name are correct

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues to improve RSSky.

## License

This project is licensed under the MIT License - see the LICENSE file for details.