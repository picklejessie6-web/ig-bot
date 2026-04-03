from dotenv import load_dotenv
load_dotenv()
import discord
from discord.ext import commands, tasks
import os
import sys
import json
import asyncio
import httpx
from datetime import datetime, timezone
from pathlib import Path
from instagrapi import Client
from instagrapi.exceptions import LoginRequired

os.environ["PYTHONUNBUFFERED"] = "1"

# ── CONFIG ────────────────────────────────────────────────────────────────────
DISCORD_TOKEN      = os.environ["DISCORD_TOKEN"]
IG_USERNAME        = os.environ["IG_USERNAME"]
IG_PASSWORD        = os.environ["IG_PASSWORD"]
INSTAGRAM_USERNAME = "ninevet2"
CHANNEL_ID         = 1488596316446527739
POLL_INTERVAL_MINS = 15
STATE_FILE         = "last_post.json"
DOWNLOAD_DIR       = "ig_downloads"
SESSION_FILE       = "ig_session.json"
# ─────────────────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ig_client = Client()


# ── INSTAGRAM LOGIN ───────────────────────────────────────────────────────────

def ig_login():
    ig_client.set_proxy("http://bytlvdsl:7x6y437b8smy@198.23.239.134:6540")
    if Path(SESSION_FILE).exists():
        try:
            ig_client.load_settings(SESSION_FILE)
            ig_client.login(IG_USERNAME, IG_PASSWORD)
            ig_client.get_timeline_feed()
            print("[INFO] Logged in via saved session")
            return
        except Exception as e:
            print(f"[WARN] Session login failed: {e}, retrying fresh...")

    ig_client.login(IG_USERNAME, IG_PASSWORD)
    ig_client.dump_settings(SESSION_FILE)
    print("[INFO] Logged in fresh and saved session")


# ── STATE HELPERS ─────────────────────────────────────────────────────────────

def load_last_shortcode():
    if Path(STATE_FILE).exists():
        with open(STATE_FILE) as f:
            return json.load(f).get("last_shortcode")
    return None


def save_last_shortcode(shortcode: str):
    with open(STATE_FILE, "w") as f:
        json.dump({"last_shortcode": shortcode}, f)


# ── INSTAGRAM SCRAPER ─────────────────────────────────────────────────────────

async def fetch_posts():
    try:
        loop = asyncio.get_event_loop()

        def _fetch():
            try:
                user_id = ig_client.user_id_from_username(INSTAGRAM_USERNAME)
                medias = ig_client.user_medias(user_id, amount=12)
                return medias
            except LoginRequired:
                print("[WARN] Login required, re-logging in...")
                ig_login()
                user_id = ig_client.user_id_from_username(INSTAGRAM_USERNAME)
                return ig_client.user_medias(user_id, amount=12)

        medias = await loop.run_in_executor(None, _fetch)

        posts = []
        for media in medias:
            shortcode = media.code
            timestamp = int(media.taken_at.timestamp())
            caption = media.caption_text or ""
            likes = media.like_count or 0
            comments = media.comment_count or 0

            media_urls = []

            if media.media_type == 8:  # carousel
                for resource in media.resources:
                    if resource.video_url:
                        media_urls.append({"url": str(resource.video_url), "is_video": True})
                    elif resource.thumbnail_url:
                        media_urls.append({"url": str(resource.thumbnail_url), "is_video": False})
            elif media.media_type == 2:  # video
                if media.video_url:
                    media_urls.append({"url": str(media.video_url), "is_video": True})
            else:  # photo
                if media.thumbnail_url:
                    media_urls.append({"url": str(media.thumbnail_url), "is_video": False})

            thumbnail = str(media.thumbnail_url or "") or (media_urls[0]["url"] if media_urls else "")

            posts.append({
                "shortcode": shortcode,
                "likes": likes,
                "comments": comments,
                "caption": caption,
                "timestamp": timestamp,
                "thumbnail": thumbnail,
                "media": media_urls,
            })

        posts.sort(key=lambda p: p["timestamp"], reverse=True)
        print(f"[INFO] Fetched {len(posts)} posts")
        return posts

    except Exception as e:
        print(f"[ERROR] fetch_posts crashed: {e}")
        import traceback
        traceback.print_exc()
        return []


# ── MEDIA DOWNLOADER ──────────────────────────────────────────────────────────

async def download_media(url: str, dest: Path) -> bool:
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                dest.write_bytes(r.content)
                return True
    except Exception as e:
        print(f"[WARN] Download failed: {e}")
    return False


# ── EMBED BUILDER ─────────────────────────────────────────────────────────────

class LinkButton(discord.ui.View):
    def __init__(self, url: str):
        super().__init__()
        self.add_item(discord.ui.Button(label="Open Post", url=url, emoji="🔗"))


