"""Error handling and utility functions for the Anoward bot."""

import asyncio
from functools import wraps
from telethon.errors import FloodWaitError, RPCError
from telethon import events


def handle_floodwait(func):
    """Decorator to handle FloodWaitError automatically."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                return await func(*args, **kwargs)
            except FloodWaitError as e:
                retry_count += 1
                wait_time = e.seconds
                
                if retry_count >= max_retries:
                    print(f"Max retries reached after FloodWait of {wait_time}s")
                    return None
                
                print(f"FloodWait: Waiting {wait_time} seconds... (Attempt {retry_count}/{max_retries})")
                await asyncio.sleep(wait_time)
            except Exception as e:
                print(f"Error in {func.__name__}: {e}")
                raise
        
        return None
    return wrapper


def friendly_error_message(error: Exception) -> str:
    """Generate a friendly error message based on the exception type."""
    if isinstance(error, FloodWaitError):
        return f"⏳ Whoops! Telegram is asking us to slow down. Please wait {error.seconds} seconds and try again. 🐌"
    
    if isinstance(error, RPCError):
        error_messages = {
            "USER_IS_BLOCKED": "😕 The user has blocked the bot. They won't receive messages.",
            "USER_NOT_MUTUAL_CONTACT": "🔒 The user has privacy settings that prevent messaging.",
            "CHAT_WRITE_FORBIDDEN": "🚫 You don't have permission to send messages in this chat.",
            "CHAT_SEND_MEDIA_FORBIDDEN": "🚫 You don't have permission to send media in this chat.",
            "MESSAGE_DELETE_FORBIDDEN": "🚫 You don't have permission to delete messages in this chat.",
            "PEER_ID_INVALID": "❌ The peer ID is invalid. Please check the chat ID or username.",
            "CHANNEL_PRIVATE": "🔒 This channel/group is private. Make sure you're a member.",
            "USER_NOT_PARTICIPANT": "🚫 You're not a participant of this group/channel.",
            "MSG_ID_INVALID": "❌ The message ID is invalid. It might have been deleted.",
            "MEDIA_EMPTY": "📭 The media is empty or invalid.",
            "MEDIA_INVALID": "❌ The media file is invalid.",
            "PHOTO_INVALID_DIMENSIONS": "📐 The photo dimensions are invalid.",
            "INPUT_USER_DEACTIVATED": "💤 This user account has been deleted or deactivated.",
            "AUTH_KEY_UNREGISTERED": "🔑 The authentication key is not registered. Please re-authenticate.",
            "SESSION_PASSWORD_NEEDED": "🔐 Two-factor authentication is enabled. Please check your password.",
            "PHONE_NUMBER_INVALID": "📱 The phone number provided is invalid.",
            "PHONE_CODE_INVALID": "🔢 The verification code is incorrect.",
            "API_ID_INVALID": "⚙️ The API ID is invalid. Please check your credentials.",
            "API_ID_PUBLISHED_FLOOD": "⚠️ This API ID has been published and is causing flood errors.",
            "BOT_METHOD_INVALID": "🤖 This method is not available for bots.",
            "BOT_DOMAIN_INVALID": "🌐 The bot domain is invalid.",
            "BOT_COMMAND_INVALID": "❌ The bot command is invalid.",
            "FILE_ID_INVALID": "📁 The file ID is invalid.",
            "PERSISTENT_TIMESTAMP_INVALID": "⏰ The timestamp is invalid.",
            "WORKER_BUSY_TOO_LONG_RETRY": "⏳ The worker is busy. Please try again later.",
            "INTERNAL_ERROR": "💥 An internal error occurred. Please try again later.",
        }
        
        # Try to find a specific message for this error
        for key, msg in error_messages.items():
            if key in str(error).upper():
                return f"😅 {msg}\n\n(Technical: {error})"
        
        return f"😅 Oops! Something went wrong: {error}\n\nPlease try again or contact support if the issue persists. 🔧"
    
    return f"😅 An unexpected error occurred: {error}\n\nDon't worry, our team has been notified! 🔧"


def error_handler(func):
    """Decorator to handle errors with friendly messages."""
    @wraps(func)
    async def wrapper(event: events.NewMessage.Event, *args, **kwargs):
        try:
            return await func(event, *args, **kwargs)
        except FloodWaitError as e:
            msg = friendly_error_message(e)
            await event.respond(msg)
        except RPCError as e:
            msg = friendly_error_message(e)
            await event.respond(msg)
        except Exception as e:
            msg = friendly_error_message(e)
            await event.respond(msg)
            print(f"Unexpected error in {func.__name__}: {e}")
    return wrapper


def fuzzy_match(input_str: str, candidates: list[str], threshold: float = 0.6) -> list[str]:
    """
    Perform fuzzy matching on input string against a list of candidates.
    Returns matching candidates sorted by similarity.
    
    Uses a simple ratio-based matching algorithm.
    """
    input_lower = input_str.lower()
    matches = []
    
    for candidate in candidates:
        candidate_lower = candidate.lower()
        
        # Exact match
        if input_lower == candidate_lower:
            matches.append((candidate, 1.0))
            continue
        
        # Check if input is a substring
        if input_lower in candidate_lower:
            ratio = len(input_lower) / len(candidate_lower)
            matches.append((candidate, ratio))
            continue
        
        # Check if candidate is a substring
        if candidate_lower in input_lower:
            ratio = len(candidate_lower) / len(input_lower)
            matches.append((candidate, ratio))
            continue
        
        # Simple character-based similarity
        common_chars = sum(1 for c in input_lower if c in candidate_lower)
        max_len = max(len(input_lower), len(candidate_lower))
        ratio = common_chars / max_len if max_len > 0 else 0
        
        if ratio >= threshold:
            matches.append((candidate, ratio))
    
    # Sort by similarity (highest first)
    matches.sort(key=lambda x: x[1], reverse=True)
    
    return [m[0] for m in matches]


def suggest_correction(input_str: str, candidates: list[str]) -> str:
    """
    Suggest a correction for an invalid input.
    Returns a friendly suggestion message.
    """
    matches = fuzzy_match(input_str, candidates)
    
    if not matches:
        return ""
    
    top_match = matches[0]
    
    if len(matches) == 1:
        return f"💡 Did you mean `{top_match}`?"
    else:
        suggestions = ", ".join(f"`{m}`" for m in matches[:3])
        return f"💡 Did you mean one of these: {suggestions}?"
