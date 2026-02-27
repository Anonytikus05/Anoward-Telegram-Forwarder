"""Configuration manager for loading and saving JSON config files."""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages configuration files for the bot."""
    
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = Path(base_dir)
        self.config_dir = self.base_dir / "config"
        
    def _load_json(self, filepath: Path) -> dict:
        """Load JSON file and return its content."""
        logger.info(f"_load_json: Loading from {filepath}")
        if not filepath.exists():
            logger.warning(f"_load_json: File does not exist: {filepath}")
            return {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"_load_json: Successfully loaded from {filepath}")
            logger.debug(f"_load_json: Data: {data}")
            return data
        except Exception as e:
            logger.error(f"_load_json: Failed to load: {e}")
            return {}
    
    def _save_json(self, filepath: Path, data: dict) -> None:
        """Save data to JSON file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"_save_json: Saving to {filepath}")
        logger.info(f"_save_json: Data: {data}")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.info(f"_save_json: Successfully saved to {filepath}")
            
            # Verify by reading back immediately
            with open(filepath, 'r', encoding='utf-8') as f:
                verify_data = json.load(f)
            logger.info(f"_save_json: Verified data matches: {verify_data == data}")
        except Exception as e:
            logger.error(f"_save_json: Failed to save: {e}")
            raise
    
    def get_credentials(self) -> dict:
        """Load credentials from config/credentials.json."""
        filepath = self.config_dir / "credentials.json"
        return self._load_json(filepath)
    
    def save_credentials(self, credentials: dict) -> None:
        """Save credentials to config/credentials.json."""
        filepath = self.config_dir / "credentials.json"
        self._save_json(filepath, credentials)
    
    def get_forward_rules(self) -> dict:
        """Load forward rules from config/forward.json."""
        filepath = self.config_dir / "forward.json"
        return self._load_json(filepath)
    
    def save_forward_rules(self, rules: dict) -> None:
        """Save forward rules to config/forward.json."""
        filepath = self.config_dir / "forward.json"
        self._save_json(filepath, rules)
    
    def get_bookmarks(self) -> dict:
        """Load bookmarks from config/bm.json."""
        filepath = self.config_dir / "bm.json"
        return self._load_json(filepath)
    
    def save_bookmarks(self, bookmarks: dict) -> None:
        """Save bookmarks to config/bm.json."""
        filepath = self.config_dir / "bm.json"
        self._save_json(filepath, bookmarks)


# Global instance
config_manager = ConfigManager()
