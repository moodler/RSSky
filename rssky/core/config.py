"""
Configuration module for RSSky

This module handles loading configuration from the config.ini file,
validating required settings, and providing access to configuration values.
"""

import os
import configparser
import logging

logger = logging.getLogger("rssky.config")

class Config:
    """Configuration manager for RSSky"""
    
    DEFAULT_CONFIG = {
        "API": {
            "api_url": "https://api.openai.com/v1/chat/completions",
            "api_key": "",
            "model": "gpt-4",
            "temperature": "0.7",
            "max_tokens": "1000"
        },
        "Settings": {
            "importance_criteria": "Focus on technological breakthroughs, scientific discoveries, major political events, and significant market movements."
        },
        "PROMPTS": {
            "summary_prompt": """
            You are an expert news analyst. Analyze the following article and provide:
            1. A 0-10 importance rating (where 10 is extremely important globally)
            2. A max 2000-word summary with one paragraph for each of the news stories in this text
            3. A brief assessment of potential impact
            4. The date of the article  
            Base the importance rating on the following user-provided criteria:
            {importance_criteria}

            
            Article:
            {article_content}
            """,
            
            "report_prompt": """
            You are an expert news analyst. Below you will find a JSON structure of news article summaries, with importance ratings. Many of these articles may actually be about the same story.  Some articles contain multiple news stories.
            Your job is to group news stories together (treating them as a single story with multiple sources). News stories with multiple sources should be seen as more important than those with a single source.  Don't clump things together in broad subjects, such as AI, that's too broad.  We're focussed on individual NEWS stories.   For each news story, provide:
            
            1. Your own concise title
            2. The importance rating (derived from the source article importance ratings and your judgement on the overall importance criteria below)
            3. A comprehensive summary (300-500 words)
            4. Date (use the most recent date from sources)
            5. A list of ALL multiple related news article sources from the input list (including name, title, and URL)
            
            Use the following criteria to evaluate importance between:
            {importance_criteria}
            Sort all the final news stories by importance rating, highest first.
            
            """,
        }
    }
    
    def __init__(self, config_path="config.ini"):
        """Initialize configuration from file"""
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        
        # Load config file if it exists, otherwise use defaults
        if os.path.exists(config_path):
            self.config.read(config_path)
            logger.info(f"Loaded configuration from {config_path}")
        else:
            # Create default config
            self._set_defaults()
            self._save_config()
            logger.info(f"Created default configuration at {config_path}")
        
        # Validate configuration
        self._validate_config()
    
    def _set_defaults(self):
        """Set default configuration values"""
        for section, options in self.DEFAULT_CONFIG.items():
            if not self.config.has_section(section):
                self.config.add_section(section)
            
            for option, value in options.items():
                if not self.config.has_option(section, option):
                    self.config.set(section, option, value)
    
    def _save_config(self):
        """Save configuration to file"""
        with open(self.config_path, 'w') as f:
            self.config.write(f)
    
    def _validate_config(self):
        """Validate required configuration settings"""
        # Check API key is set
        if not self.get('API', 'api_key'):
            logger.warning("API key is not set in configuration")
        
        # Validate other critical settings
        required_sections = ['API', 'Settings', 'PROMPTS']
        for section in required_sections:
            if not self.config.has_section(section):
                logger.error(f"Missing required section '{section}' in configuration")
                raise ValueError(f"Missing required section '{section}' in configuration")
    
    def get(self, section, option, fallback=None):
        """Get configuration value"""
        return self.config.get(section, option, fallback=fallback)
    
    def getint(self, section, option, fallback=None):
        """Get configuration value as integer"""
        return self.config.getint(section, option, fallback=fallback)
    
    def getfloat(self, section, option, fallback=None):
        """Get configuration value as float"""
        return self.config.getfloat(section, option, fallback=fallback)
    
    def getboolean(self, section, option, fallback=None):
        """Get configuration value as boolean"""
        return self.config.getboolean(section, option, fallback=fallback)
    
    def get_api_config(self):
        """Get API configuration as dictionary"""
        return {
            'api_url': self.get('API', 'api_url'),
            'api_key': self.get('API', 'api_key'),
            'model': self.get('API', 'model'),
            'temperature': self.getfloat('API', 'temperature', 0.7),
            'max_tokens': self.getint('API', 'max_tokens', 1000)
        }
    
    def get_importance_criteria(self):
        """Get user-defined importance criteria"""
        return self.get('Settings', 'importance_criteria', 
                        self.DEFAULT_CONFIG['Settings']['importance_criteria'])
    
    def get_summary_prompt(self):
        """Get the summary prompt template with importance criteria filled in"""
        prompt = self.get('PROMPTS', 'summary_prompt', 
                          self.DEFAULT_CONFIG['PROMPTS']['summary_prompt'])
        
        # Only replace the {importance_criteria} placeholder
        # Use a temporary placeholder to avoid conflicts with JSON formatting
        prompt = prompt.replace("{importance_criteria}", "###IMPORTANCE_CRITERIA###")
        
        # Now replace the temporary placeholder with the actual criteria
        return prompt.replace("###IMPORTANCE_CRITERIA###", self.get_importance_criteria())
    
    def get_report_prompt(self):
        """Get the report prompt template with importance criteria filled in"""
        prompt = self.get('PROMPTS', 'report_prompt', 
                         self.DEFAULT_CONFIG['PROMPTS']['report_prompt'])
        
        # Only replace the {importance_criteria} placeholder
        # Use a temporary placeholder to avoid conflicts with JSON formatting
        prompt = prompt.replace("{importance_criteria}", "###IMPORTANCE_CRITERIA###")
        
        # Now replace the temporary placeholder with the actual criteria
        return prompt.replace("###IMPORTANCE_CRITERIA###", self.get_importance_criteria()) 