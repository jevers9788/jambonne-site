import plistlib
import os
from typing import List 
from datetime import datetime
from ..models import ReadingListEntry


class SafariReader:
    """Service for reading Safari reading list from Bookmarks.plist"""
    
    def __init__(self):
        self.bookmarks_path = os.path.expanduser("~/Library/Safari/Bookmarks.plist")
    
    def read_reading_list(self) -> List[ReadingListEntry]:
        """Read Safari reading list and return structured data."""
        if not os.path.exists(self.bookmarks_path):
            raise FileNotFoundError(f"Safari Bookmarks.plist not found at {self.bookmarks_path}")
        
        try:
            with open(self.bookmarks_path, 'rb') as fp:
                plist_data = plistlib.load(fp)
            
            # Find the Reading List section
            reading_list = None
            for item in plist_data.get('Children', []):
                if item.get('Title') == 'com.apple.ReadingList':
                    reading_list = item.get('Children', [])
                    break
            
            if not reading_list:
                return []
            
            entries = []
            for entry in reading_list:
                title = entry.get('URLString', 'No Title')
                if 'URIDictionary' in entry and 'title' in entry['URIDictionary']:
                    title = entry['URIDictionary']['title']
                
                url = entry.get('URLString', '')
                if not url or url == 'No URL':
                    continue
                
                # Convert date
                date_added = entry.get('DateAdded', datetime.now())
                if isinstance(date_added, (int, float)):
                    date_added = datetime.fromtimestamp(date_added)
                
                entries.append(ReadingListEntry(
                    title=title,
                    url=url,
                    date_added=date_added
                ))
            
            return entries
            
        except Exception as e:
            raise Exception(f"Error reading Bookmarks.plist: {e}")
    
    def get_reading_list_summary(self) -> dict:
        """Get a summary of the reading list without full content."""
        entries = self.read_reading_list()
        return {
            "total_count": len(entries),
            "recent_entries": entries[:5] if entries else [],
            "date_range": {
                "oldest": min(entry.date_added for entry in entries) if entries else None,
                "newest": max(entry.date_added for entry in entries) if entries else None
            }
        } 