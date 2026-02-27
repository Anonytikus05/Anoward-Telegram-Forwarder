"""
Anoward Bot - Telegram Message Forwarding Bot
Main entry point for the bot and userbot.
"""

import asyncio
import logging
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

from utils.config_manager import config_manager
from utils.forwarding_userbot import ForwardingUserbot
from handlers.bot_handlers import (
    cmd_start,
    cmd_help,
    cmd_forward,
    cmd_bookmark,
    handle_callback,
    is_whitelisted,
)
from utils.error_handler import friendly_error_message
from utils.chat_info import get_chat_display_info, format_chat_id_with_title

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Changed to DEBUG for more detailed logging
)
logger = logging.getLogger(__name__)


def load_credentials():
    """Load credentials from config."""
    credentials = config_manager.get_credentials()
    
    api_id = credentials.get('api_id')
    api_hash = credentials.get('api_hash')
    bot_token = credentials.get('bot_token')
    phone = credentials.get('phone')
    
    # Validate credentials
    if not api_id or not api_hash or not bot_token or not phone:
        raise ValueError(
            "❌ Missing credentials! Please configure config/credentials.json with:\n"
            "  - api_id\n"
            "  - api_hash\n"
            "  - bot_token\n"
            "  - phone\n"
            "  - whitelist (list of user IDs)"
        )
    
    return credentials


