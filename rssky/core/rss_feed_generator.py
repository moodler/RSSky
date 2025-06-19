import os
import glob
import datetime
import configparser
from pathlib import Path
from xml.sax.saxutils import escape
from feedgen.feed import FeedGenerator


def generate_daily_rss_feed(output_dir, config_path, stories_by_date):
    """
    Generate an RSS feed (feed.rss) in output_dir, summarizing all daily digests.
    Each item is a daily digest with a paragraph summary and a link to the HTML file.
    stories_by_date: dict of {date_str: [story, ...]}
    """
    config = configparser.ConfigParser()
    config.read(config_path)
    feed_title = config.get("Feed", "feed_name", fallback="RSSky Daily Digest")
    feed_author = config.get("Feed", "author", fallback="RSSky Bot")
    site_url = config.get("Feed", "site_url", fallback="http://localhost/")

    fg = FeedGenerator()
    fg.title(feed_title)
    fg.link(href=site_url, rel="alternate")
    fg.description(f"{feed_title} - AI-generated summaries of daily news")
    fg.language('en')
    fg.author({'name': feed_author})

    # Sort by date descending
    for date_str in sorted(stories_by_date.keys(), reverse=True):
        stories = stories_by_date[date_str]
        # Compose a paragraph summary for the day
        if stories:
            summary_parts = []
            for s in stories:
                summary_item = s.get('summary', '')
                if isinstance(summary_item, list):
                    summary_parts.append(" ".join(summary_item))
                else:
                    summary_parts.append(summary_item)
            summary = " ".join(summary_parts)
            summary = summary[:800] + ("..." if len(summary) > 800 else "")
        else:
            summary = f"No stories for {date_str}."
        # Compose link to HTML file
        html_file = f"{date_str}.html"
        pub_date = datetime.datetime.strptime(date_str, "%Y%m%d").strftime("%a, %d %b %Y 00:00:00 +0000")
        fe = fg.add_entry()
        fe.title(f"Daily Digest for {date_str}")
        fe.link(href=f"{site_url}output/{html_file}")
        fe.guid(date_str, permalink=False)
        fe.pubDate(pub_date)
        fe.description(summary)
    # Write RSS file
    rss_path = Path(output_dir) / "feed.rss"
    fg.rss_file(str(rss_path), pretty=True)
    return str(rss_path)
