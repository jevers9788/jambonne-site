import plistlib
import os
import requests
from bs4 import BeautifulSoup
import time
import re
import json
from typing import List, Dict, Optional


def clean_text(text: str) -> str:
    """Clean and normalize extracted text."""
    if not text:
        return ""

    # Remove extra whitespace and normalize
    text = re.sub(r"\s+", " ", text.strip())
    # Remove common web artifacts
    text = re.sub(r"[^\w\s\.\,\!\?\;\:\-\(\)\[\]]", "", text)
    return text


def extract_text_from_url(url: str, timeout: int = 10) -> Optional[str]:
    """Extract main text content from a URL."""
    try:
        # Add headers to mimic a real browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.content, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()

        # Try to find main content areas
        main_content = None

        # Look for common content selectors
        selectors = [
            "main",
            "article",
            ".content",
            ".post-content",
            ".entry-content",
            "#content",
            "#main",
            ".main-content",
            '[role="main"]',
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
        return clean_text(text)

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None


def read_safari_reading_list() -> List[Dict]:
    """Read Safari reading list and return structured data."""
    # Construct the path to the Bookmarks.plist file
    bookmarks_path = os.path.expanduser("~/Library/Safari/Bookmarks.plist")

    # Check if the file exists
    if not os.path.exists(bookmarks_path):
        print(f"Error: Safari Bookmarks.plist not found at {bookmarks_path}")
        return []

    try:
        # Load the plist file
        with open(bookmarks_path, "rb") as fp:
            plist_data = plistlib.load(fp)

        # Find the Reading List section
        reading_list = None
        for item in plist_data.get("Children", []):
            if item.get("Title") == "com.apple.ReadingList":
                reading_list = item.get("Children", [])
                break

        if reading_list:
            entries = []
            for entry in reading_list:
                title = entry.get("URLString", "No Title")
                if "URIDictionary" in entry and "title" in entry["URIDictionary"]:
                    title = entry["URIDictionary"]["title"]
                url = entry.get("URLString", "No URL")

                entries.append(
                    {
                        "title": title,
                        "url": url,
                        "date_added": entry.get("DateAdded", "Unknown"),
                    }
                )
            return entries
        else:
            print("No Reading List found in Bookmarks.plist.")
            return []

    except Exception as e:
        print(f"Error reading Bookmarks.plist: {e}")
        return []


def scrape_reading_list_content(entries: List[Dict], delay: float = 1.0) -> List[Dict]:
    """Scrape content from reading list URLs."""
    scraped_entries = []

    print(f"Scraping content from {len(entries)} URLs...")

    for i, entry in enumerate(entries, 1):
        url = entry["url"]
        title = entry["title"]

        print(f"[{i}/{len(entries)}] Scraping: {title}")

        # Skip invalid URLs
        if not url or url == "No URL":
            print(f"  Skipping invalid URL: {url}")
            continue

        # Extract text content
        content = extract_text_from_url(url)

        if content:
            # Truncate content if too long (for mind map purposes)
            if len(content) > 5000:
                content = content[:5000] + "..."

            entry["scraped_content"] = content
            entry["content_length"] = len(content)
            print(f"  ✓ Extracted {len(content)} characters")
        else:
            entry["scraped_content"] = ""
            entry["content_length"] = 0
            print("  ✗ Failed to extract content")

        scraped_entries.append(entry)

        # Be respectful with delays between requests
        if i < len(entries):
            time.sleep(delay)

    return scraped_entries


def save_scraped_data(entries: List[Dict], filename: str = "reading_list_content.json"):
    """Save scraped data to JSON file."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False, default=str)
        print(f"Saved scraped data to {filename}")
    except Exception as e:
        print(f"Error saving data: {e}")


def generate_mind_map_data(entries: List[Dict]) -> Dict:
    """Generate structured data for mind map creation."""
    mind_map = {"central_topic": "Safari Reading List", "branches": []}

    for entry in entries:
        if entry.get("scraped_content"):
            # Create a branch for each article
            branch = {
                "topic": entry["title"],
                "url": entry["url"],
                "content_preview": entry["scraped_content"][:200] + "...",
                "content_length": entry["content_length"],
            }
            mind_map["branches"].append(branch)

    return mind_map


def main():
    """Main function to read, scrape, and process reading list."""
    # Read Safari reading list
    entries = read_safari_reading_list()

    if not entries:
        print("No entries found in Safari reading list.")
        return

    print(f"Found {len(entries)} entries in Safari reading list.")

    # Ask user if they want to scrape content
    response = (
        input("Do you want to scrape content from these URLs? (y/n): ").lower().strip()
    )

    if response == "y":
        # Scrape content
        scraped_entries = scrape_reading_list_content(entries)

        # Save raw data
        save_scraped_data(scraped_entries)

        # Generate mind map data
        mind_map_data = generate_mind_map_data(scraped_entries)

        # Save mind map data
        with open("mind_map_data.json", "w", encoding="utf-8") as f:
            json.dump(mind_map_data, f, indent=2, ensure_ascii=False)

        print("\nMind map data saved to mind_map_data.json")
        print(f"Processed {len(mind_map_data['branches'])} articles with content")

        # Print summary
        print("\nSummary:")
        for branch in mind_map_data["branches"]:
            print(f"- {branch['topic']} ({branch['content_length']} chars)")

    else:
        # Just display the reading list without scraping
        print("\nSafari Reading List:")
        for entry in entries:
            print(f"- Title: {entry['title']}")
            print(f"  URL: {entry['url']}")
            print(f"  Date Added: {entry['date_added']}\n")


if __name__ == "__main__":
    main()
