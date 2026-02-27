"""Chat info utilities for displaying chat titles and usernames."""

import logging
from telethon import TelegramClient, utils
from telethon.tl.custom.message import Message

logger = logging.getLogger(__name__)

# Cache for chat info to avoid repeated API calls
_chat_info_cache = {}


async def get_chat_display_info(client: TelegramClient, chat_id: int) -> dict:
    """
    Get display information for a chat/user.
    Returns dict with 'title', 'username', 'type', and 'mention'.
    
    Caches results to avoid repeated API calls.
    """
    if chat_id in _chat_info_cache:
        return _chat_info_cache[chat_id]
    
    try:
        entity = await client.get_entity(chat_id)
        
        # Determine chat type and get display info
        from telethon.tl.types import Channel, Chat, User
        
        if isinstance(entity, Channel):
            chat_type = "channel" if entity.broadcast else "supergroup"
            title = entity.title
            username = entity.username
        elif isinstance(entity, Chat):
            chat_type = "group"
            title = entity.title
            username = None
        elif isinstance(entity, User):
            chat_type = "user"
            # Get full name
            first_name = entity.first_name or ""
            last_name = entity.last_name or ""
            title = f"{first_name} {last_name}".strip() or "Deleted Account"
            username = entity.username
        else:
            chat_type = "unknown"
            title = str(chat_id)
            username = None
        
        # Create mention string
        if username:
            mention = f"@{username}"
        elif chat_type == "user":
            mention = f"👤 {title}"
        else:
            mention = ""
        
        info = {
            "title": title,
            "username": username,
            "chat_type": chat_type,
            "mention": mention,
            "id": chat_id
        }
        
        _chat_info_cache[chat_id] = info
        return info
        
    except Exception as e:
        logger.debug(f"Failed to get chat info for {chat_id}: {e}")
        return {
            "title": str(chat_id),
            "username": None,
            "chat_type": "unknown",
            "mention": "",
            "id": chat_id
        }


def format_chat_id_with_title(chat_id: int, info: dict = None) -> str:
    """
    Format a chat ID with its title/username for display.
    
    Examples:
        Channel: (-1001234567890) Indonesian Group
        User with username: (123456) @Anony
        User without username: (123456) 👤 Anonymous User
    """
    if info is None:
        return f"`{chat_id}`"
    
    title = info.get("title", str(chat_id))
    mention = info.get("mention", "")
    chat_type = info.get("chat_type", "unknown")
    
    # Format based on type
    if chat_type == "user":
        if mention:
            return f"({chat_id}) {mention}"
        else:
            return f"({chat_id}) 👤 {title}"
    elif chat_type in ["channel", "supergroup"]:
        emoji = "📢" if chat_type == "channel" else "👥"
        return f"{emoji} ({chat_id}) {title}"
    elif chat_type == "group":
        return f"👥 ({chat_id}) {title}"
    else:
        return f"({chat_id}) {title}"


async def format_chat_list(client: TelegramClient, chat_ids: list) -> str:
    """
    Format a list of chat IDs with their titles for display.
    Returns a formatted string with each chat on a new line.
    """
    if not chat_ids:
        return "No chats"
    
    lines = []
    for chat_id in chat_ids:
        try:
            # Try to resolve if it's a string
            if isinstance(chat_id, str):
                if chat_id.startswith('@'):
                    entity = await client.get_entity(chat_id)
                    chat_id = utils.get_peer_id(entity)
                else:
                    chat_id = int(chat_id)
        except:
            pass
        
        info = await get_chat_display_info(client, chat_id)
        formatted = format_chat_id_with_title(chat_id, info)
        lines.append(formatted)
    
    return "\n".join(lines)