async def main():
    """Main function to run the bot and userbot."""
    print("🤖 Starting Anoward Bot...")
    
    # Load credentials
    try:
        credentials = load_credentials()
    except ValueError as e:
        print(str(e))
        return
    
    api_id = credentials['api_id']
    api_hash = credentials['api_hash']
    bot_token = credentials['bot_token']
    phone = credentials['phone']
    
    # Create bot client
    bot_client = TelegramClient('anoward_bot', api_id, api_hash)
    
    # Create userbot client
    userbot_client = TelegramClient('anoward_userbot', api_id, api_hash)
    
    # Initialize forwarding userbot
    forwarding_userbot = ForwardingUserbot(userbot_client)
    
    # ============== Bot Command Handlers ==============
    
    @bot_client.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        await cmd_start(event)
    
    @bot_client.on(events.NewMessage(pattern='/help'))
    async def help_handler(event):
        await cmd_help(event)
    
    @bot_client.on(events.NewMessage(pattern='/f'))
    async def forward_handler(event):
        try:
            await cmd_forward(event, userbot_client)
            # Refresh userbot rules after any /f command
            await forwarding_userbot.load_rules()
        except FloodWaitError as e:
            await event.respond(f"⏳ Please wait {e.seconds} seconds before trying again.")
        except Exception as e:
            await event.respond(f"😅 An error occurred: {e}")
            logger.error(f"Error in /f command: {e}")

    @bot_client.on(events.NewMessage(pattern='/bm'))
    async def bookmark_handler(event):
        try:
            await cmd_bookmark(event, userbot_client)
            # Refresh userbot bookmarks after any /bm command
            await forwarding_userbot.load_rules()
        except FloodWaitError as e:
            await event.respond(f"⏳ Please wait {e.seconds} seconds before trying again.")
        except Exception as e:
            await event.respond(f"😅 An error occurred: {e}")
            logger.error(f"Error in /bm command: {e}")

    # ============== Debug Command (for testing) ==============

    @bot_client.on(events.NewMessage(pattern='/debug'))
    async def debug_handler(event):
        """Debug command to check forwarding status."""
        if not is_whitelisted(event.sender_id):
            return
        
        debug_msg = "🔍 **Debug Info:**\n\n"
        debug_msg += f"📋 Active Rules: {len(forwarding_userbot.active_rules)}\n"
        debug_msg += f"🔍 Resolved Sources: {len(forwarding_userbot.resolved_sources)}\n"
        debug_msg += f"🎯 Event Handlers: {len(userbot_client._event_builders)}\n"
        
        if forwarding_userbot.resolved_sources:
            debug_msg += "\n**Resolved Source Chats:**\n"
            for src, chat_id in forwarding_userbot.resolved_sources.items():
                # Try to get chat info
                try:
                    info = await get_chat_display_info(bot_client, chat_id)
                    display = format_chat_id_with_title(chat_id, info)
                    debug_msg += f"├ `{src}` → {display}\n"
                except:
                    debug_msg += f"├ `{src}` → `{chat_id}`\n"
        
        if forwarding_userbot.active_rules:
            debug_msg += "\n**Active Rules:**\n"
            for rule in forwarding_userbot.active_rules:
                status = "🟢" if rule.active else "🔴"
                debug_msg += f"├ Rule `{rule.fwd_id}` {status}\n"
                debug_msg += f"│   Types: {rule.message_types}\n"
                debug_msg += f"│   Hide Forwarded: {rule.hide_forwarded}\n"
        
        await event.respond(debug_msg)
    
    # ============== Test Command (for verifying forwarding) ==============

    @bot_client.on(events.NewMessage(pattern='/test'))
    async def test_handler(event):
        """Test command to verify forwarding setup."""
        if not is_whitelisted(event.sender_id):
            return
        
        test_msg = "🧪 **Forwarding Test:**\n\n"
        
        # Check if we have active rules
        if not forwarding_userbot.active_rules:
            test_msg += "❌ No active rules found!\n"
            test_msg += "Use `/f on <fwd_id>` to activate a rule."
            await event.respond(test_msg)
            return
        
        test_msg += f"✅ Found {len(forwarding_userbot.active_rules)} active rule(s)\n\n"
        
        # Check resolved sources
        if not forwarding_userbot.resolved_sources:
            test_msg += "⚠️ Source chats not resolved yet. Sending a test message might help.\n"
        else:
            test_msg += "✅ Source chats resolved:\n"
            for src, chat_id in forwarding_userbot.resolved_sources.items():
                test_msg += f"├ `{src}` → `{chat_id}`\n"
        
        test_msg += "\n💡 **Next Steps:**\n"
        test_msg += "1. Send a message in one of the source chats\n"
        test_msg += "2. Check the console logs for forwarding activity\n"
        test_msg += "3. Look for: 📨 Received message, ✅ Matched chat, 📤 Forwarding\n"
        
        await event.respond(test_msg)
    
    # ============== Callback Query Handler ==============

    @bot_client.on(events.CallbackQuery())
    async def callback_handler(event):
        try:
            logger.debug(f"Callback query received from user {event.sender_id}")
            await handle_callback(event, forwarding_userbot, userbot_client)
        except FloodWaitError as e:
            logger.warning(f"FloodWait in callback: {e.seconds}s")
            await event.answer(f"⏳ Please wait {e.seconds} seconds.", alert=True)
        except Exception as e:
            logger.error(f"Error in callback: {e}", exc_info=True)
            await event.answer(f"😅 Error: {e}", alert=True)
    
    # ============== Start Clients ==============
    
    print("🔑 Connecting to Telegram...")
    
    # Start bot client
    await bot_client.start(bot_token=bot_token)
    print("✅ Bot client started!")

    # Get bot info
    bot_me = await bot_client.get_me()
    print(f"🤖 Logged in as: @{bot_me.username}")

    # Start userbot client
    await userbot_client.start(phone=phone)
    print("✅ Userbot client started!")

    # Get userbot info
    userbot_me = await userbot_client.get_me()
    print(f"👤 Userbot logged in as: @{userbot_me.username}")

    # Initialize forwarding userbot - load rules FIRST, then register handlers
    await forwarding_userbot.load_rules()
    
    forwarding_userbot.register_handlers()
    print(f"📋 Loaded {len(forwarding_userbot.active_rules)} active forwarding rules")
    
    # Log resolved sources for debugging
    if forwarding_userbot.resolved_sources:
        print("🔍 Resolved source chats:")
        for src, chat_id in forwarding_userbot.resolved_sources.items():
            print(f"   {src} -> {chat_id}")
    else:
        print("⚠️  No resolved source chats. Check your rule configurations!")
    
    # List all chats the userbot is in (for debugging)
    try:
        dialogs = await userbot_client.get_dialogs(limit=20)
        print(f"💬 Userbot has access to {len(dialogs)} chats. Top 10:")
        for dialog in dialogs[:10]:
            chat_type = "Channel" if dialog.is_channel else "Group" if dialog.is_group else "Private"
            print(f"   [{chat_type}] {dialog.name} ({dialog.id})")
    except Exception as e:
        print(f"⚠️  Could not list dialogs: {e}")
    
    # Check whitelist
    whitelist = credentials.get('whitelist', [])
    if not whitelist:
        print("⚠️  WARNING: Whitelist is empty! No one can use the bot.")
        print("   Add user IDs to config/credentials.json like: \"whitelist\": [123456789]")
    else:
        print(f"👥 Whitelist: {len(whitelist)} user(s) authorized")
    
    print("\n✨ Anoward Bot is now running! Press Ctrl+C to stop.")
    print("=" * 50)
    
    # Keep running until disconnected
    await bot_client.run_until_disconnected()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Stopping Anoward Bot...")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        raise
