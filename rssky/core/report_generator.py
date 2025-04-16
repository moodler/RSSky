"""
Report Generator module for RSSky

This module handles the generation of HTML reports from digest data,
and manages the report index. It creates daily HTML files and maintains
an index.html file linking to all reports.
"""

import os
import logging
import datetime
from pathlib import Path
import json

logger = logging.getLogger("rssky.report")

class ReportGenerator:
    """Generates HTML reports from digest data"""
    
    def __init__(self, output_dir="output"):
        """Initialize with output directory"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def create_daily_report(self, digest, date_str, prompt=None, response=None):
        """Create a daily HTML report from digest data. Optionally saves prompt/response in debug dir."""
        report_path = self.output_dir / f"{date_str}.html"
        if prompt is not None:
            prompt_file = Path("debug") / f"report_prompt_{date_str}.txt"
            try:
                prompt_file.write_text(str(prompt), encoding="utf-8")
            except Exception:
                pass
        if response is not None:
            response_file = Path("debug") / f"report_response_{date_str}.json"
            import json as _json
            try:
                response_file.write_text(_json.dumps(response, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                response_file.write_text(str(response), encoding="utf-8")
        # Create HTML content
        html_content = self._generate_html_report(digest, date_str)
        # Write to file
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"Generated report: {report_path}")
        return report_path
    
    def update_index(self):
        """Update the index.html file linking to all reports"""
        index_path = self.output_dir / "index.html"
        
        # Find all report files
        report_files = sorted(self.output_dir.glob("*.html"), reverse=True)
        reports = []
        
        for file_path in report_files:
            if file_path.name != "index.html":
                # Parse date from filename
                date_str = file_path.stem
                if len(date_str) == 8:  # YYYYMMDD format
                    try:
                        year = int(date_str[:4])
                        month = int(date_str[4:6])
                        day = int(date_str[6:8])
                        date_obj = datetime.date(year, month, day)
                        formatted_date = date_obj.strftime("%B %d, %Y")
                        
                        reports.append({
                            "filename": file_path.name,
                            "date_str": date_str,
                            "formatted_date": formatted_date
                        })
                    except ValueError:
                        # Skip files with invalid date format
                        continue
        
        # Generate index HTML
        html_content = self._generate_index_html(reports)
        
        # Write to file
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Updated index: {index_path}")
        return index_path
    
    def _generate_html_report(self, digest, date_str):
        """Generate HTML content for a daily report"""
        # Parse date
        try:
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            date_obj = datetime.date(year, month, day)
            formatted_date = date_obj.strftime("%B %d, %Y")
        except ValueError:
            formatted_date = date_str
        
        # Get the stories list (new format)
        stories = digest.get('stories', [])
        # Fallback for legacy format
        if not stories:
            stories = digest.get('high_impact', []) + digest.get('significant', [])
            # Sort by importance_rating or importance, descending
            def get_importance(story):
                return story.get('importance_rating', story.get('importance', 0))
            stories.sort(key=get_importance, reverse=True)
        
        # Always sort stories by importance (descending) before generating HTML
        if stories:
            def get_importance(story):
                return story.get('importance_rating', story.get('importance', 0))
            stories.sort(key=get_importance, reverse=True)
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>RSSky Digest - {formatted_date}</title>
        <style>
            :root {{
                --primary: #1e3a8a;
                --secondary: #5b21b6;
                --background: #f9fafb;
                --text: #111827;
                --card-bg: #fff;
                --card-border: #e5e7eb;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif;
                background-color: var(--background);
                color: var(--text);
                margin: 0;
                padding: 20px;
            }}
            main {{
                max-width: 1000px;
                margin: 0 auto;
                padding: 20px;
            }}
            header {{
                margin-bottom: 30px;
            }}
            h1 {{
                color: var(--primary);
                margin-bottom: 5px;
            }}
            h2 {{
                color: var(--secondary);
                border-bottom: 2px solid var(--secondary);
                padding-bottom: 10px;
                margin-top: 30px;
            }}
            .date {{
                font-size: 1.2em;
                color: var(--secondary);
                margin-bottom: 10px;
            }}
            .story-card {{
                background-color: var(--card-bg);
                border: 1px solid var(--card-border);
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(30,58,138,0.03);
                padding: 24px 28px;
                margin-bottom: 30px;
                transition: box-shadow 0.2s;
            }}
            .story-card:hover {{
                box-shadow: 0 4px 16px rgba(30,58,138,0.08);
            }}
            .story-meta {{
                display: flex;
                flex-wrap: wrap;
                gap: 18px;
                align-items: center;
                margin-bottom: 12px;
            }}
            .importance {{
                color: #fff;
                background: linear-gradient(90deg, var(--primary), var(--secondary));
                border-radius: 4px;
                padding: 4px 12px;
                font-weight: bold;
                font-size: 1em;
                margin-right: 12px;
            }}
            .sources h4 {{
                margin-top: 0;
                margin-bottom: 10px;
            }}
            .source-list {{
                list-style-type: none;
                padding: 0;
                margin: 0;
            }}
            .source-list li {{
                margin-bottom: 8px;
            }}
            .source-list a {{
                color: var(--secondary);
                text-decoration: none;
            }}
            .source-list a:hover {{
                text-decoration: underline;
            }}
            .no-stories {{
                background-color: var(--card-bg);
                border-radius: 8px;
                padding: 20px;
                text-align: center;
                color: #666;
            }}
            footer {{
                margin-top: 50px;
                text-align: center;
                font-size: 0.9em;
                color: #666;
                border-top: 1px solid var(--card-border);
                padding-top: 20px;
            }}
            a {{
                color: var(--secondary);
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            @media (max-width: 768px) {{
                body {{
                    padding: 15px;
                }}
                .story-meta {{
                    flex-direction: column;
                }}
            }}
        </style>
        </head>
        <body>
        <header>
            <h1>RSSky Digest</h1>
            <div class="date">{formatted_date}</div>
            <a href="index.html">← Back to Index</a>
        </header>
        <main>
        <section>
            <h2>Stories</h2>
        """
        if stories:
            for story in stories:
                html += self._generate_story_card(story)
        else:
            html += """
            <div class="no-stories">
                <p>No stories for today.</p>
            </div>
            """
        html += """
        </section>
        </main>
        <footer>
            <p>Generated by RSSky on """ + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
        </footer>
        </body>
        </html>"""
        return html
    
    def _generate_story_card(self, story):
        """Generate HTML for a story card"""
        title = story.get('title', 'Untitled')
        url = story.get('url', '#')
        feed = story.get('feed', 'Unknown Source')
        date = story.get('date', '')
        
        # Get importance from either importance or importance_rating
        importance = story.get('importance')
        if importance is None:
            importance = story.get('importance_rating', 0)
        if isinstance(importance, str):
            try:
                importance = float(importance)
            except (ValueError, TypeError):
                importance = 5  # Default if we can't convert
        
        # Format importance as integer for display
        importance_display = int(importance)
        
        # Get summary text
        summary_text = story.get('summary', 'No summary available')
        
        # Get impact if available
        impact = story.get('impact', '')
        
        # Combine summary and impact if both exist
        full_summary = summary_text
        if impact and impact != 'No impact assessment available':
            full_summary += f"<p><strong>Impact:</strong> {impact}</p>"
        
        # Check if we have the old format with sources
        sources = story.get('sources', [])
        
        # Remove 'Source: Unknown Source' if sources are present, and only show Source if not redundant
        show_source = not sources and feed and feed != 'Unknown Source'
        html = f"""
            <div class="story-card">
                <h2 class="story-title">{title}</h2>
                <div class="story-meta" style="justify-content: space-between;">
        """
        if show_source:
            html += f"<div>Source: {feed}</div>"
        html += f"<div class=\"importance\" style=\"margin-left:auto;\">Importance: {importance_display}/10</div>"
        html += f"""
                </div>
                <div class="summary">
                    {full_summary}
                </div>
        """
        # Add sources section if we have sources
        if sources:
            html += """
                <div class="sources">
                    <h4>Sources:</h4>
                    <ul class="source-list">
            """
            
            for source in sources:
                name = source.get('name', 'Unknown')
                src_title = source.get('title', 'Untitled')
                src_url = source.get('url', '#')
                
                html += f"""
                        <li><strong>{name}</strong>: <a href="{src_url}" target="_blank">{src_title}</a></li>
                """
            
            html += """
                    </ul>
                </div>
            """
        
        html += """
            </div>
        """
        
        return html
    
    def _generate_index_html(self, reports):
        """Generate HTML for the index page"""
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RSSky Digest Index</title>
    <style>
        :root {
            --primary: #1e3a8a;
            --secondary: #5b21b6;
            --background: #f9fafb;
            --text: #111827;
            --card-bg: #fff;
            --card-border: #e5e7eb;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif;
            line-height: 1.6;
            color: var(--text);
            background-color: var(--background);
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            margin-bottom: 40px;
            text-align: center;
        }
        
        h1 {
            color: var(--primary);
            margin-bottom: 10px;
        }
        
        .description {
            font-size: 1.1em;
            color: #666;
        }
        
        .reports-list {
            list-style-type: none;
            padding: 0;
        }
        
        .report-card {
            background-color: var(--card-bg);
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            margin-bottom: 15px;
            padding: 15px 20px;
            border: 1px solid var(--card-border);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .report-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }
        
        .report-card a {
            color: var(--secondary);
            text-decoration: none;
            font-size: 1.2em;
            font-weight: 500;
            display: block;
        }
        
        .report-card a:hover {
            text-decoration: underline;
        }
        
        .no-reports {
            background-color: var(--card-bg);
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            color: #666;
        }
        
        footer {
            margin-top: 50px;
            text-align: center;
            font-size: 0.9em;
            color: #666;
            border-top: 1px solid var(--card-border);
            padding-top: 20px;
        }
    </style>
</head>
<body>
    <header>
        <h1>RSSky Digest Index</h1>
        <div class="description">Archive of all RSSky daily news digests</div>
    </header>
    
    <main>
"""
        
        if reports:
            html += """
        <ul class="reports-list">
"""
            
            for report in reports:
                filename = report["filename"]
                formatted_date = report["formatted_date"]
                
                html += f"""
            <li class="report-card">
                <a href="{filename}">{formatted_date}</a>
            </li>
"""
            
            html += """
        </ul>
"""
        else:
            html += """
        <div class="no-reports">
            <p>No reports available yet.</p>
        </div>
"""
        
        html += """
    </main>
    
    <footer>
        <p>Generated by RSSky on """ + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
    </footer>
</body>
</html>"""
        
        return html 