def build_embed(post: dict) -> tuple[discord.Embed, discord.ui.View]:
    post_url = f"https://www.instagram.com/p/{post['shortcode']}/"

    timestamp_str = f"<t:{post['timestamp']}:R>"

    caption = post.get("caption", "")
    trimmed_caption = caption[:300] + ("…" if len(caption) > 300 else "") if caption else "_No caption_"

    description = (
        f"👤 **@{INSTAGRAM_USERNAME}** {timestamp_str}\n"
        f"\u200b\n"
        f"📝 {trimmed_caption}\n"
        f"\u200b\n"
        f"🔗 Link ⬇️"
    )

    embed = discord.Embed(description=description, color=0x000000)
    view = LinkButton(post_url)

    return embed, view


# ── POST SENDER ───────────────────────────────────────────────────────────────

async def send_post(channel: discord.TextChannel, post: dict):
    post_dir = Path(DOWNLOAD_DIR) / post["shortcode"]
    post_dir.mkdir(parents=True, exist_ok=True)

    files = []
    for i, media in enumerate(post["media"][:10]):
        ext = ".mp4" if media["is_video"] else ".jpg"
        dest = post_dir / f"media_{i}{ext}"
        success = await download_media(media["url"], dest)
        if success:
            files.append(discord.File(str(dest)))

    embed, view = build_embed(post)

    if files:
        await channel.send(embed=embed, view=view, files=files)
    else:
        if post.get("thumbnail"):
            embed.set_image(url=post["thumbnail"])
        await channel.send(embed=embed, view=view)

    for p in post_dir.iterdir():
        p.unlink()
    post_dir.rmdir()


# ── POLLING TASK ──────────────────────────────────────────────────────────────

@tasks.loop(minutes=POLL_INTERVAL_MINS)
async def poll_instagram():
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print(f"[ERROR] Channel {CHANNEL_ID} not found.")
        return

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Checking @{INSTAGRAM_USERNAME}...")

    posts = await fetch_posts()
    if not posts:
        print("[WARN] No posts returned.")
        return

    last_shortcode = load_last_shortcode()
    new_posts = []

    if last_shortcode is None:
        save_last_shortcode(posts[0]["shortcode"])
        print("[INFO] First run — saved latest post, waiting for next poll.")
        return

    now = datetime.now(tz=timezone.utc).timestamp()
    for post in posts:
        if post["shortcode"] == last_shortcode:
            break
        if now - post["timestamp"] > 86400:
            continue
        new_posts.append(post)

    for post in reversed(new_posts):
        try:
            await send_post(channel, post)
            print(f"[INFO] Sent post {post['shortcode']}")
        except Exception as e:
            print(f"[ERROR] Failed to send post {post['shortcode']}: {e}")

    if new_posts:
        save_last_shortcode(new_posts[0]["shortcode"])


# ── BOT CUSTOMISATION COMMANDS ────────────────────────────────────────────────

@bot.command(name="changename")
@commands.has_permissions(administrator=True)
async def changename(ctx, *, new_name: str):
    try:
        await bot.user.edit(username=new_name)
        await ctx.send(f"✅ Name changed to **{new_name}**!")
    except discord.errors.HTTPException as e:
        await ctx.send(f"❌ Failed: {e}")


@bot.command(name="changepfp")
@commands.has_permissions(administrator=True)
async def changepfp(ctx):
    if not ctx.message.attachments:
        await ctx.send("❌ Please attach an image to the message.")
        return
    attachment = ctx.message.attachments[0]
    if not attachment.content_type or not attachment.content_type.startswith("image/"):
        await ctx.send("❌ Attachment must be an image.")
        return
    try:
        image_data = await attachment.read()
        await bot.user.edit(avatar=image_data)
        await ctx.send("✅ Profile picture updated!")
    except discord.errors.HTTPException as e:
        await ctx.send(f"❌ Failed: {e}")


# ── TEST COMMAND ─────────────────────────────────────────────────────────────

@bot.command(name="testpost")
async def testpost(ctx):
    await ctx.send(f"⏳ Fetching latest post from @{INSTAGRAM_USERNAME}...")
    posts = await fetch_posts()
    if not posts:
        await ctx.send("❌ Could not fetch any posts. Check the console for errors.")
        return
    await send_post(ctx.channel, posts[0])
    await ctx.send("✅ Done!")


# ── BOT EVENTS ────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")
    print(f"Watching @{INSTAGRAM_USERNAME} every {POLL_INTERVAL_MINS} min(s)")
    try:
        ig_login()
    except Exception as e:
        print(f"[ERROR] Instagram login failed: {e}")
    poll_instagram.start()


# ── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    bot.run(DISCORD_TOKEN)
