"""Bot command handlers for /start, /help, /f, and /bm commands."""

import re
import logging
import asyncio
from typing import List, Tuple
from telethon import events, Button
from telethon.tl.custom.message import Message

from utils.forward_manager import forward_manager, ForwardRule
from utils.bookmark_manager import bookmark_manager
from utils.config_manager import config_manager
from utils.error_handler import fuzzy_match, suggest_correction
from utils.chat_info import get_chat_display_info, format_chat_id_with_title

logger = logging.getLogger(__name__)


# Pagination settings
ITEMS_PER_PAGE = 5


def is_whitelisted(user_id: int) -> bool:
    """Check if user is in whitelist."""
    credentials = config_manager.get_credentials()
    whitelist = credentials.get("whitelist", [])
    return user_id in whitelist


def check_whitelist(func):
    """Decorator to check if user is whitelisted."""
    async def wrapper(event: events.NewMessage.Event):
        if not is_whitelisted(event.sender_id):
            await event.respond(
                "⛔ Sorry, you are not in the whitelist to use this bot! "
                "Please contact the admin to be added. 🔒"
            )
            return
        return await func(event)
    return wrapper


async def send_paginated_list(
    event: events.NewMessage.Event,
    items: List[dict],
    item_formatter,
    title: str,
    callback_prefix: str,
    page: int = 1
):
    """Send a paginated list with inline navigation buttons."""
    total_pages = max(1, (len(items) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_items = items[start_idx:end_idx]

    message = f"{title}\n\n"

    if not page_items:
        message += "📭 No items found!"
    else:
        # Support both sync and async formatters
        if asyncio.iscoroutinefunction(item_formatter):
            for i, item in enumerate(page_items, start=start_idx + 1):
                message += await item_formatter(item, i)
        else:
            for i, item in enumerate(page_items, start=start_idx + 1):
                message += item_formatter(item, i)

    # Build navigation buttons
    buttons = []
    nav_row = []

    if page > 1:
        nav_row.append(Button.inline("◀️ Previous", f"{callback_prefix}_prev_{page - 1}"))

    if page < total_pages:
        nav_row.append(Button.inline("Next ▶️", f"{callback_prefix}_next_{page + 1}"))

    if nav_row:
        buttons.append(nav_row)

    buttons.append([Button.inline("❌ Close", f"{callback_prefix}_close")])

    if page_items:
        message += f"\n📄 Page {page}/{total_pages}"

    return message, buttons


# ============== /start command ==============

@check_whitelist
async def cmd_start(event: events.NewMessage.Event):
    """Handle /start command."""
    welcome_message = (
        "👋 **Welcome to Anoward Bot!** 🤖\n\n"
        "I'm a powerful message forwarding bot that helps you automatically forward "
        "messages from one chat to another. Here's what I can do:\n\n"
        "📌 **Features:**\n"
        "• Create forwarding rules to auto-forward messages\n"
        "• Manage multiple source and destination chats\n"
        "• Filter messages by type (Text, Photo, Video, File, Audio)\n"
        "• Use bookmarks for easy chat ID management\n"
        "• Control which rules are active or inactive\n"
        "• Hide 'Forwarded from' tags when forwarding\n\n"
        "💡 **Quick Start:**\n"
        "• Use /help to see all available commands\n"
        "• Use /f a <src> <dst> to create a forwarding rule\n"
        "• Use /bm a <id> <title> to create a bookmark\n\n"
        "✨ Need help? Just use /help anytime!"
    )
    await event.respond(welcome_message)


# ============== /help command ==============

@check_whitelist
async def cmd_help(event: events.NewMessage.Event):
    """Handle /help command."""
    help_message = (
        "📚 **Anoward Bot - Complete Guide**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔄 **FORWARDING COMMANDS** (`/f`)\n\n"
        "➕ **Add Rule:** `/f a <src> <dst>`\n"
        "   Create a new forwarding rule\n"
        "   • Src/Dst: Chat ID, username, or bookmark title\n"
        "   • Multiple IDs: separate with `,`\n"
        "   • Example: `/f a -100123 @destination`\n"
        "   • With bookmark: `/f a my_source bm_dest`\n\n"
        "🗑️ **Delete Rule:** `/f d <fwd_id>`\n"
        "   Remove forwarding rule(s)\n"
        "   • Example: `/f d 001`\n"
        "   • Multiple: `/f d 001,002`\n"
        "   • **Delete all:** `/f d all`\n\n"
        "✅ **Activate Rule:** `/f on <fwd_id>`\n"
        "   Start forwarding messages\n"
        "   • Example: `/f on 001`\n"
        "   • **Activate all:** `/f on all`\n\n"
        "⏸️ **Deactivate Rule:** `/f off <fwd_id>`\n"
        "   Stop forwarding messages\n"
        "   • Example: `/f off 001`\n"
        "   • **Deactivate all:** `/f off all`\n\n"
        "📋 **List Rules:** `/f l`\n"
        "   View all rules with pagination\n\n"
        "⚙️ **Configure Rule:** `/f set <fwd_id>`\n"
        "   Open interactive settings:\n"
        "   • Toggle rule status (Active/Inactive)\n"
        "   • Select message types (Text, Photo, etc.)\n"
        "   • Hide 'Forwarded from' tag\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔖 **BOOKMARK COMMANDS** (`/bm`)\n\n"
        "➕ **Add Bookmark:** `/bm a <id> <title>`\n"
        "   Create a shortcut for chat IDs\n"
        "   • Example: `/bm a -100123 my_group`\n"
        "   • Use title in rules: `/f a my_group @dest`\n"
        "   • ⚠️ Only **title** works as alias, NOT bm_id!\n"
        "   • Nested: `/bm a bm1,bm2 combined_bm`\n\n"
        "🗑️ **Delete Bookmark:** `/bm d <bm_id>`\n"
        "   Remove bookmark(s)\n"
        "   • Example: `/bm d 001`\n"
        "   • Multiple: `/bm d 001,002`\n"
        "   • **Delete all:** `/bm d all`\n\n"
        "📋 **List Bookmarks:** `/bm l`\n"
        "   View all bookmarks with pagination\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 **PRO TIPS:**\n"
        "• Chat IDs: `-100` prefix for channels/supergroups\n"
        "• Usernames: Start with `@` (e.g., `@username`)\n"
        "• Bookmarks: Use **titles** as aliases in rules\n"
        "• Multiple IDs: Use comma separator (e.g., `id1,id2`)\n"
        "• Rule IDs: 3-digit format (`001`, `002`, etc.)\n"
        "• Use `all` parameter to affect all items at once\n\n"
        "🔧 **DEBUG COMMANDS:**\n"
        "• `/debug` - Show current rules and status\n"
        "• `/test` - Test forwarding setup\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    await event.respond(help_message)


# ============== /f command ==============

@check_whitelist
async def cmd_forward(event: events.NewMessage.Event, userbot_client=None):
    """Handle /f command."""
    args = event.message.text.split()[1:]  # Skip '/f'

    if not args:
        await event.respond(
            "❓ Please specify a subcommand!\n\n"
            "Available: `a`, `d`, `on`, `off`, `l`, `set`\n"
            "Use /help for more details. 📚"
        )
        return

    subcommand = args[0].lower()

    if subcommand == "a":
        await handle_forward_add(event, args[1:])
    elif subcommand == "d":
        await handle_forward_delete(event, args[1:])
    elif subcommand == "on":
        await handle_forward_toggle(event, args[1:], active=True)
    elif subcommand == "off":
        await handle_forward_toggle(event, args[1:], active=False)
    elif subcommand == "l":
        await handle_forward_list(event, userbot_client)
    elif subcommand == "set":
        await handle_forward_set(event, args[1:], userbot_client)
    else:
        await event.respond(
            f"❓ Unknown subcommand: `{subcommand}`\n\n"
            "Available: `a`, `d`, `on`, `off`, `l`, `set`\n"
            "Use /help for more details. 📚"
        )


async def handle_forward_add(event: events.NewMessage.Event, args: List[str]):
    """Handle /f a - Add new forwarding rule."""
    if len(args) < 2:
        await event.respond(
            "❌ Not enough arguments!\n\n"
            "Usage: `/f a <src_id> <dst_id>`\n"
            "Example: `/f a -100123 -100456`\n"
            "You can use bookmarks too: `/f a bm1 bm2`"
        )
        return

    # Handle multiple sources and destinations
    # Sources come first, destinations come after
    src_ids = args[0].split(',')
    dst_ids = args[1].split(',')

    # Resolve bookmarks
    bookmarks = bookmark_manager.get_bookmark_dict()
    all_bookmarks = bookmark_manager.get_all_bookmarks()
    all_bookmark_titles = [bm.title for bm in all_bookmarks]
    
    resolved_sources = []
    resolved_destinations = []
    unresolved = []

    for src in src_ids:
        src = src.strip()
        resolved = forward_manager.resolve_id(src, bookmarks)
        if resolved:
            resolved_sources.extend(resolved)
        else:
            unresolved.append(src)

    for dst in dst_ids:
        dst = dst.strip()
        resolved = forward_manager.resolve_id(dst, bookmarks)
        if resolved:
            resolved_destinations.extend(resolved)
        else:
            unresolved.append(dst)

    # Handle unresolved IDs with fuzzy matching suggestions
    if unresolved:
        error_msg = "⚠️ Could not resolve the following IDs:\n\n"
        for unres in unresolved:
            error_msg += f"• `{unres}`\n"
        
        # Try fuzzy matching for each unresolved ID
        suggestions = []
        for unres in unresolved:
            matches = fuzzy_match(unres, all_bookmark_titles)
            if matches:
                suggestions.append(suggest_correction(unres, matches))
        
        if suggestions:
            error_msg += "\n" + "\n".join(suggestions)
        
        error_msg += "\n\nPlease check the IDs and try again!"
        await event.respond(error_msg)
        return

    if not resolved_sources or not resolved_destinations:
        await event.respond("❌ Could not resolve any valid source or destination IDs!")
        return

    rule = forward_manager.add_rule(resolved_sources, resolved_destinations)

    if rule:
        await event.respond(
            f"✅ **Forwarding Rule Created!** 🎉\n\n"
            f"🆔 **Rule ID:** `{rule.fwd_id}`\n"
            f"📤 **Sources:** {', '.join(f'`{s}`' for s in rule.sources)}\n"
            f"📥 **Destinations:** {', '.join(f'`{d}`' for d in rule.destinations)}\n"
            f"⚡ **Status:** Inactive (use `/f on {rule.fwd_id}` to activate)\n\n"
            "💡 Use `/f set {rule.fwd_id}` to configure message types and options!"
        )
    else:
        await event.respond("❌ Failed to create forwarding rule. Please try again.")


async def handle_forward_delete(event: events.NewMessage.Event, args: List[str]):
    """Handle /f d - Delete forwarding rule(s)."""
    if not args:
        await event.respond(
            "❌ Please specify the rule ID(s) to delete!\n"
            "Usage: `/f d <fwd_id>` or `/f d 001,002` or `/f d all`"
        )
        return
    
    # Check for 'all' parameter
    if 'all' in [a.lower() for a in args]:
        # Delete all rules
        rules = forward_manager.get_all_rules()
        if not rules:
            await event.respond("📭 No rules to delete!")
            return
        fwd_ids = [r.fwd_id for r in rules]
        confirm_msg = (
            f"⚠️ **Confirm Delete All Rules**\n\n"
            f"You are about to delete **{len(fwd_ids)} rule(s)**:\n"
            f"{', '.join(f'`{fid}`' for fid in fwd_ids)}\n\n"
            f"Reply `/f d all` again to confirm."
        )
        # Simple confirmation - just delete
        if forward_manager.delete_rule(fwd_ids):
            await event.respond(
                f"✅ **All Forwarding Rules Deleted!** 🗑️\n\n"
                f"Deleted {len(fwd_ids)} rule(s): {', '.join(f'`{fid}`' for fid in fwd_ids)}"
            )
        return
    
    fwd_ids = [fid.strip() for fid in ','.join(args).split(',')]

    if forward_manager.delete_rule(fwd_ids):
        await event.respond(
            f"✅ **Forwarding Rule(s) Deleted!** 🗑️\n\n"
            f"Deleted: {', '.join(f'`{fid}`' for fid in fwd_ids)}"
        )
    else:
        await event.respond(
            "❌ No matching forwarding rules found.\n"
            "Please check the rule IDs and try again."
        )


async def handle_forward_toggle(event: events.NewMessage.Event, args: List[str], active: bool):
    """Handle /f on and /f off - Toggle forwarding rule(s)."""
    if not args:
        status = "activate" if active else "deactivate"
        await event.respond(
            f"❌ Please specify the rule ID(s) to {status}!\n"
            f"Usage: `/f {'on' if active else 'off'} <fwd_id>` or `/f {'on' if active else 'off'} all`"
        )
        return
    
    # Check for 'all' parameter
    if 'all' in [a.lower() for a in args]:
        # Toggle all rules
        rules = forward_manager.get_all_rules()
        if not rules:
            await event.respond(f"📭 No rules to {'activate' if active else 'deactivate'}!")
            return
        fwd_ids = [r.fwd_id for r in rules]
    else:
        fwd_ids = [fid.strip() for fid in ','.join(args).split(',')]
    
    status_text = "activated" if active else "deactivated"
    emoji = "🟢" if active else "🔴"
    action_word = "Activating" if active else "Deactivating"

    if forward_manager.set_rule_active(fwd_ids, active):
        await event.respond(
            f"✅ **Forwarding Rule(s) {status_text.title()}!** {emoji}\n\n"
            f"{action_word}: {', '.join(f'`{fid}`' for fid in fwd_ids)}"
        )
    else:
        await event.respond(
            "❌ No matching forwarding rules found.\n"
            "Please check the rule IDs and try again."
        )


async def handle_forward_list(event: events.NewMessage.Event, userbot_client=None):
    """Handle /f l - List all forwarding rules with pagination."""
    rules = forward_manager.get_all_rules()
    
    # Use userbot client for chat info lookup (bot may not be in all chats)
    client_for_info = userbot_client or event.client

    async def format_rule(rule: dict, index: int) -> str:
        fwd_id = rule.get("fwd_id", "???")
        sources = rule.get("sources", [])
        destinations = rule.get("destinations", [])
        active = rule.get("active", False)
        message_types = rule.get("message_types", [])

        status_emoji = "🟢" if active else "🔴"
        status_text = "Active" if active else "Inactive"
        
        # Format sources with titles
        source_strs = []
        for s in sources[:3]:
            try:
                if s.startswith('@'):
                    source_strs.append(f"`{s}`")
                elif s.lstrip('-').isdigit():
                    chat_id = int(s)
                    info = await get_chat_display_info(client_for_info, chat_id)
                    source_strs.append(format_chat_id_with_title(chat_id, info))
                else:
                    # It's a bookmark title
                    source_strs.append(f"🔖 `{s}`")
            except:
                source_strs.append(f"`{s}`")
        
        # Format destinations with titles
        dest_strs = []
        for d in destinations[:3]:
            try:
                if d.startswith('@'):
                    dest_strs.append(f"`{d}`")
                elif d.lstrip('-').isdigit():
                    chat_id = int(d)
                    info = await get_chat_display_info(client_for_info, chat_id)
                    dest_strs.append(format_chat_id_with_title(chat_id, info))
                else:
                    # It's a bookmark title
                    dest_strs.append(f"🔖 `{d}`")
            except:
                dest_strs.append(f"`{d}`")
        
        sources_display = ', '.join(source_strs)
        if len(sources) > 3:
            sources_display += f" (+{len(sources)-3})"
            
        dests_display = ', '.join(dest_strs)
        if len(destinations) > 3:
            dests_display += f" (+{len(destinations)-3})"

        return (
            f"**#{index} - Rule `{fwd_id}`** {status_emoji}\n"
            f"├ Status: {status_text}\n"
            f"├ Types: {', '.join(message_types[:3])}{'...' if len(message_types) > 3 else ''}\n"
            f"├ From: {sources_display}\n"
            f"└ To: {dests_display}\n\n"
        )

    title = "📋 **Your Forwarding Rules:**\n\n"
    message, buttons = await send_paginated_list(
        event,
        [r.to_dict() for r in rules],
        format_rule,
        title,
        "fwd_list"
    )

    await event.respond(message, buttons=buttons)


async def handle_forward_set(event: events.NewMessage.Event, args: List[str], userbot_client=None):
    """Handle /f set - Configure forwarding rule."""
    if not args:
        await event.respond(
            "❌ Please specify the rule ID to configure!\n"
            "Usage: `/f set <fwd_id>`"
        )
        return

    fwd_id = args[0].strip()
    rule = forward_manager.get_rule(fwd_id)

    if not rule:
        await event.respond(
            f"❌ Forwarding rule `{fwd_id}` not found!\n"
            "Please check the rule ID and try again."
        )
        return

    # Use userbot client for chat info lookup (bot may not be in all chats)
    client_for_info = userbot_client or event.client
    
    # Format sources with titles
    source_strs = []
    for s in rule.sources:
        if s.startswith('@'):
            source_strs.append(f"`{s}`")
        elif s.lstrip('-').isdigit():
            try:
                chat_id = int(s)
                info = await get_chat_display_info(client_for_info, chat_id)
                source_strs.append(format_chat_id_with_title(chat_id, info))
            except:
                source_strs.append(f"`{s}`")
        else:
            # Bookmark title
            source_strs.append(f"🔖 `{s}`")
    
    # Format destinations with titles
    dest_strs = []
    for d in rule.destinations:
        if d.startswith('@'):
            dest_strs.append(f"`{d}`")
        elif d.lstrip('-').isdigit():
            try:
                chat_id = int(d)
                info = await get_chat_display_info(client_for_info, chat_id)
                dest_strs.append(format_chat_id_with_title(chat_id, info))
            except:
                dest_strs.append(f"`{d}`")
        else:
            # Bookmark title
            dest_strs.append(f"🔖 `{d}`")

    # Build inline keyboard for configuration
    message_types = rule.message_types
    all_types = ["Text", "Photo", "Video", "File", "Audio"]

    type_buttons = []
    for mt in all_types:
        is_active = mt in message_types
        emoji = "🟢" if is_active else "🔴"
        type_buttons.append(Button.inline(f"{mt} {emoji}", f"fwd_cfg_type_{fwd_id}_{mt}"))

    # Group buttons in rows of 2
    type_rows = [type_buttons[i:i+2] for i in range(0, len(type_buttons), 2)]

    fwd_emoji = "🟢" if rule.hide_forwarded else "🔴"
    status_emoji = "🟢" if rule.active else "🔴"
    status_text = "Active" if rule.active else "Inactive"

    buttons = [
        [Button.inline(f"⚡ Status: {status_text} {status_emoji}", f"fwd_cfg_status_{fwd_id}")],
        [Button.inline("📝 MessageType", "")],  # Header
        *type_rows,
        [Button.inline(f"🔄 ForwardedFrom {fwd_emoji}", f"fwd_cfg_fwdtag_{fwd_id}")],
        [Button.inline("❌ CLOSE", f"fwd_cfg_close_{fwd_id}")]
    ]

    config_message = (
        f"⚙️ **Configure Forwarding Rule `{fwd_id}`**\n\n"
        f"📤 **Sources:**\n{chr(10).join(f'   ├ {s}' for s in source_strs)}\n\n"
        f"📥 **Destinations:**\n{chr(10).join(f'   ├ {d}' for d in dest_strs)}\n\n"
        f"**Rule Status:** {status_text} {status_emoji}\n"
        f"Click the status button above to toggle\n\n"
        f"**Message Types to Forward:**\n"
        f"(Click to toggle)\n\n"
        f"**Forwarded From Tag:**\n"
        f"🟢 = Hidden (no 'Forwarded from' tag)\n"
        f"🔴 = Visible (shows 'Forwarded from' tag)"
    )

    await event.respond(config_message, buttons=buttons)


# ============== /bm command ==============

@check_whitelist
async def cmd_bookmark(event: events.NewMessage.Event, userbot_client=None):
    """Handle /bm command."""
    args = event.message.text.split()[1:]  # Skip '/bm'

    if not args:
        await event.respond(
            "❓ Please specify a subcommand!\n\n"
            "Available: `a`, `d`, `l`\n"
            "Use /help for more details. 📚"
        )
        return

    subcommand = args[0].lower()

    if subcommand == "a":
        await handle_bookmark_add(event, args[1:])
    elif subcommand == "d":
        await handle_bookmark_delete(event, args[1:])
    elif subcommand == "l":
        await handle_bookmark_list(event, userbot_client)
    else:
        await event.respond(
            f"❓ Unknown subcommand: `{subcommand}`\n\n"
            "Available: `a`, `d`, `l`\n"
            "Use /help for more details. 📚"
        )


async def handle_bookmark_add(event: events.NewMessage.Event, args: List[str]):
    """Handle /bm a - Add new bookmark."""
    if len(args) < 2:
        await event.respond(
            "❌ Not enough arguments!\n\n"
            "Usage: `/bm a <id> <title>`\n"
            "Example: `/bm a -100123 bm1`"
        )
        return
    
    target = args[0]
    title = args[1]
    
    # Check for nested bookmarks
    bookmarks = bookmark_manager.get_bookmark_dict()
    target_parts = target.split(',')
    resolved_targets = []
    
    for part in target_parts:
        part = part.strip()
        if part in bookmarks:
            # It's a bookmark reference
            resolved_targets.append(part)
        else:
            resolved_targets.append(part)
    
    final_target = ','.join(resolved_targets)
    
    bookmark = bookmark_manager.add_bookmark(final_target, title)
    
    await event.respond(
        f"✅ **Bookmark Created!** 🔖\n\n"
        f"🆔 **Bookmark ID:** `{bookmark.bm_id}`\n"
        f"📝 **Title:** {bookmark.title}\n"
        f"🎯 **Target:** `{bookmark.target}`\n\n"
        f"💡 Now you can use `{bookmark.bm_id}` or `{bookmark.title}` "
        f"instead of the full ID in forwarding rules!"
    )


async def handle_bookmark_delete(event: events.NewMessage.Event, args: List[str]):
    """Handle /bm d - Delete bookmark(s)."""
    if not args:
        await event.respond(
            "❌ Please specify the bookmark ID(s) to delete!\n"
            "Usage: `/bm d <bm_id>` or `/bm d 001,002` or `/bm d all`"
        )
        return
    
    # Check for 'all' parameter
    if 'all' in [a.lower() for a in args]:
        # Delete all bookmarks
        bookmarks = bookmark_manager.get_all_bookmarks()
        if not bookmarks:
            await event.respond("📭 No bookmarks to delete!")
            return
        bm_ids = [b.bm_id for b in bookmarks]
        if bookmark_manager.delete_bookmark(bm_ids):
            await event.respond(
                f"✅ **All Bookmarks Deleted!** 🗑️\n\n"
                f"Deleted {len(bm_ids)} bookmark(s): {', '.join(f'`{bid}`' for bid in bm_ids)}"
            )
        return
    
    bm_ids = [bid.strip() for bid in ','.join(args).split(',')]

    if bookmark_manager.delete_bookmark(bm_ids):
        await event.respond(
            f"✅ **Bookmark(s) Deleted!** 🗑️\n\n"
            f"Deleted: {', '.join(f'`{bid}`' for bid in bm_ids)}"
        )
    else:
        await event.respond(
            "❌ No matching bookmarks found.\n"
            "Please check the bookmark IDs and try again."
        )


async def handle_bookmark_list(event: events.NewMessage.Event, userbot_client=None):
    """Handle /bm l - List all bookmarks with pagination."""
    bookmarks = bookmark_manager.get_all_bookmarks()
    
    # Use userbot client for chat info lookup (bot may not be in all chats)
    client_for_info = userbot_client or event.client

    async def format_bookmark(bm: dict, index: int) -> str:
        bm_id = bm.get("bm_id", "???")
        title = bm.get("title", "???")
        target = bm.get("target", "???")
        
        # Try to resolve target display
        target_display = target
        if target.lstrip('-').isdigit():
            try:
                chat_id = int(target)
                info = await get_chat_display_info(client_for_info, chat_id)
                target_display = format_chat_id_with_title(chat_id, info)
            except:
                pass

        return (
            f"**#{index} - Bookmark `{bm_id}`** 🔖\n"
            f"├ Title: `{title}`\n"
            f"└ Target: {target_display}\n\n"
        )

    title = "📑 **Your Bookmarks:**\n\n"
    message, buttons = await send_paginated_list(
        event,
        [b.to_dict() for b in bookmarks],
        format_bookmark,
        title,
        "bm_list"
    )

    await event.respond(message, buttons=buttons)


# ============== Callback Query Handlers ==============

async def handle_callback(event, forwarding_userbot=None, userbot_client=None):
    """Handle all callback queries from inline buttons."""
    data = event.data.decode('utf-8')
    logger.info(f"🔘 Callback received: {data}")
    
    try:
        # Forward list pagination
        if data.startswith("fwd_list_"):
            await handle_forward_list_callback(event, data, userbot_client)
        # Bookmark list pagination
        elif data.startswith("bm_list_"):
            await handle_bookmark_list_callback(event, data, userbot_client)
        # Forward rule configuration
        elif data.startswith("fwd_cfg_"):
            await handle_forward_config_callback(event, data, forwarding_userbot, userbot_client)
        else:
            logger.warning(f"Unknown callback: {data}")
            await event.answer("❓ Unknown action", alert=True)
    except Exception as e:
        logger.error(f"Error handling callback '{data}': {e}", exc_info=True)
        await event.answer(f"❌ Error: {e}", alert=True)
        raise


async def handle_forward_list_callback(event, data: str, userbot_client=None):
    """Handle forward list pagination callbacks."""
    parts = data.split('_')
    action = parts[2]

    # Get current page from the message
    # We need to re-fetch the rules and determine the page
    rules = forward_manager.get_all_rules()
    rules_data = [r.to_dict() for r in rules]
    total_pages = max(1, (len(rules_data) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

    # Extract current page from original message if possible
    # For simplicity, we'll start from page 1 on navigation
    page = 1
    if action in ["next", "prev"]:
        page = int(parts[3])
    
    # Use userbot client for chat info
    client_for_info = userbot_client or event.client

    async def format_rule(rule: dict, index: int) -> str:
        fwd_id = rule.get("fwd_id", "???")
        sources = rule.get("sources", [])
        destinations = rule.get("destinations", [])
        active = rule.get("active", False)

        status_emoji = "🟢" if active else "🔴"
        status_text = "Active" if active else "Inactive"

        return (
            f"**#{index} - Rule `{fwd_id}`** {status_emoji}\n"
            f"├ Status: {status_text}\n"
            f"├ Sources: {', '.join(f'`{s}`' for s in sources[:3])}"
            f"{'...' if len(sources) > 3 else ''}\n"
            f"└ Destinations: {', '.join(f'`{d}`' for d in destinations[:3])}"
            f"{'...' if len(destinations) > 3 else ''}\n\n"
        )

    title = "📋 **Your Forwarding Rules:**\n\n"
    message, buttons = await send_paginated_list(
        event,
        rules_data,
        format_rule,
        title,
        "fwd_list",
        page
    )

    await event.edit(message, buttons=buttons)


async def handle_bookmark_list_callback(event, data: str):
    """Handle bookmark list pagination callbacks."""
    parts = data.split('_')
    action = parts[2]
    
    bookmarks = bookmark_manager.get_all_bookmarks()
    bookmarks_data = [b.to_dict() for b in bookmarks]
    total_pages = max(1, (len(bookmarks_data) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    
    page = 1
    if action in ["next", "prev"]:
        page = int(parts[3])
    
    def format_bookmark(bm: dict, index: int) -> str:
        bm_id = bm.get("bm_id", "???")
        title = bm.get("title", "???")
        target = bm.get("target", "???")
        
        return (
            f"**#{index} - Bookmark `{bm_id}`** 🔖\n"
            f"├ Title: `{title}`\n"
            f"└ Target: `{target}`\n\n"
        )
    
    title = "📑 **Your Bookmarks:**\n\n"
    message, buttons = await send_paginated_list(
        event,
        bookmarks_data,
        format_bookmark,
        title,
        "bm_list",
        page
    )
    
    await event.edit(message, buttons=buttons)


async def handle_forward_config_callback(event, data: str, forwarding_userbot=None):
    """Handle forward rule configuration callbacks."""
    parts = data.split('_')
    # fwd_cfg_type_<fwd_id>_<msg_type> or fwd_cfg_fwdtag_<fwd_id> or fwd_cfg_status_<fwd_id> or fwd_cfg_close_<fwd_id>

    logger.info(f"🔧 Config callback parts: {parts}")
    
    if len(parts) < 4:
        logger.error(f"Invalid callback data: {data}")
        await event.answer("❌ Invalid configuration request!", alert=True)
        return

    action = parts[2]
    fwd_id = parts[3]

    logger.info(f"🔧 Action: {action}, Fwd ID: {fwd_id}")

    if action == "type":
        # Toggle message type - reload rule first to get fresh data
        rule = forward_manager.get_rule(fwd_id)
        if not rule:
            logger.error(f"Rule not found: {fwd_id}")
            await event.answer("❌ Rule not found!", alert=True)
            return
            
        msg_type = parts[4] if len(parts) > 4 else None
        if msg_type:
            message_types = rule.message_types.copy()
            if msg_type in message_types:
                message_types.remove(msg_type)
                logger.info(f"🔧 Disabled message type: {msg_type}")
            else:
                message_types.append(msg_type)
                logger.info(f"🔧 Enabled message type: {msg_type}")

            # Ensure at least one type is selected
            if not message_types:
                await event.answer("⚠️ At least one message type must be selected!", alert=True)
                return

            forward_manager.update_rule_config(fwd_id, message_types=message_types)
            await event.answer(f"✅ {msg_type} {'enabled' if msg_type in message_types else 'disabled'}!")

    elif action == "fwdtag":
        # Toggle hide_forwarded - reload rule first to get fresh data
        rule = forward_manager.get_rule(fwd_id)
        if not rule:
            logger.error(f"Rule not found: {fwd_id}")
            await event.answer("❌ Rule not found!", alert=True)
            return
            
        # Toggle hide_forwarded
        new_value = not rule.hide_forwarded
        forward_manager.update_rule_config(fwd_id, hide_forwarded=new_value)
        logger.info(f"🔧 Toggled hide_forwarded to: {new_value}")
        await event.answer(f"✅ ForwardedFrom tag {'hidden' if new_value else 'visible'}!")

    elif action == "status":
        # Toggle rule active status - reload rule first to get fresh data
        rule = forward_manager.get_rule(fwd_id)
        if not rule:
            logger.error(f"Rule not found: {fwd_id}")
            await event.answer("❌ Rule not found!", alert=True)
            return
            
        # Toggle rule active status
        new_value = not rule.active
        logger.info(f"🔧 Toggled rule status from {rule.active} to {new_value}")
        forward_manager.set_rule_active([fwd_id], new_value)
        status_text = "activated" if new_value else "deactivated"
        emoji = "🟢" if new_value else "🔴"
        await event.answer(f"✅ Rule {status_text}! {emoji}")

    elif action == "close":
        logger.info(f"🔧 Closing config menu for rule {fwd_id}")
        await event.delete()
        return

    # Small delay to ensure JSON is saved
    await asyncio.sleep(0.2)
    
    # CRITICAL: Reload userbot rules if forwarding_userbot is provided
    if forwarding_userbot:
        logger.info(f"🔧 Refreshing userbot rules after config change")
        await forwarding_userbot.load_rules()
    
    # CRITICAL: Reload rule from JSON to get fresh data for display
    logger.info(f"🔧 Reloading rule {fwd_id} from JSON for display refresh")
    await handle_forward_set_original(event, fwd_id, userbot_client)


async def handle_forward_set_original(event, fwd_id: str, userbot_client=None):
    """Re-send the forward configuration message after update."""
    # Reload rule from JSON to get fresh data
    rule = forward_manager.get_rule(fwd_id)
    if not rule:
        logger.error(f"Rule not found in refresh: {fwd_id}")
        return

    logger.info(f"🔄 Refreshing config display for rule {fwd_id}: active={rule.active}, hide_forwarded={rule.hide_forwarded}, types={rule.message_types}")
    
    # Use userbot client for chat info lookup (bot may not be in all chats)
    client_for_info = userbot_client or event.client
    
    # Format sources with titles
    source_strs = []
    for s in rule.sources:
        if s.startswith('@'):
            source_strs.append(f"`{s}`")
        elif s.lstrip('-').isdigit():
            try:
                chat_id = int(s)
                info = await get_chat_display_info(client_for_info, chat_id)
                source_strs.append(format_chat_id_with_title(chat_id, info))
            except:
                source_strs.append(f"`{s}`")
        else:
            # Bookmark title
            source_strs.append(f"🔖 `{s}`")
    
    # Format destinations with titles
    dest_strs = []
    for d in rule.destinations:
        if d.startswith('@'):
            dest_strs.append(f"`{d}`")
        elif d.lstrip('-').isdigit():
            try:
                chat_id = int(d)
                info = await get_chat_display_info(client_for_info, chat_id)
                dest_strs.append(format_chat_id_with_title(chat_id, info))
            except:
                dest_strs.append(f"`{d}`")
        else:
            # Bookmark title
            dest_strs.append(f"🔖 `{d}`")

    message_types = rule.message_types
    all_types = ["Text", "Photo", "Video", "File", "Audio"]

    type_buttons = []
    for mt in all_types:
        is_active = mt in message_types
        emoji = "🟢" if is_active else "🔴"
        type_buttons.append(Button.inline(f"{mt} {emoji}", f"fwd_cfg_type_{fwd_id}_{mt}"))

    type_rows = [type_buttons[i:i+2] for i in range(0, len(type_buttons), 2)]

    fwd_emoji = "🟢" if rule.hide_forwarded else "🔴"
    status_emoji = "🟢" if rule.active else "🔴"
    status_text = "Active" if rule.active else "Inactive"

    buttons = [
        [Button.inline(f"⚡ Status: {status_text} {status_emoji}", f"fwd_cfg_status_{fwd_id}")],
        [Button.inline("📝 MessageType", "")],
        *type_rows,
        [Button.inline(f"🔄 ForwardedFrom {fwd_emoji}", f"fwd_cfg_fwdtag_{fwd_id}")],
        [Button.inline("❌ CLOSE", f"fwd_cfg_close_{fwd_id}")]
    ]

    config_message = (
        f"⚙️ **Configure Forwarding Rule `{fwd_id}`**\n\n"
        f"📤 **Sources:**\n{chr(10).join(f'   ├ {s}' for s in source_strs)}\n\n"
        f"📥 **Destinations:**\n{chr(10).join(f'   ├ {d}' for d in dest_strs)}\n\n"
        f"**Rule Status:** {status_text} {status_emoji}\n"
        f"Click the status button above to toggle\n\n"
        f"**Message Types to Forward:**\n"
        f"(Click to toggle)\n\n"
        f"**Forwarded From Tag:**\n"
        f"🟢 = Hidden (no 'Forwarded from' tag)\n"
        f"🔴 = Visible (shows 'Forwarded from' tag)"
    )

    try:
        logger.info(f"🔄 Editing message for rule {fwd_id}")
        await event.edit(config_message, buttons=buttons)
    except Exception as e:
        logger.warning(f"Edit failed, sending new message: {e}")
        try:
            await event.respond(config_message, buttons=buttons)
        except Exception as e2:
            logger.error(f"Failed to send new message: {e2}")
