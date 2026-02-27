"""Userbot forwarding logic for automatically forwarding messages."""

import asyncio
import logging
from telethon import TelegramClient, events
from telethon.tl.custom.message import Message
from telethon.errors import FloodWaitError
from telethon import utils
from utils.forward_manager import forward_manager, ForwardRule
from utils.bookmark_manager import bookmark_manager

logger = logging.getLogger(__name__)


class ForwardingUserbot:
    """Handles message forwarding as a userbot."""

    def __init__(self, client: TelegramClient):
        self.client = client
        self.active_rules: list[ForwardRule] = []
        self.bookmarks: dict[str, str] = {}
        self.resolved_sources: dict[str, int] = {}  # Cache resolved source IDs
        self.forwarded_messages: set = set()  # Track recently forwarded messages

    async def load_rules(self):
        """Load active forwarding rules and bookmarks."""
        self.active_rules = forward_manager.get_active_rules()
        # Load bookmarks as title->target mapping (NOT bm_id)
        all_bookmarks = bookmark_manager.get_all_bookmarks()
        self.bookmarks = {bm.title.lower(): bm.target for bm in all_bookmarks}
        logger.info(f"Loaded {len(self.active_rules)} active forwarding rules")
        logger.info(f"Loaded {len(self.bookmarks)} bookmarks (title->target)")

        # Pre-resolve all source chat IDs for faster matching
        await self._preload_resolved_ids()

    async def _preload_resolved_ids(self):
        """Pre-resolve all source and destination IDs from active rules."""
        self.resolved_sources = {}
        for rule in self.active_rules:
            for src in rule.sources:
                resolved = await self.resolve_chat_id(src)
                if resolved:
                    self.resolved_sources[src] = resolved
                    logger.info(f"Resolved source '{src}' to chat ID {resolved}")
            
            for dst in rule.destinations:
                resolved = await self.resolve_chat_id(dst)
                if resolved:
                    logger.info(f"Resolved destination '{dst}' to chat ID {resolved}")

    def refresh_rules(self):
        """Refresh rules from config (call after config changes)."""
        asyncio.create_task(self.load_rules())

    async def resolve_chat_id(self, identifier: str) -> int | None:
        """
        Resolve a chat identifier (ID, username, or bookmark TITLE) to an actual chat ID.
        Returns None if resolution fails.
        
        Note: Only bookmark titles can be used as aliases, NOT bm_id.
        """
        if not identifier or not identifier.strip():
            return None

        identifier = identifier.strip()

        try:
            # Check if it's a bookmark by TITLE (case-insensitive)
            # NOTE: bm_id is NOT allowed as alias, only titles
            bookmarks = bookmark_manager.get_all_bookmarks()
            bookmark_found = None
            
            # Check by bookmark title (case-insensitive)
            for bm in bookmarks:
                if bm.title.lower() == identifier.lower():
                    identifier = bm.target
                    bookmark_found = identifier
                    break
            
            # If bookmark resolved to another bookmark, resolve recursively
            if bookmark_found:
                while True:
                    found_nested = False
                    for bm in bookmarks:
                        if bm.title.lower() == identifier.lower():
                            identifier = bm.target
                            found_nested = True
                            break
                    if not found_nested:
                        break

            # Try to resolve the identifier
            if identifier.startswith('@'):
                # It's a username
                entity = await self.client.get_entity(identifier)
                return utils.get_peer_id(entity)
            elif identifier.startswith('+'):
                # It's a phone number
                entity = await self.client.get_entity(identifier)
                return utils.get_peer_id(entity)
            elif identifier.lstrip('-').isdigit():
                # It's a numeric ID (can be negative for channels/supergroups)
                chat_id = int(identifier)
                entity = await self.client.get_entity(chat_id)
                return utils.get_peer_id(entity)
            else:
                # Invalid format
                logger.warning(f"Invalid identifier format: '{identifier}'")
                return None
        except ValueError as e:
            logger.warning(f"Failed to parse chat ID '{identifier}': {e}")
            return None
        except Exception as e:
            logger.warning(f"Failed to resolve chat ID '{identifier}': {e}")
            return None

    def should_forward_message(self, message: Message, rule: ForwardRule) -> bool:
        """Check if a message should be forwarded based on rule configuration."""
        # Check message type
        msg_type = self.get_message_type(message)
        if msg_type not in rule.message_types:
            logger.debug(f"Message type '{msg_type}' not in rule types {rule.message_types}")
            return False

        return True

    def get_message_type(self, message: Message) -> str:
        """Determine the type of message."""
        if message.text and not message.media:
            return "Text"
        if message.photo:
            return "Photo"
        if message.video:
            return "Video"
        if message.document:
            return "File"
        if message.audio:
            return "Audio"
        if message.voice:
            return "Audio"
        if message.sticker:
            return "Photo"

        # Default to Text for other types
        return "Text"

    async def forward_message(self, message: Message, destination: int,
                              hide_forwarded: bool = False) -> bool:
        """
        Forward a single message to a destination.
        Returns True if successful, False otherwise.
        """
        try:
            # Determine forwarding method based on hide_forwarded
            if hide_forwarded:
                # Send without 'Forwarded from' tag by copying content
                if message.text and not message.media:
                    # Text only
                    await self.client.send_message(
                        destination,
                        message.text
                    )
                elif message.media:
                    # Message with media - forward without caption if no text
                    caption = message.message if message.message else ""
                    await self.client.send_message(
                        destination,
                        caption,
                        file=message.media
                    )
                else:
                    # Fallback: regular forward
                    await self.client.forward_messages(destination, message)
            else:
                # Regular forward with 'Forwarded from' tag
                await self.client.forward_messages(destination, message)

            logger.info(f"Forwarded message {message.id} to {destination}")
            return True
        except FloodWaitError as e:
            logger.warning(f"FloodWait: Waiting {e.seconds} seconds...")
            await asyncio.sleep(e.seconds)
            # Retry once after waiting
            try:
                return await self.forward_message(message, destination, hide_forwarded)
            except Exception:
                return False
        except Exception as e:
            logger.error(f"Error forwarding message: {e}")
            return False

    async def handle_new_message(self, event: events.NewMessage.Event):
        """Handle incoming messages and forward based on active rules."""
        message = event.message
        source_chat_id = message.chat_id
        
        logger.info(f"📨 Received message {message.id} from chat {source_chat_id} (type: {type(source_chat_id).__name__})")
        
        # Skip if this message was recently forwarded by us (prevent loops)
        if message.id in self.forwarded_messages:
            logger.debug(f"Skipping message {message.id} - already forwarded")
            return
        
        # Clean up old forwarded message IDs (keep last 1000)
        if len(self.forwarded_messages) > 1000:
            self.forwarded_messages = set(list(self.forwarded_messages)[-500:])

        logger.debug(f"Active rules to check: {len(self.active_rules)}")
        logger.debug(f"Resolved sources cache: {self.resolved_sources}")
        
        # Log chat ID format info for debugging
        logger.info(f"📋 Source chat IDs in config vs received:")
        for rule in self.active_rules:
            for src in rule.sources:
                cached = self.resolved_sources.get(src)
                logger.info(f"   Config: '{src}' -> Cached: {cached} | Received: {source_chat_id} | Match: {cached == source_chat_id}")

        # Check each active rule
        for rule in self.active_rules:
            logger.debug(f"Checking rule {rule.fwd_id}: sources={rule.sources}, active={rule.active}")
            
            # Check if source_chat_id matches any resolved source for this rule
            source_matched = False
            
            for src in rule.sources:
                logger.debug(f"  Checking source '{src}'...")
                
                # Check cache first
                if src in self.resolved_sources:
                    cached_id = self.resolved_sources[src]
                    logger.debug(f"    Cache hit: '{src}' -> {cached_id}, comparing with {source_chat_id}")
                    if cached_id == source_chat_id:
                        source_matched = True
                        logger.info(f"  ✅ Matched chat {source_chat_id} to rule source '{src}' (cached)")
                        break
                else:
                    # Resolve on the fly
                    logger.debug(f"    Cache miss, resolving '{src}'...")
                    resolved_src = await self.resolve_chat_id(src)
                    if resolved_src:
                        self.resolved_sources[src] = resolved_src
                        logger.debug(f"    Resolved: '{src}' -> {resolved_src}")
                        if resolved_src == source_chat_id:
                            source_matched = True
                            logger.info(f"  ✅ Matched chat {source_chat_id} to rule source '{src}' (resolved)")
                            break
                    else:
                        logger.warning(f"    Could not resolve source '{src}'")
            
            if not source_matched:
                logger.debug(f"  ❌ No source match for rule {rule.fwd_id}")
                continue

            logger.info(f"  🎯 Source matched for rule {rule.fwd_id}")

            # This message should be forwarded!
            if not self.should_forward_message(message, rule):
                msg_type = self.get_message_type(message)
                logger.info(f"  ❌ Message type '{msg_type}' not in rule types {rule.message_types}")
                continue

            logger.info(f"  📤 Forwarding message {message.id} from chat {source_chat_id} (rule {rule.fwd_id})")

            # Forward to all destinations
            for dst in rule.destinations:
                logger.debug(f"    Resolving destination '{dst}'...")
                resolved_dst = await self.resolve_chat_id(dst)
                if resolved_dst:
                    logger.info(f"    Destination resolved: '{dst}' -> {resolved_dst}")
                    success = await self.forward_message(
                        message,
                        resolved_dst,
                        rule.hide_forwarded
                    )
                    if success:
                        self.forwarded_messages.add(message.id)
                        logger.info(f"    ✅ Successfully forwarded to {resolved_dst}")
                    else:
                        logger.error(f"    ❌ Failed to forward to {resolved_dst}")
                else:
                    logger.warning(f"    ❌ Could not resolve destination '{dst}'")

    def register_handlers(self):
        """Register the message handler with the client."""
        # Handle ALL new messages (including our own outgoing messages)
        @self.client.on(events.NewMessage)
        async def new_message_handler(event: events.NewMessage.Event):
            # Log all messages including outgoing
            logger.info(f"📬 [EVENT] New message: chat_id={event.chat_id}, id={event.message.id}, from={event.sender_id}, out={event.message.out}")
            await self.handle_new_message(event)
        
        logger.info("✅ Message handler registered (all messages)")


def create_userbot_client(api_id: int, api_hash: str, phone: str) -> TelegramClient:
    """Create and return a TelegramClient for the userbot."""
    client = TelegramClient(
        'anoward_userbot',
        api_id,
        api_hash
    )
    
    return client
