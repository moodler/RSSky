#!/usr/bin/env python3
"""
RSSky - A Python-based RSS feed aggregator with AI-powered news summarization

This is the main application file that orchestrates the entire process:
1. Parse command line arguments
2. Load configuration
3. Process RSS feeds
4. Generate AI summaries
5. Create daily digest
6. Generate HTML reports
"""

import os
import sys
import argparse
import datetime
import logging
from pathlib import Path

# Import the test runner function
from tests.run_tests import run_tests 

from rssky.core.config import Config
from rssky.core.feed_manager import FeedManager
from rssky.core.content_processor import ContentProcessor
from rssky.core.ai_processor import AIProcessor
from rssky.core.cache_manager import CacheManager
from rssky.core.report_generator import ReportGenerator


def setup_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("rssky.log"),
        ],
    )
    return logging.getLogger("rssky")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="RSSky - RSS feed aggregator with AI summaries")
    parser.add_argument("--days", type=int, default=3, help="Process feeds from the last N days (default: 3)")
    parser.add_argument("--clear-cache", action="store_true", help="Clear the cache before running")
    parser.add_argument("--config", default="config.ini", help="Path to configuration file (default: config.ini)")
    parser.add_argument("--opml", help="Path to OPML file (default: any .opml file in current directory)")
    parser.add_argument("--skip-prefetch", action="store_true", help="Skip prefetching of all feeds from the last 7 days")
    return parser.parse_args()


def find_opml_file(specified_file=None):
    """Find OPML file in the current directory or use the specified one"""
    if specified_file and os.path.exists(specified_file):
        return specified_file
    
    # Look for any .opml file in the current directory
    opml_files = list(Path(".").glob("*.opml"))
    if opml_files:
        return str(opml_files[0])
    
    logging.error("No OPML file found")
    sys.exit(1)


def main():
    """Main application entry point"""
    # Empty debug directory at the start of every run
    debug_dir = Path("debug")
    if debug_dir.exists() and debug_dir.is_dir():
        for item in debug_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                import shutil
                shutil.rmtree(item)
    logger = setup_logging()
    logger.info("Emptied debug directory.")
    logger.info("Starting RSSky")

    # Run unit tests first
    logger.info("Running unit tests...")
    test_result = run_tests()
    if test_result != 0:
        logger.error("Unit tests failed. Exiting.")
        sys.exit(test_result) # Exit with the test runner's exit code
    logger.info("Unit tests passed successfully.")
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Find OPML file
    opml_file = find_opml_file(args.opml)
    logger.info(f"Using OPML file: {opml_file}")
    
    # Load configuration
    try:
        config = Config(args.config)
        logger.info("Configuration loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Initialize components
    try:
        cache_manager = CacheManager(
            cache_dir="cache", 
            retention_days=7,
            clear_cache=args.clear_cache
        )
        
        feed_manager = FeedManager(
            opml_file=opml_file,
            cache_manager=cache_manager
        )
        
        content_processor = ContentProcessor(
            cache_manager=cache_manager
        )
        
        ai_processor = AIProcessor(
            config=config,
            cache_manager=cache_manager
        )
        
        report_generator = ReportGenerator(
            output_dir="output"
        )
        
        # Load all feeds
        feeds = feed_manager.load_feeds()
        logger.info(f"Loaded {len(feeds)} feeds from OPML")
        
        # Prefetch all feeds from the specified date range
        if not args.skip_prefetch:
            logger.info(f"Prefetching feeds from the last {args.days} days")
            prefetch_date = datetime.datetime.now().date() - datetime.timedelta(days=args.days)
            
            # Initialize a counter for prefetched entries
            prefetched_entries = 0
            
            # Prefetch and cache all feeds
            for feed in feeds:
                try:
                    feed_entries = feed_manager.get_feed_entries(feed, since_date=prefetch_date)
                    logger.info(f"Prefetched {len(feed_entries)} entries from '{feed['title']}'")
                    prefetched_entries += len(feed_entries)
                    
                    # Process and cache the content for each entry
                    for entry in feed_entries:
                        # Add feed URL to entry for cache operations
                        entry['feed_url'] = feed['url']
                        entry['feed_title'] = feed['title']
                        
                        # Only process entries that fall within the date range
                        entry_date = entry.get('parsed_date')
                        if entry_date and entry_date.date() >= prefetch_date:
                            # Extract and cache full content
                            content_processor.process_entry(entry)
                        else:
                            logger.debug(f"Skipping entry outside date range: {entry.get('title', 'Unknown')}")
                except Exception as e:
                    logger.error(f"Error prefetching feed '{feed['title']}': {e}")
            
            logger.info(f"Completed prefetching {prefetched_entries} entries from all feeds")
        
        # Process date range for the digest
        today = datetime.datetime.now().date()
        start_date = today - datetime.timedelta(days=args.days)
        logger.info(f"Processing entries from {start_date} to {today}")
        
        # Process each feed and its entries for the specified date range
        all_processed_entries = []
        for feed in feeds:
            feed_entries = feed_manager.get_feed_entries(feed, since_date=start_date)
            logger.info(f"Processing {len(feed_entries)} entries from '{feed['title']}'")
            
            for entry in feed_entries:
                # Add feed URL to entry for cache operations
                entry['feed_url'] = feed['url']
                entry['feed_title'] = feed['title']
                
                # Ensure the entry is within the date range
                entry_date = entry.get('parsed_date')
                if entry_date and entry_date.date() >= start_date:
                    # Extract full content (should already be cached from prefetch)
                    entry_content = content_processor.process_entry(entry)
                    
                    # Generate cache keys for summary check
                    feed_id = cache_manager.generate_feed_id(feed['url'], feed['title'])
                    entry_id = CacheManager.create_entry_cache_key(entry)
                    # Generate AI summary if needed
                    if not cache_manager.has_entry_summary(feed_id, entry_id):
                        logger.info(f"No cached summary found, generating for: {entry.get('title', 'Unknown')}")
                        ai_processor.summarize_entry(entry, feed_id, feed['title'])
                    else:
                        logger.info(f"Using cached summary for: {entry.get('title', 'Unknown')}")
                    
                    # Add to processed entries list
                    all_processed_entries.append(entry)
                else:
                    logger.debug(f"Skipping entry outside date range: {entry.get('title', 'Unknown')}")
        
        # Generate daily digest
        report_date = today.strftime("%Y%m%d")
        logger.info(f"Generating digest for {report_date}")
        
        digest = ai_processor.generate_digest(report_date, all_processed_entries)
        report_generator.create_daily_report(digest, report_date)
        report_generator.update_index()
        
        logger.info("RSSky processing completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Error during processing: {e}", exc_info=True)
        return 3


if __name__ == "__main__":
    sys.exit(main()) 