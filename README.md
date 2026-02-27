# Anoward Bot 🤖

A Telegram message forwarding bot built with Python and Telethon. Automatically forward messages from source chats to destination chats with advanced filtering and management features.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Telethon](https://img.shields.io/badge/Telethon-1.34+-orange.svg)

## ✨ Features

- 🔄 **Automatic Message Forwarding** - Set up rules to auto-forward messages between chats
- 📝 **Message Type Filtering** - Filter by Text, Photo, Video, File, Audio
- 🔖 **Bookmark System** - Create shortcuts for chat IDs using memorable titles
- ⚡ **Real-time Control** - Toggle rules on/off instantly via inline buttons
- 🎯 **Smart Chat Detection** - Automatically displays chat titles and usernames
- 📊 **Pagination** - Browse rules and bookmarks with easy navigation
- 🎨 **Beautiful UI** - Clean, emoji-rich interface with inline keyboards
- 🔒 **Whitelist Security** - Only authorized users can control the bot
- ⏳ **Flood Wait Handling** - Automatic rate limit management
- 💬 **Friendly Errors** - Clear, helpful error messages

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Telegram API credentials
- A Telegram account (for userbot)
- A Telegram Bot token

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/Anonytikus05/Anoward-Telegram-Forwarder
cd Anoward-Telegram-Forwarder
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure credentials**

Edit `config/credentials.json`:
```json
{
    "api_id": 12345678,
    "api_hash": "your_api_hash_here",
    "bot_token": "your_bot_token_here",
    "phone": "+1234567890",
    "whitelist": [123456789, 987654321]
}
```

**Getting Credentials:**
- **API ID & Hash**: Visit [my.telegram.org](https://my.telegram.org) → Login → API Development Tools
- **Bot Token**: Message [@BotFather](https://t.me/BotFather) → `/newbot` → Follow instructions
- **Phone**: Your Telegram account phone number (for userbot)
- **Whitelist**: User IDs authorized to use the bot (use [@userinfobot](https://t.me/userinfobot) to get your ID)

4. **Run the bot**
```bash
python main.py
```

## 📖 Commands

### Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Display welcome message |
| `/help` | Show complete command guide |
| `/f` | Manage forwarding rules |
| `/bm` | Manage bookmarks |
| `/debug` | Show current rules and status (whitelisted users only) |
| `/test` | Test forwarding setup (whitelisted users only) |

### Forwarding Rules (`/f`)

| Subcommand | Description | Example |
|------------|-------------|---------|
| `a <src> <dst>` | Add new forwarding rule | `/f a -100123 -100456` |
| `d <fwd_id>` | Delete rule(s) | `/f d 001` |
| `d all` | Delete ALL rules | `/f d all` |
| `on <fwd_id>` | Activate rule(s) | `/f on 001` |
| `on all` | Activate ALL rules | `/f on all` |
| `off <fwd_id>` | Deactivate rule(s) | `/f off 001` |
| `off all` | Deactivate ALL rules | `/f off all` |
| `l` | List all rules | `/f l` |
| `set <fwd_id>` | Configure rule | `/f set 001` |

### Bookmarks (`/bm`)

| Subcommand | Description | Example |
|------------|-------------|---------|
| `a <id> <title>` | Add bookmark | `/bm a -100123 my_group` |
| `d <bm_id>` | Delete bookmark(s) | `/bm d 001` |
| `d all` | Delete ALL bookmarks | `/bm d all` |
| `l` | List all bookmarks | `/bm l` |

## 💡 Usage Examples

### Create a Forwarding Rule

```bash
# Forward from one chat to another
/f a -100123456 -100789012

# Forward using usernames
/f a @source_channel @dest_group

# Forward to multiple destinations
/f a -100123 -100456,-100789

# Forward from multiple sources
/f a -100111,-100222 -100333
```

### Using Bookmarks

```bash
# Create bookmarks
/bm a -100123456 news_channel
/bm a -100789012 backup_group

# Use bookmarks in rules (use TITLE, not bm_id!)
/f a news_channel backup_group

# Create nested bookmarks
/bm a news_channel,backup_group all_dest
```

### Configure Rule Settings

```bash
# Open configuration menu
/f set 001

# Then use inline buttons to:
# - Toggle rule status (Active/Inactive)
# - Select message types to forward
# - Hide/Show "Forwarded from" tag
```

### Bulk Operations

```bash
# Activate all rules at once
/f on all

# Deactivate all rules
/f off all

# Delete all rules (careful!)
/f d all

# Delete all bookmarks
/bm d all
```

## 🔧 Configuration

### Credentials (`config/credentials.json`)

```json
{
    "api_id": 12345678,
    "api_hash": "your_api_hash_here",
    "bot_token": "bot_token_here",
    "phone": "+1234567890",
    "whitelist": [123456789, 987654321]
}
```

| Field | Description | Required |
|-------|-------------|----------|
| `api_id` | Telegram API ID | ✅ |
| `api_hash` | Telegram API Hash | ✅ |
| `bot_token` | Bot token from @BotFather | ✅ |
| `phone` | Your Telegram phone number | ✅ |
| `whitelist` | List of authorized user IDs | ✅ |

### Forwarding Rules (`config/forward.json`)

Automatically managed by the bot. Each rule contains:
- `fwd_id`: Unique 3-digit rule ID (001, 002, etc.)
- `sources`: List of source chat IDs
- `destinations`: List of destination chat IDs
- `active`: Whether rule is active (true/false)
- `message_types`: Types to forward (Text, Photo, Video, File, Audio)
- `hide_forwarded`: Hide "Forwarded from" tag (true/false)

### Bookmarks (`config/bm.json`)

Automatically managed by the bot. Each bookmark contains:
- `bm_id`: Unique 3-digit bookmark ID (001, 002, etc.)
- `title`: Bookmark title (used as alias in rules)
- `target`: Chat ID or nested bookmark reference

## ⚙️ Advanced Features

### Message Type Filtering

When configuring a rule (`/f set <fwd_id>`), you can select which message types to forward:
- **Text** - Text messages
- **Photo** - Images and photos
- **Video** - Video files
- **File** - Documents and files
- **Audio** - Voice messages and audio files

### Forwarded From Tag

Control whether the "Forwarded from" tag appears:
- **🟢 Hidden** - Messages appear as sent by userbot (no tag)
- **🔴 Visible** - Messages show original sender (with tag)

### Bookmark System

**Important**: Only bookmark **titles** can be used as aliases in rules, NOT bm_id!

```bash
# ✅ Correct - using title
/bm a -100123 my_channel
/f a my_channel @destination

# ❌ Wrong - using bm_id
/bm a -100123 my_channel
/f a 001 @destination  # This won't work!
```

### Nested Bookmarks

Bookmarks can reference other bookmarks:

```bash
# Create base bookmarks
/bm a -100111 source1
/bm a -100222 source2

# Create combined bookmark
/bm a source1,source2 all_sources

# Use in rule
/f a all_sources @destination
```

## 🔐 Security

### Whitelist

Only users in the whitelist can control the bot. Add user IDs to `config/credentials.json`:

```json
{
    "whitelist": [123456789, 987654321, 456789123]
}
```

To get your user ID, message [@userinfobot](https://t.me/userinfobot) on Telegram.

### Userbot Permissions

The userbot account must:
- Be a **member** of source chats/channels
- Have **send permissions** in destination chats/channels
- Have **read permissions** in source chats/channels

## 🐛 Troubleshooting

### Bot doesn't respond
- ✅ Check if your user ID is in the whitelist
- ✅ Verify `bot_token` is correct
- ✅ Ensure bot is not blocked by Telegram

### Forwarding doesn't work
- ✅ Ensure rule is **activated** (`/f on <fwd_id>`)
- ✅ Userbot must be a **member** of source chat
- ✅ Userbot must have **send permissions** in destination chat
- ✅ Check chat IDs are correct (use `/debug` to verify)

### Chat titles not showing
- ✅ Userbot must be a member of the chat
- ✅ This is normal for private chats where userbot isn't a member

### FloodWait errors
- ⏳ Wait the specified time before trying again
- 🤖 The bot handles this automatically

### "Rule not found" error
- ✅ Check rule ID format (3 digits: 001, 002, etc.)
- ✅ Use `/f l` to list all rules and verify IDs

## 📝 Notes

1. **Userbot Required**: This bot uses a userbot (your personal account) to forward messages. The bot itself only handles commands.

2. **Rate Limits**: Telegram has messaging rate limits. The bot handles FloodWait automatically, but avoid creating excessive rules.

3. **Privacy**: Respect message privacy and Telegram's Terms of Service when forwarding messages.

4. **Backup**: Regularly backup your `config/` folder to preserve rules and settings.

## 🙏 Acknowledgments

- [Telethon](https://github.com/LonamiWebs/Telethon) - Amazing Telegram MTProto library
- [Telegram](https://telegram.org) - For the awesome messaging platform
- All contributors and supporters

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Contact the developer

## 🌟 Show Your Support

If you like this project, please ⭐ star this repository!

---

**Made with AI by Anonytikus05**
