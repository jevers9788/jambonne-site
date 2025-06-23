import requests
from bs4 import BeautifulSoup
import time
import re
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
from ..models import ReadingListEntry, ScrapingOptions


class WebScraper:
    """Service for scraping web content from URLs"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        # Remove common web artifacts
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]]', '', text)
        return text
    
    def extract_text_from_url(self, url: str, options: ScrapingOptions) -> Optional[str]:
        """Extract main text content from a URL."""
        try:
            response = self.session.get(str(url), timeout=options.timeout)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.decompose()
            
            # Try to find main content areas
            main_content = None
            
            # Look for common content selectors
            selectors = [
                'main', 'article', '.content', '.post-content', '.entry-content',
                '#content', '#main', '.main-content', '[role="main"]'
            ]
            
            for selector in selectors:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            # If no main content found, use body
            if not main_content:
                main_content = soup.body or soup
            
            # Extract text
            text = main_content.get_text()
            cleaned_text = self.clean_text(text)
            
            # Truncate if too long
            if len(cleaned_text) > options.max_content_length:
                cleaned_text = cleaned_text[:options.max_content_length] + "..."
            
            return cleaned_text
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None
    
    async def scrape_entries(self, entries: List[ReadingListEntry], options: ScrapingOptions) -> List[ReadingListEntry]:
        """Scrape content from a list of reading list entries."""
        scraped_entries = []
        
        for i, entry in enumerate(entries):
            print(f"Scraping {i+1}/{len(entries)}: {entry.title}")
            
            # Extract text content
            content = self.extract_text_from_url(entry.url, options)
            
            if content:
                entry.content = content
                entry.content_length = len(content)
                print(f"  ✓ Extracted {len(content)} characters")
            else:
                entry.content = ""
                entry.content_length = 0
                print(f"  ✗ Failed to extract content")
            
            scraped_entries.append(entry)
            
            # Be respectful with delays between requests
            if i < len(entries) - 1:
                time.sleep(options.delay)
        
        return scraped_entries
    
    def scrape_urls(self, urls: List[str], options: ScrapingOptions) -> List[Dict[str, Any]]:
        """Scrape content from a list of URLs."""
        results = []
        
        for i, url in enumerate(urls):
            print(f"Scraping {i+1}/{len(urls)}: {url}")
            
            content = self.extract_text_from_url(url, options)
            
            result = {
                "url": url,
                "content": content,
                "content_length": len(content) if content else 0,
                "success": content is not None
            }
            
            results.append(result)
            
            # Be respectful with delays between requests
            if i < len(urls) - 1:
                time.sleep(options.delay)
        
        return results 