"""Forwarding rules manager for managing message forwarding configurations."""

import logging
from typing import List, Dict, Optional, Any
from utils.config_manager import config_manager

logger = logging.getLogger(__name__)


class ForwardRule:
    """Represents a single forwarding rule."""
    
    def __init__(self, fwd_id: str, sources: List[str], destinations: List[str],
                 active: bool = False, message_types: List[str] = None,
                 hide_forwarded: bool = False):
        self.fwd_id = fwd_id
        self.sources = sources
        self.destinations = destinations
        self.active = active
        self.message_types = message_types or ["Text", "Photo", "Video", "File", "Audio"]
        self.hide_forwarded = hide_forwarded
    
    def to_dict(self) -> dict:
        """Convert rule to dictionary."""
        return {
            "fwd_id": self.fwd_id,
            "sources": self.sources,
            "destinations": self.destinations,
            "active": self.active,
            "message_types": self.message_types,
            "hide_forwarded": self.hide_forwarded
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ForwardRule":
        """Create ForwardRule from dictionary."""
        logger.debug(f"ForwardRule.from_dict: {data}")
        return cls(
            fwd_id=data.get("fwd_id", ""),
            sources=data.get("sources", []),
            destinations=data.get("destinations", []),
            active=data.get("active", False),
            message_types=data.get("message_types", ["Text", "Photo", "Video", "File", "Audio"]),
            hide_forwarded=data.get("hide_forwarded", False)
        )


class ForwardManager:
    """Manages forwarding rules."""
    
    def __init__(self):
        self.config_manager = config_manager
    
    def _get_next_fwd_id(self, rules: List[dict]) -> str:
        """Generate the next available fwd_id (3 digits)."""
        if not rules:
            return "001"
        
        existing_ids = []
        for rule in rules:
            try:
                fid = int(rule.get("fwd_id", "0"))
                existing_ids.append(fid)
            except ValueError:
                continue
        
        if not existing_ids:
            return "001"
        
        next_id = max(existing_ids) + 1
        return f"{next_id:03d}"
    
    def get_all_rules(self) -> List[ForwardRule]:
        """Get all forwarding rules."""
        data = self.config_manager.get_forward_rules()
        rules_data = data.get("rules", [])
        return [ForwardRule.from_dict(r) for r in rules_data]
    
    def get_rule(self, fwd_id: str) -> Optional[ForwardRule]:
        """Get a specific rule by fwd_id."""
        logger.info(f"get_rule: Looking for fwd_id={fwd_id}")
        rules = self.get_all_rules()
        logger.info(f"get_rule: Found {len(rules)} rules")
        for rule in rules:
            if rule.fwd_id == fwd_id:
                logger.info(f"get_rule: Found rule {fwd_id}, active={rule.active}, hide_forwarded={rule.hide_forwarded}")
                return rule
        logger.warning(f"get_rule: Rule {fwd_id} not found")
        return None
    
    def add_rule(self, sources: List[str], destinations: List[str]) -> Optional[ForwardRule]:
        """Add a new forwarding rule."""
        data = self.config_manager.get_forward_rules()
        rules_data = data.get("rules", [])
        
        new_fwd_id = self._get_next_fwd_id(rules_data)
        
        new_rule = ForwardRule(
            fwd_id=new_fwd_id,
            sources=sources,
            destinations=destinations,
            active=False,
            message_types=["Text", "Photo", "Video", "File", "Audio"],
            hide_forwarded=False
        )
        
        rules_data.append(new_rule.to_dict())
        data["rules"] = rules_data
        self.config_manager.save_forward_rules(data)
        
        return new_rule
    
    def delete_rule(self, fwd_ids: List[str]) -> bool:
        """Delete one or more rules by fwd_id."""
        data = self.config_manager.get_forward_rules()
        rules_data = data.get("rules", [])
        
        original_count = len(rules_data)
        rules_data = [r for r in rules_data if r.get("fwd_id") not in fwd_ids]
        
        if len(rules_data) < original_count:
            data["rules"] = rules_data
            self.config_manager.save_forward_rules(data)
            return True
        return False
    
    def set_rule_active(self, fwd_ids: List[str], active: bool) -> bool:
        """Set one or more rules as active or inactive."""
        data = self.config_manager.get_forward_rules()
        rules_data = data.get("rules", [])
        
        logger.info(f"set_rule_active: fwd_ids={fwd_ids}, active={active}")
        logger.info(f"set_rule_active: Current rules before update: {rules_data}")

        modified = False
        for rule in rules_data:
            if rule.get("fwd_id") in fwd_ids:
                old_active = rule.get("active")
                rule["active"] = active
                modified = True
                logger.info(f"set_rule_active: Set rule {rule.get('fwd_id')} active from {old_active} to {active}")

        if modified:
            data["rules"] = rules_data
            logger.info(f"set_rule_active: Saving rules: {data}")
            self.config_manager.save_forward_rules(data)
            logger.info(f"set_rule_active: Saved updated rules to forward.json")
            
            # Verify by reading back
            verify_data = self.config_manager.get_forward_rules()
            logger.info(f"set_rule_active: Verified saved data: {verify_data}")
            return True
        
        logger.warning(f"set_rule_active: No rules modified")
        return False

    def update_rule_config(self, fwd_id: str, message_types: List[str] = None,
                           hide_forwarded: bool = None) -> bool:
        """Update rule configuration (message types, hide forwarded)."""
        data = self.config_manager.get_forward_rules()
        rules_data = data.get("rules", [])
        
        logger.info(f"update_rule_config: fwd_id={fwd_id}, message_types={message_types}, hide_forwarded={hide_forwarded}")
        logger.info(f"update_rule_config: Current rules before update: {rules_data}")

        for rule in rules_data:
            if rule.get("fwd_id") == fwd_id:
                if message_types is not None:
                    rule["message_types"] = message_types
                    logger.info(f"update_rule_config: Set message_types to {message_types}")
                if hide_forwarded is not None:
                    rule["hide_forwarded"] = hide_forwarded
                    logger.info(f"update_rule_config: Set hide_forwarded to {hide_forwarded}")
                    
                data["rules"] = rules_data
                logger.info(f"update_rule_config: Saving rules: {data}")
                self.config_manager.save_forward_rules(data)
                logger.info(f"update_rule_config: Saved updated config for rule {fwd_id}")
                
                # Verify by reading back
                verify_data = self.config_manager.get_forward_rules()
                logger.info(f"update_rule_config: Verified saved data: {verify_data}")
                return True
                
        logger.warning(f"update_rule_config: Rule {fwd_id} not found")
        return False
    
    def get_active_rules(self) -> List[ForwardRule]:
        """Get all active forwarding rules."""
        rules = self.get_all_rules()
        return [r for r in rules if r.active]
    
    def resolve_id(self, identifier: str, bookmarks: Dict[str, str] = None) -> List[str]:
        """
        Resolve an identifier to actual chat IDs.
        Handles bookmarks (by TITLE only, not bm_id) and comma-separated values.
        Returns a list of resolved IDs.
        
        Note: Only bookmark titles can be used as aliases, NOT bm_id.
        """
        if bookmarks is None:
            bookmarks_data = self.config_manager.get_bookmarks()
            bookmarks = {b["bm_id"]: b["target"] for b in bookmarks_data.get("bookmarks", [])}
        
        # Create a title-to-target mapping (case-insensitive)
        from utils.bookmark_manager import bookmark_manager
        all_bookmarks = bookmark_manager.get_all_bookmarks()
        title_bookmarks = {bm.title.lower(): bm.target for bm in all_bookmarks}

        resolved = []
        parts = identifier.split(',')

        for part in parts:
            part = part.strip()
            resolved_part = None
            
            # Check if it's a bookmark by TITLE (case-insensitive)
            # NOTE: bm_id is NOT allowed as alias, only titles
            if part.lower() in title_bookmarks:
                resolved_part = title_bookmarks[part.lower()]
            
            if resolved_part:
                # Handle nested bookmarks recursively
                nested = self.resolve_id(resolved_part, bookmarks)
                resolved.extend(nested)
            else:
                resolved.append(part)

        return resolved


# Global instance
forward_manager = ForwardManager()
