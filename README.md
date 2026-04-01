# Instagram Discord Bot (Chromium-Based)

A Discord bot that monitors an Instagram account for new posts and automatically posts them with embeds and media to a dedicated Discord channel.

## Features

- ✅ Chromium/Puppeteer-based scraping (no instaloader dependency)
- ✅ Checks for new posts every 5 minutes
- ✅ Posts embeds with engagement metrics (likes, comments)
- ✅ Downloads and attaches media (photos/videos)
- ✅ Secure credential storage via `.env` file
- ✅ State tracking (doesn't re-post old posts)
- ✅ Full error handling and logging

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `discord.py` - Discord bot framework
- `pyppeteer` - Chromium automation (Puppeteer for Python)
- `aiohttp` - Async HTTP client for media download
- `python-dotenv` - Environment variable loading

### 2. Create `.env` File

Create a `.env` file in the same directory as `bot.py`:

```env
DISCORD_TOKEN=your_discord_bot_token_here
IG_USERNAME=your_burner_instagram_username
IG_PASSWORD=your_burner_instagram_password
```

**Get your Discord token:**
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" tab → "Add Bot"
4. Copy the token

**Use a burner Instagram account:**
- Create a dummy Instagram account with the credentials in `.env`
- The bot will use these to login and scrape posts

### 3. Update Config

Edit these variables in `bot.py`:

```python
INSTAGRAM_USERNAME = "ninevet2"      # Account to watch (no @)
CHANNEL_ID         = 1234567890      # Your Discord channel ID
POLL_INTERVAL_MINS = 5               # Check every N minutes
```

**Get your channel ID:**
1. Enable Developer Mode in Discord (Settings → Advanced → Developer Mode)
2. Right-click the channel → Copy ID

### 4. Discord Bot Permissions

Add these permissions to your bot in the Developer Portal:
- Send Messages
- Embed Links
- Attach Files
- Read Message History

### 5. Run the Bot

```bash
python bot.py
```

You should see:
```
Logged in as YourBotName (123456789)
Watching @ninevet2 every 5 min(s)
[INFO] Browser initialized
[HH:MM:SS] Checking @ninevet2…
```

## How It Works

1. **Initialization** → Bot starts, Chromium browser launches
2. **Poll Loop** → Every 5 minutes, the bot visits the Instagram profile
3. **Scrape Posts** → Extracts post IDs and metadata from the page
4. **Check State** → Compares against `last_post.json` to find new posts
5. **Fetch Details** → For each new post, loads full details (caption, likes, comments, etc.)
6. **Download Media** → Downloads the best quality image/video
7. **Create Embed** → Builds a Discord embed with all post info
8. **Send to Discord** → Posts the embed + media to the channel

## Troubleshooting

### "Browser not initialized"
- Pyppeteer needs to download Chromium on first run (may take a few minutes)
- Ensure you have internet and disk space

### "Channel not found"
- Double-check `CHANNEL_ID` is correct
- Bot must have permission to view the channel

### "Failed to fetch posts"
- Instagram may be blocking the bot
- Try adding delays or rotating user agents
- Consider using a residential proxy

### "No media downloaded"
- Instagram may have changed their page structure
- Check the browser console output for JavaScript errors

### "Can't login to Instagram"
- Ensure credentials in `.env` are correct
- Instagram may require 2FA approval
- Use a burner account without 2FA enabled

## File Structure

```
.
├── bot.py              # Main bot code
├── .env                # Credentials (keep private!)
├── requirements.txt    # Dependencies
├── last_post.json      # Tracks last seen post (auto-created)
├── ig_downloads/       # Temp media folder (auto-created)
└── README.md           # This file
```

## Security Notes

- ⚠️ **Never commit `.env` to git** - add it to `.gitignore`
- ⚠️ **Use a burner Instagram account** - not your personal account
- ⚠️ **Rotate credentials regularly**
- ⚠️ **Don't share your Discord token**

## Customization

### Change Poll Interval

```python
POLL_INTERVAL_MINS = 10  # Check every 10 minutes instead
```

### Change Embed Color

```python
embed = discord.Embed(
    color=discord.Color.from_rgb(100, 150, 200),  # Your color
)
```

### Add More Metadata to Embed

Edit the `build_embed()` function to add custom fields.

## Limitations

- Instagram actively blocks scrapers, may need proxy/rotating UA
- Media downloads may fail for stories, reels, or restricted content
- Rate limiting may occur with frequent checks
- Browser automation is slower than library-based scraping

## Alternative: Use Instaloader

If Chromium-based scraping is too slow, switch back to:

```python
import instaloader
loader = instaloader.Instaloader()
```

(The original bot.py in your uploads uses this approach)
"# ig-bot" 
