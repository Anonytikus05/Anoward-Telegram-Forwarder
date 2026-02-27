"""Bookmark manager for managing chat ID bookmarks."""

from typing import List, Dict, Optional
from utils.config_manager import config_manager


class Bookmark:
    """Represents a single bookmark."""
    
    def __init__(self, bm_id: str, target: str, title: str):
        self.bm_id = bm_id
        self.target = target
        self.title = title
    
    def to_dict(self) -> dict:
        """Convert bookmark to dictionary."""
        return {
            "bm_id": self.bm_id,
            "target": self.target,
            "title": self.title
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Bookmark":
        """Create Bookmark from dictionary."""
        return cls(
            bm_id=data.get("bm_id", ""),
            target=data.get("target", ""),
            title=data.get("title", "")
        )


class BookmarkManager:
    """Manages bookmarks."""
    
    def __init__(self):
        self.config_manager = config_manager
    
    def _get_next_bm_id(self, bookmarks: List[dict]) -> str:
        """Generate the next available bm_id (3 digits)."""
        if not bookmarks:
            return "001"
        
        existing_ids = []
        for bm in bookmarks:
            try:
                bid = int(bm.get("bm_id", "0"))
                existing_ids.append(bid)
            except ValueError:
                continue
        
        if not existing_ids:
            return "001"
        
        next_id = max(existing_ids) + 1
        return f"{next_id:03d}"
    
    def get_all_bookmarks(self) -> List[Bookmark]:
        """Get all bookmarks."""
        data = self.config_manager.get_bookmarks()
        bookmarks_data = data.get("bookmarks", [])
        return [Bookmark.from_dict(b) for b in bookmarks_data]
    
    def get_bookmark(self, bm_id: str) -> Optional[Bookmark]:
        """Get a specific bookmark by bm_id."""
        bookmarks = self.get_all_bookmarks()
        for bm in bookmarks:
            if bm.bm_id == bm_id:
                return bm
        return None
    
    def add_bookmark(self, target: str, title: str) -> Bookmark:
        """Add a new bookmark."""
        data = self.config_manager.get_bookmarks()
        bookmarks_data = data.get("bookmarks", [])
        
        new_bm_id = self._get_next_bm_id(bookmarks_data)
        
        new_bookmark = Bookmark(
            bm_id=new_bm_id,
            target=target,
            title=title
        )
        
        bookmarks_data.append(new_bookmark.to_dict())
        data["bookmarks"] = bookmarks_data
        self.config_manager.save_bookmarks(data)
        
        return new_bookmark
    
    def delete_bookmark(self, bm_ids: List[str]) -> bool:
        """Delete one or more bookmarks by bm_id."""
        data = self.config_manager.get_bookmarks()
        bookmarks_data = data.get("bookmarks", [])
        
        original_count = len(bookmarks_data)
        bookmarks_data = [b for b in bookmarks_data if b.get("bm_id") not in bm_ids]
        
        if len(bookmarks_data) < original_count:
            data["bookmarks"] = bookmarks_data
            self.config_manager.save_bookmarks(data)
            return True
        return False
    
    def get_bookmark_dict(self) -> Dict[str, str]:
        """Get bookmarks as a dictionary {bm_id: target}."""
        bookmarks = self.get_all_bookmarks()
        return {bm.bm_id: bm.target for bm in bookmarks}
    
    def find_bookmark_by_title(self, title: str) -> Optional[Bookmark]:
        """Find a bookmark by its title."""
        bookmarks = self.get_all_bookmarks()
        for bm in bookmarks:
            if bm.title.lower() == title.lower():
                return bm
        return None


# Global instance
bookmark_manager = BookmarkManager()
