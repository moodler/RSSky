"""
AI Processor module for RSSky

This module handles the AI processing of article content, generating summaries
and importance ratings for individual articles, and creating the daily digest.
"""

import json
import logging
import requests
import datetime
from datetime import datetime
import traceback
from pathlib import Path
import os
from dateutil import parser
import re
import demjson3

from rssky.utils.helpers import format_date
from rssky.core.cache_manager import CacheManager

logger = logging.getLogger("rssky.ai")

class AIProcessor:
    """Handles AI processing for RSSky"""
    
    def __init__(self, config, cache_manager):
        """Initialize with configuration and cache manager"""
        self.config = config
        self.cache_manager = cache_manager
        self.api_config = config.get_api_config()
    
    def get_entry_content(self, entry, feed_id, entry_id):
        """Helper method to get content using consistent IDs"""
        # feed_id and entry_id are now generated *before* calling this
        if not feed_id or not entry_id:
             logger.error(f"Missing feed_id or entry_id during get_entry_content for {entry.get('title')}")
             return None
        # Assume ContentProcessor has already run and cached the content
        content = self.cache_manager.get_cached_content(feed_id, entry_id)
        if not content:
             logger.warning(f"Content not found in cache for {feed_id}/{entry_id}. ContentProcessor might have failed.")
        return content
    
    def summarize_entry(self, entry, feed_id, feed_title, force=False):
        """Generate an AI summary for a feed entry, with retry logic on parse failure"""
        entry_title = entry.get('title', 'Unknown') # Keep for logging
        try:
            entry_id = CacheManager.create_entry_cache_key(entry)
        except Exception as e:
            logger.error(f"Failed to create entry cache key for '{entry_title}': {e}", exc_info=True)
            return self._generate_fallback_summary(entry)
        content = self.get_entry_content(entry, feed_id, entry_id)
        if not content:
            logger.warning(f"Content missing for {feed_id}/{entry_id}, generating fallback summary.")
            fallback_summary = self._generate_fallback_summary(entry)
            try:
                self.cache_manager.cache_summary(feed_id, entry_id, fallback_summary)
            except Exception as cache_err:
                logger.error(f"Failed to cache fallback summary for {feed_id}/{entry_id}: {cache_err}")
            return fallback_summary
        if not force:
            cached_summary = self.cache_manager.get_entry_summary(feed_id, entry_id)
            if cached_summary:
                logger.info(f"Using cached summary for: {feed_id}/{entry_id} ('{entry_title}')")
                return cached_summary
        logger.info(f"No cached summary found, generating for: {feed_id}/{entry_id} ('{entry_title}')")
        prompt = self.config.get_summary_prompt()
        # Add strict instruction to avoid comments and explanations
        prompt = (
            prompt.strip() +
            "\n\nRespond ONLY with a valid JSON object, and do not include comments or explanations."
        )
        if isinstance(content, list):
            content = "\n".join([str(item) for item in content if item])
        # --- Ensure title and date are included in the prompt above the full text ---
        item_title = entry.get('title', 'Unknown')
        item_date = entry.get('published', entry.get('date', ''))
        if not item_date:
            item_date = datetime.now().strftime('%Y-%m-%d')
        # Prepend title and date to the content
        content_header = f"Title: {item_title}\nDate: {item_date}\n\n"
        full_content = content_header + content
        debug_dir = Path("debug")
        if not debug_dir.exists():
            os.makedirs(debug_dir)
        entry_name = entry_title[:30].replace(" ", "_").replace("/", "_").replace(":", "_")
        full_content_file = debug_dir / f"full_content_{entry_name}.txt"
        full_content_file.write_text(full_content, encoding="utf-8")
        ai_content = full_content
        if len(full_content) > 20000:
            logger.info(f"Truncating content from {len(full_content)} to 20000 characters for AI processing")
            ai_content = full_content[:20000] + "... [content truncated]"
        article_prompt = prompt.replace("{article_content}", ai_content)
        summary_prompt_file = debug_dir / f"prompt_{entry_name}.txt"
        summary_prompt_file.write_text(article_prompt, encoding="utf-8")
        # --- Retry logic for AI call and JSON extraction ---
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                # logger.info(f"Making AI request for: {entry_title} (attempt {attempt})")
                raw_response, parsed_response = self._make_ai_request(article_prompt, entry_title, use_summary_schema=True)
                # --- INSTRUMENTATION: Log and save the raw_response at the earliest point ---
                debug_dir = Path("debug")
                debug_dir.mkdir(exist_ok=True)
                raw_file = debug_dir / f"raw_ai_response_{entry_name}_attempt{attempt}.txt"
                try:
                    raw_file.write_text(str(raw_response), encoding="utf-8")
                except Exception:
                    pass
                logger.debug(f"[DEBUG] Length of raw_response: {len(str(raw_response)) if raw_response else 0}")
                # logger.debug(f"[DEBUG] Start of raw_response: {str(raw_response)[:500] if raw_response else ''}")
                logger.debug(f"[DEBUG] End of raw_response: {str(raw_response)[-500:] if raw_response else ''}")
                if parsed_response:
                    # Check if we got a fallback/error summary (by summary text)
                    summary_text = parsed_response.get("summary", "")
                    if "could not be extracted" in summary_text or "parsing error" in summary_text or "API request failed" in summary_text:
                        logger.warning(f"AI returned fallback/error summary on attempt {attempt}: {summary_text}")
                        logger.debug(f"Raw AI response on failure: {raw_response}")
                        if attempt == max_attempts:
                            logger.error(f"All {max_attempts} attempts failed for {entry_title}. Returning fallback.")
                            self.cache_manager.cache_summary(feed_id, entry_id, parsed_response)
                            return parsed_response
                        else:
                            continue  # Retry
                    # Success: valid summary
                    # logger.info(f"AI response for {entry_title}: {parsed_response}")
                    response_file = debug_dir / f"response_{entry_name}.json"
                    response_file.write_text(json.dumps(parsed_response, indent=2), encoding="utf-8")
                    parsed_response['url'] = entry.get('link', '')
                    parsed_response['title'] = entry.get('title', '')
                    parsed_response['full_content_available'] = True
                    self.cache_manager.cache_summary(feed_id, entry_id, parsed_response)
                    return parsed_response
                else:
                    logger.warning(f"AI request returned no data for entry: {entry_title} (attempt {attempt})")
                    if attempt == max_attempts:
                        fallback_summary = self._generate_fallback_summary(entry)
                        self.cache_manager.cache_summary(feed_id, entry_id, fallback_summary)
                        return fallback_summary
            except Exception as e:
                logger.error(f"Error during AI summary extraction (attempt {attempt}): {e}", exc_info=True)
                if attempt == max_attempts:
                    fallback_summary = self._generate_fallback_summary(entry)
                    self.cache_manager.cache_summary(feed_id, entry_id, fallback_summary)
                    return fallback_summary
        # Defensive fallback
        fallback_summary = self._generate_fallback_summary(entry)
        self.cache_manager.cache_summary(feed_id, entry_id, fallback_summary)
        return fallback_summary
    
    def generate_digest(self, date_str, entries):
        """Generate a daily digest of the most important entries."""
        logger.info(f"Generating digest with {len(entries)} entries")
        
        entries_with_summaries = []
        
        for entry in entries:
            feed_title = entry.get('feed_title', '')
            feed_id = entry.get('feed_id', '')
            # --- FIX: Always use the same cache key logic as summary generation ---
            try:
                entry_id = CacheManager.create_entry_cache_key(entry)
            except Exception as e:
                logger.error(f"Failed to create entry cache key for digest: {entry.get('title', 'Unknown')} ({feed_id}): {e}")
                continue
            logger.debug(f"Processing entry for digest: {entry.get('title', 'Unknown')} from {feed_title}")
            # Get cached summary using feed_id and entry_id
            summary = self.cache_manager.get_entry_summary(feed_id, entry_id)
            
            if summary:
                logger.debug(f"Found cached summary with importance: {summary.get('importance', 'Unknown')}")
                
                # Ensure importance is a number
                importance = summary.get('importance', 0)
                if isinstance(importance, str):
                    try:
                        importance = float(importance)
                    except (ValueError, TypeError):
                        importance = 5  # Default if we can't convert
                
                # Include summaries with importance >= 5 or fallback/error summaries
                if importance >= 5 or "API request failed" in summary.get('summary', '') or "could not be extracted" in summary.get('summary', ''):
                    logger.info(f"Adding entry to digest: {entry.get('title', 'Unknown')} with importance {importance}")
                    
                    # Ensure all required fields are present
                    if 'title' not in summary:
                        summary['title'] = entry.get('title', '')
                    if 'date' not in summary:
                        summary['date'] = entry.get('published', '')
                    if 'url' not in summary:
                        summary['url'] = entry.get('link', '')
                    if 'feed' not in summary:
                        summary['feed'] = feed_title
                        
                    entries_with_summaries.append({
                        'title': entry.get('title', ''),
                        'summary': summary,
                        'date': entry.get('published', ''),
                        'url': entry.get('link', ''),
                        'feed': feed_title
                    })
                else:
                    logger.debug(f"Skipping entry with low importance: {entry.get('title', 'Unknown')} - {importance}")
            else:
                logger.debug(f"No cached summary found for: {entry.get('title', 'Unknown')}")
        
        logger.info(f"Found {len(entries_with_summaries)} significant entries for digest")
        
        if not entries_with_summaries:
            logger.warning("No significant entries found for digest")
            return {"high_impact": [], "significant": []}
        
        # Insert summary.json content directly, no wrapping or transformation
        summaries_json = json.dumps(entries_with_summaries, indent=2, ensure_ascii=False)
        
        # Get the report prompt template
        digest_prompt = self.config.get_report_prompt()
        
        # Replace placeholders
        if "{summaries_json}" in digest_prompt:
            digest_prompt = digest_prompt.replace("{summaries_json}", "###SUMMARIES_JSON###")
            digest_prompt = digest_prompt.replace("###SUMMARIES_JSON###", summaries_json)
        else:
            # Fallback for older templates
            digest_prompt = f"{digest_prompt}\n\nHere are the summaries (each is a direct JSON object from summary.json):\n{summaries_json}"
        
        # Save the report prompt and response to debug dir for inspection
        debug_dir = Path("debug")
        debug_dir.mkdir(exist_ok=True)
        report_prompt_file = debug_dir / f"report_prompt_{date_str}.txt"
        report_prompt_file.write_text(digest_prompt, encoding="utf-8")
        report_response_file = debug_dir / f"report_response_{date_str}.json"
        # (response will be written after AI call)
        
        # Determine if using OpenAI model (skip schema injection)
        api_conf = self.api_config
        model = api_conf['model'].strip()
        # Determine if using OpenAI model (which doesn't support response_format param)
        is_openai = model.lower().startswith("gpt")
        temperature = float(self.api_config['temperature'])
        max_tokens = int(self.api_config['max_tokens'])
        
        # Prepare the request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_conf['api_key']}"
        }
        
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": digest_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Inject response_format for Gemini/Google models only
        schema_flag = not is_openai
        
        # Make the AI request with retry logic
        max_retries = 3
        retry_delay = 3  # seconds
        attempt = 0
        while attempt < max_retries:
            try:
                raw_response, parsed_response = self._make_ai_request(digest_prompt, use_report_schema=schema_flag)
                # Map 'news' key to 'stories' if API returned it
                if parsed_response and isinstance(parsed_response, dict):
                    if "news" in parsed_response:
                        logger.warning("API response used 'news' key; mapping to 'stories'")
                        parsed_response["stories"] = parsed_response.pop("news")
                    elif "newsStories" in parsed_response:
                        logger.warning("API response used 'newsStories' key; mapping to 'stories'")
                        parsed_response["stories"] = parsed_response.pop("newsStories")
                # Always write the raw AI response to the debug file BEFORE any validation logic
                try:
                    report_response_file.write_text(str(raw_response), encoding="utf-8")
                except Exception:
                    pass
                # Accept only valid AI output (must be a dict with 'stories' key)
                if parsed_response and isinstance(parsed_response, dict) and "stories" in parsed_response:
                    return parsed_response
                else:
                    logger.warning(f"Attempt {attempt+1}: Invalid AI response for digest (missing 'stories'). Retrying...")
            except Exception as e:
                logger.error(f"Attempt {attempt+1}: Exception during AI request for digest: {e}")
                logger.error(f"Exception details: {traceback.format_exc()}")
                try:
                    report_response_file.write_text(f"AI request failed: {str(e)}\n{traceback.format_exc()}", encoding="utf-8")
                except Exception:
                    pass
            attempt += 1
            if attempt < max_retries:
                import time
                time.sleep(retry_delay)
        # If all retries fail, log critical error and abort
        logger.critical("All attempts to generate digest via AI failed. Aborting digest generation.")
        raise RuntimeError("Failed to generate digest via AI after multiple attempts.")
    
    def _make_ai_request(self, prompt, entry_title=None, use_report_schema=False, use_summary_schema=False):
        """Make an API request to the AI service"""
        try:
            # Get API configuration
            api_url = self.api_config['api_url']
            
            # Ensure API URL ends with /v1/chat/completions for LiteLLM compatibility
            if not api_url.endswith('/v1/chat/completions'):
                if api_url.endswith('/'):
                    api_url = api_url + 'v1/chat/completions'
                else:
                    api_url = api_url + '/v1/chat/completions'
                    
            api_key = self.api_config['api_key']
            model = self.api_config['model'].strip()
            # Determine if using OpenAI model (which doesn't support response_format param)
            is_openai = model.lower().startswith("gpt")
            temperature = float(self.api_config['temperature'])
            max_tokens = int(self.api_config['max_tokens'])
            
            # Prepare the request
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that only responds with valid, unformatted JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            # Inject response_format for Gemini/Google models only
            if use_report_schema and not is_openai:
                response_format = {
                    "type": "object",
                    "properties": {
                        "stories": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "importance_rating": {"type": "number"},
                                    "summary": {"type": "string"},
                                    "date": {"type": "string"},
                                    "sources": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "name": {"type": "string"},
                                                "title": {"type": "string"},
                                                "url": {"type": "string"}
                                            },
                                            "required": ["name", "title", "url"]
                                        }
                                    }
                                },
                                "required": ["title", "importance_rating", "summary", "date", "sources"]
                            }
                        }
                    },
                    "required": ["stories"]
                }
                # Try Gemini/Google-style schema param, fallback to OpenAI function calling if needed
                data["response_format"] = response_format
            
            # Inject response_format for summary calls
            if use_summary_schema and not is_openai:
                summary_format = {
                    "type": "object",
                    "properties": {
                        "importance": {"type": "number"},
                        "summary": {"type": "string"},
                        "impact": {"type": "string"},
                        "date": {"type": "string"}
                    },
                    "required": ["importance", "summary", "impact", "date"]
                }
                data["response_format"] = summary_format
            
            # Make the request
            logger.info(f"Making API request to {api_url} with model {model}")
            response = requests.post(api_url, headers=headers, json=data)
            
            # Check if the request was successful
            if response.status_code == 200:
                result = response.json()
                
                # Extract the content from the response
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                else:
                    logger.error("No choices or message content in response")
                    return (None, None)
                
                # Save raw content for debugging
                debug_dir = Path("debug")
                if not debug_dir.exists():
                    os.makedirs(debug_dir)
                raw_response_file = debug_dir / "raw_content.txt"
                raw_response_file.write_text(content, encoding="utf-8")
                
                # Log the raw content
                # logger.info(f"Raw content from API: {content[:100]}...")
                
                # Extract JSON from content
                json_str = self._extract_json_from_string(content, entry_title, prompt)
                
                if not json_str:
                    logger.error(f"Could not extract JSON from API response. Raw content was: {content}")
                    return (content, None)
                
                # Save extracted JSON for debugging
                json_file = debug_dir / f"extracted_json_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
                json_file.write_text(json_str, encoding="utf-8")
                
                # Try to parse the JSON
                try:
                    parsed_result = json.loads(json_str)
                    logger.info(f"Successfully parsed JSON with keys: {list(parsed_result.keys())}")
                    return (content, parsed_result)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON: {str(e)}")
                    return (content, None)
            else:
                # Log the full error message and response text
                logger.error(f"API request failed with status code {response.status_code}")
                return (f"API request failed with status code {response.status_code}: {response.text}", None)
        except Exception as e:
            logger.error(f"Exception during API request: {e}")
            logger.error(traceback.format_exc())
            return (f"Exception during API request: {e}\n{traceback.format_exc()}", None)
    
    def _extract_json_from_string(self, s, entry_title=None, prompt=None):
        """Extract JSON from a string that may contain <think> tags, markdown code blocks, or plain JSON, and strip comments and invalid control characters. Save failed extractions."""
        import re
        s = s.strip()
        
        # Find the start of the JSON object
        start_brace = s.find('{')
        if start_brace == -1:
            logger.error("Could not find starting brace '{' in AI response.")
            return ""
            
        # Find the end of the JSON object
        end_brace = s.rfind('}')
        if end_brace == -1:
            logger.error("Could not find ending brace '}' in AI response.")
            return ""
            
        json_str = s[start_brace:end_brace+1]
        
        # Use demjson3 for robust parsing
        try:
            cleaned_obj = demjson3.decode(json_str)
            # Re-encode to ensure it's a clean JSON string
            json_str = demjson3.encode(cleaned_obj)
            logger.debug(f"[DEBUG] demjson3 sanitized JSON string for parsing: {repr(json_str[:1000])}")
        except Exception as e:
            logger.error(f"[DEBUG] demjson3 failed to decode extracted JSON: {e}")
            return ""
            
        return json_str
    
    def _generate_fallback_summary(self, entry):
        """Generate a fallback summary when AI processing fails"""
        logger.info("Generating fallback summary")
        
        # Get entry title based on type
        entry_title = entry.get('title', 'Unknown') # Keep for logging

        # Get entry date based on type
        if isinstance(entry, dict):
            entry_date = entry.get('published', None) or entry.get('updated', None)
        else:
            entry_date = getattr(entry, 'published', None) or getattr(entry, 'updated', None)
            
        # Format date as YYYY-MM-DD
        if entry_date:
            try:
                if isinstance(entry_date, str):
                    # Parse string date
                    date_obj = parser.parse(entry_date)
                    formatted_date = date_obj.strftime("%Y-%m-%d")
                else:
                    # Already a datetime object
                    formatted_date = entry_date.strftime("%Y-%m-%d")
            except Exception as e:
                logger.error(f"Error formatting date: {e}")
                formatted_date = datetime.now().strftime("%Y-%m-%d")
        else:
            formatted_date = datetime.now().strftime("%Y-%m-%d")
        
        return {
            "importance": 5,
            "summary": f"Summary could not be extracted for: {entry_title}",
            "impact": "Impact could not be determined due to processing error.",
            "date": formatted_date
        }