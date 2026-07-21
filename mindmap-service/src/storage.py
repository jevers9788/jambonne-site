"""
Persistent storage for mindmap data using file-based JSON storage.

This module provides thread-safe file operations for storing and retrieving
mindmap data. Uses file locking to prevent race conditions.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional
from filelock import FileLock, Timeout
from datetime import datetime

# Storage paths
STORAGE_DIR = Path(__file__).parent.parent / "storage"
STORAGE_FILE = STORAGE_DIR / "mindmaps.json"
LOCK_FILE = STORAGE_DIR / "mindmaps.lock"


def ensure_storage_exists():
    """Ensure storage directory and file exist."""
    STORAGE_DIR.mkdir(exist_ok=True)
    if not STORAGE_FILE.exists():
        STORAGE_FILE.write_text("{}")


def load_mindmaps() -> Dict:
    """
    Load all mindmaps from persistent storage.

    Returns:
        Dict mapping mindmap IDs to mindmap data

    Raises:
        Exception if storage is corrupted or unreadable
    """
    ensure_storage_exists()

    try:
        with FileLock(LOCK_FILE, timeout=5):
            with open(STORAGE_FILE, 'r') as f:
                data = json.load(f)

                # Convert datetime strings back to objects if needed
                for mindmap_id, mindmap in data.items():
                    if isinstance(mindmap.get('created_at'), str):
                        # Keep as string for now - Pydantic will handle conversion
                        pass

                return data
    except Timeout:
        raise Exception("Could not acquire lock on storage file - timeout")
    except json.JSONDecodeError as e:
        raise Exception(f"Storage file is corrupted: {e}")
    except Exception as e:
        raise Exception(f"Error loading mindmaps: {e}")


def save_mindmaps(mindmaps: Dict) -> None:
    """
    Save all mindmaps to persistent storage atomically.

    Uses atomic write pattern (write to temp file, then rename) to prevent
    corruption if process is interrupted during write.

    Args:
        mindmaps: Dict mapping mindmap IDs to mindmap data

    Raises:
        Exception if write fails
    """
    ensure_storage_exists()

    temp_file = STORAGE_FILE.with_suffix('.json.tmp')

    try:
        with FileLock(LOCK_FILE, timeout=10):
            # Write to temporary file first
            with open(temp_file, 'w') as f:
                json.dump(mindmaps, f, indent=2, default=str)

            # Atomic rename (overwrites existing file)
            temp_file.replace(STORAGE_FILE)

    except Timeout:
        if temp_file.exists():
            temp_file.unlink()
        raise Exception("Could not acquire lock on storage file - timeout")
    except Exception as e:
        if temp_file.exists():
            temp_file.unlink()
        raise Exception(f"Error saving mindmaps: {e}")


def save_mindmap(mindmap_id: str, mindmap_data: Dict) -> None:
    """
    Save a single mindmap to storage.

    Args:
        mindmap_id: Unique identifier for the mindmap
        mindmap_data: Mindmap data to save
    """
    mindmaps = load_mindmaps()
    mindmaps[mindmap_id] = mindmap_data
    save_mindmaps(mindmaps)


def delete_mindmap(mindmap_id: str) -> bool:
    """
    Delete a mindmap from storage.

    Args:
        mindmap_id: Unique identifier for the mindmap to delete

    Returns:
        True if mindmap was deleted, False if it didn't exist
    """
    mindmaps = load_mindmaps()
    if mindmap_id in mindmaps:
        del mindmaps[mindmap_id]
        save_mindmaps(mindmaps)
        return True
    return False


def get_latest_mindmap() -> Optional[Dict]:
    """
    Get the most recently created mindmap.

    Returns:
        Most recent mindmap data, or None if no mindmaps exist
    """
    mindmaps = load_mindmaps()
    if not mindmaps:
        return None

    # Sort by created_at timestamp and return the latest
    latest_id = max(mindmaps.keys(), key=lambda k: mindmaps[k].get('created_at', ''))
    return mindmaps[latest_id]
