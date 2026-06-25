import asyncio
import aiohttp
import os
from datetime import datetime
from fastapi import FastAPI
import uvicorn
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.config import Config
from bot.database.models import db
from bot.database.crud import (
    get_user, create_user, update_user, get_all_users, count_users,
    set_premium, remove_premium, check_premium,
    add_download_log, increment_daily_count,
    set_user_thumbnail, remove_user_thumbnail,
    set_user_upload_chat, remove_user_upload_chat,
    set_user_cookies, remove_user_cookies,
    set_owner_cookies, get_owner_cookies, remove_owner_cookies,
    ban_user, unban_user, is_user_banned,
    add_system_log
)
from bot.utils.logger import logger
from bot.utils.queue import download_queue

# ============ WEB SERVER ============
web_app = FastAPI()

@web_app.get("/")
@web_app.head("/")
async def root():
    return {"status": "ok"}

@web_app.get("/health")
@web_app.head("/health")
async def health():
    try:
        await db.connect()
        await db.db.command('ping')
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": "disconnected", "error": str(e)}

async def run_web():
    config = uvicorn.Config(web_app, host="0.0.0.0", port=Config.PORT, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

# ============ TELEGRAM BOT ============
app = Client(
    "youtube_bot",
    bot_token=Config.BOT_TOKEN,
    api_id=Config.API_ID,
    api_hash=Config.API_HASH
)

# ============ USER COMMANDS ============
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message: Message):
    logger.info(f"✅ /start received from {message.from_user.id}")
    user = await get_user(message.from_user.id)
    if not user:
        user = await create_user(message.from_user.__dict__)
    await message.reply_text(
        f"👋 Welcome {user['first_name']}!\n\n"
        "I can download videos, audio, playlists, and live streams from YouTube.\n"
        "Send me a YouTube URL to get started.\n\n"
        "Use /help for more information.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📚 Help", callback_data="help"),
             InlineKeyboardButton("💰 Plans", callback_data="plans")]
        ])
    )

@app.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message: Message):
    logger.info(f"✅ /help received from {message.from_user.id}")
    text = (
        "📖 **Help & Commands**\n\n"
        "**Download**\n"
        "Send a YouTube URL (video, Short, playlist, live).\n"
        "Multiple URLs per line for batch.\n\n"
        "**Account**\n"
        "/account - Your account info\n"
        "/plan - View premium plans\n"
        "/myplan - Your current plan\n"
        "/terms - Terms of service\n"
        "/status - Queue status\n\n"
        "**Upload**\n"
        "/setchat <chat_id> - Set upload destination\n"
        "/removechat - Remove custom destination\n\n"
        "**Thumbnail**\n"
        "/setthumbnail (reply to photo) - Set custom thumbnail\n"
        "/remthumbnail - Remove custom thumbnail\n\n"
        "**Cookies**\n"
        "/setcookies (reply to cookies.txt) - Upload your cookies\n"
        "/removecookies - Remove your cookies\n"
        "/cookieinfo - Check your cookie status\n"
        "/cookiecheck - Validate your cookies\n\n"
        "**Premium**\n"
        "Unlimited downloads, priority queue, larger files, playlists, live streams."
    )
    await message.reply_text(text)

@app.on_message(filters.command("account") & filters.private)
async def account_cmd(client, message: Message):
    logger.info(f"✅ /account received from {message.from_user.id}")
    user = await get_user(message.from_user.id)
    if not user:
        user = await create_user(message.from_user.__dict__)
    premium = user.get('is_premium', False)
    expiry = user.get('premium_expiry')
    if premium and expiry and expiry > datetime.utcnow():
        premium_status = f"✅ Active until {expiry.strftime('%Y-%m-%d %H:%M')}"
    else:
        premium_status = "❌ Free"
    text = (
        f"📊 **Account Info**\n\n"
        f"ID: `{user['user_id']}`\n"
        f"Name: {user['first_name']} {user.get('last_name', '')}\n"
        f"Username: @{user.get('username', 'N/A')}\n"
        f"Premium: {premium_status}\n"
        f"Daily Downloads: {user.get('daily_count', 0)}/{Config.DAILY_LIMIT}\n"
        f"Thumbnail: {'✅ Set' if user.get('thumbnail_file_id') else '❌ Not set'}\n"
        f"Upload Chat: {user.get('upload_chat_id', 'DM only')}\n"
        f"Cookies: {'✅ Uploaded' if user.get('cookies_encrypted') else '❌ None'}"
    )
    await message.reply_text(text)

@app.on_message(filters.command("plan") & filters.private)
async def plan_cmd(client, message: Message):
    await message.reply_text(
        "💰 **Premium Plans**\n\n"
        "**Premium** – $5/month\n"
        "✅ Unlimited downloads\n"
        "✅ Priority queue\n"
        "✅ File size up to 2GB\n"
        "✅ Playlist downloads\n"
        "✅ Live stream recording\n"
        "✅ Custom thumbnail\n"
        "✅ No daily limits\n\n"
        "Contact @admin to purchase."
    )

@app.on_message(filters.command("myplan") & filters.private)
async def myplan_cmd(client, message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        user = await create_user(message.from_user.__dict__)
    premium = user.get('is_premium', False)
    expiry = user.get('premium_expiry')
    if premium and expiry and expiry > datetime.utcnow():
        text = f"✅ You have **Premium** until {expiry.strftime('%Y-%m-%d %H:%M')}."
    else:
        text = "❌ You are on the **Free** plan. Upgrade with /plan."
    await message.reply_text(text)

@app.on_message(filters.command("terms") & filters.private)
async def terms_cmd(client, message: Message):
    text = (
        "📜 **Terms of Service**\n\n"
        "1. This bot is for personal use only.\n"
        "2. Do not share copyrighted content.\n"
        "3. You are responsible for the content you download.\n"
        "4. We reserve the right to ban users who misuse the bot.\n"
        "5. Premium subscriptions are non-refundable.\n"
        "6. We do not store your personal data (except user ID and settings).\n"
        "7. Cookies are encrypted and only used for downloads."
    )
    await message.reply_text(text)

@app.on_message(filters.command("status") & filters.private)
async def status_cmd(client, message: Message):
    pending = download_queue.pending_count
    processing = len(download_queue.processing)
    text = f"📋 **Queue Status**\n\nPending: {pending}\nProcessing: {processing}"
    await message.reply_text(text)

@app.on_message(filters.command("ping") & filters.private)
async def ping_cmd(client, message: Message):
    logger.info(f"✅ /ping received from {message.from_user.id}")
    await message.reply_text("🏓 Pong! Bot is alive!")

# ============ THUMBNAIL COMMANDS ============
@app.on_message(filters.command("setthumbnail") & filters.private)
async def set_thumbnail_cmd(client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.photo:
        await message.reply_text("Reply to a photo to set as custom thumbnail.")
        return
    file_id = message.reply_to_message.photo.file_id
    await set_user_thumbnail(message.from_user.id, file_id)
    await message.reply_text("✅ Thumbnail set successfully!")

@app.on_message(filters.command("remthumbnail") & filters.private)
async def rem_thumbnail_cmd(client, message: Message):
    await remove_user_thumbnail(message.from_user.id)
    await message.reply_text("✅ Thumbnail removed.")

# ============ UPLOAD DESTINATION COMMANDS ============
@app.on_message(filters.command("setchat") & filters.private)
async def set_chat_cmd(client, message: Message):
    args = message.text.split()
    if len(args) != 2:
        await message.reply_text("Usage: /setchat <chat_id> (negative for group/channel)")
        return
    try:
        chat_id = int(args[1])
    except ValueError:
        await message.reply_text("Invalid chat ID. Must be an integer.")
        return
    await set_user_upload_chat(message.from_user.id, chat_id)
    await message.reply_text(f"✅ Upload destination set to chat ID: {chat_id}")

@app.on_message(filters.command("removechat") & filters.private)
async def remove_chat_cmd(client, message: Message):
    await remove_user_upload_chat(message.from_user.id)
    await message.reply_text("✅ Upload destination removed. Files will be sent to your DM.")

# ============ URL HANDLER ============
@app.on_message(filters.private & filters.regex(r'^(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.'))
async def handle_url(client, message: Message):
    logger.info(f"✅ URL received from {message.from_user.id}: {message.text}")
    
    user_id = message.from_user.id
    user = await get_user(user_id)
    if not user:
        user = await create_user(message.from_user.__dict__)
    
    if user.get('banned'):
        await message.reply_text("🚫 You are banned.")
        return

    urls = [line.strip() for line in message.text.split('\n') if line.strip()]
    if len(urls) > Config.MAX_BATCH_URLS:
        await message.reply_text(f"❌ Maximum {Config.MAX_BATCH_URLS} URLs at once.")
        return

    # Store URLs for callback
    if not hasattr(client, 'user_urls'):
        client.user_urls = {}
    client.user_urls[user_id] = urls

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Video", callback_data=f"dl_video_{user_id}"),
         InlineKeyboardButton("🎵 Audio", callback_data=f"dl_audio_{user_id}")],
        [InlineKeyboardButton("📁 Playlist", callback_data=f"dl_playlist_{user_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="dl_cancel")]
    ])
    await message.reply_text("Select download format:", reply_markup=keyboard)

# ============ CALLBACKS ============
@app.on_callback_query(filters.regex(r'^dl_(video|audio|playlist|cancel)_(\d+)$'))
async def download_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data.split('_')
    action = data[1]
    if data[2] != str(user_id):
        await callback_query.answer("Not for you.", show_alert=True)
        return
    if action == "cancel":
        await callback_query.message.delete()
        await callback_query.answer("Cancelled.")
        return

    urls = getattr(client, 'user_urls', {}).get(user_id, [])
    if not urls:
        await callback_query.answer("No URLs found. Please send again.", show_alert=True)
        return

    if action == 'video':
        await process_urls(client, callback_query.message, user_id, urls, 'video', 'best')
    elif action == 'audio':
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("128k MP3", callback_data=f"q_128_{user_id}"),
             InlineKeyboardButton("192k MP3", callback_data=f"q_192_{user_id}"),
             InlineKeyboardButton("320k MP3", callback_data=f"q_320_{user_id}")],
            [InlineKeyboardButton("128k M4A", callback_data=f"q_128m4a_{user_id}"),
             InlineKeyboardButton("192k M4A", callback_data=f"q_192m4a_{user_id}")],
            [InlineKeyboardButton("Cancel", callback_data="dl_cancel")]
        ])
        await callback_query.message.edit_text("Select audio quality:", reply_markup=keyboard)
    elif action == 'playlist':
        await process_urls(client, callback_query.message, user_id, urls, 'playlist', 'best')

@app.on_callback_query(filters.regex(r'^q_(\d+)(m4a)?_(\d+)$'))
async def quality_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    parts = callback_query.data.split('_')
    bitrate = parts[1]
    codec = 'm4a' if len(parts) > 2 and parts[2] == 'm4a' else 'mp3'
    quality = f"{bitrate}{codec}"
    user_id_from_callback = int(parts[-1])
    if user_id_from_callback != user_id:
        await callback_query.answer("Not for you.", show_alert=True)
        return
    urls = getattr(client, 'user_urls', {}).get(user_id, [])
    if not urls:
        await callback_query.answer("No URLs.", show_alert=True)
        return
    await process_urls(client, callback_query.message, user_id, urls, 'audio', quality)

@app.on_callback_query(filters.regex("^help$"))
async def help_callback(client, callback_query: CallbackQuery):
    await callback_query.message.edit_text("Use /help for full command list.")
    await callback_query.answer()

@app.on_callback_query(filters.regex("^plans$"))
async def plans_callback(client, callback_query: CallbackQuery):
    await callback_query.message.edit_text("Use /plan for premium details.")
    await callback_query.answer()

async def process_urls(client, message, user_id, urls, format_type, quality):
    from bot.utils.queue import DownloadJob
    user = await get_user(user_id)
    if not user:
        user = await create_user(message.from_user.__dict__)
    is_premium = user.get('is_premium', False)
    for url in urls:
        job = DownloadJob(
            user_id=user_id,
            url=url,
            format_type=format_type,
            quality=quality,
            rename=None,
            caption=None,
            upload_chat=user.get('upload_chat_id'),
            is_premium=is_premium
        )
        await download_queue.add_job(job)
    await message.edit_text(f"✅ {len(urls)} job(s) added to queue. You will receive the files once processed.")
    if hasattr(client, 'user_urls') and user_id in client.user_urls:
        del client.user_urls[user_id]

# ============ COOKIE COMMANDS ============
@app.on_message(filters.command("setcookies") & filters.private)
async def set_cookies_cmd(client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply_text("Reply to a `cookies.txt` file.")
        return
    doc = message.reply_to_message.document
    if not doc.file_name.endswith('.txt'):
        await message.reply_text("Please upload a .txt file (Netscape format).")
        return
    from bot.utils.helpers import encrypt_cookies, validate_cookie_content
    path = await client.download_media(doc)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        if not validate_cookie_content(content):
            await message.reply_text("❌ Invalid cookie format. Must be Netscape format.")
            return
        encrypted = encrypt_cookies(content)
        await set_user_cookies(message.from_user.id, encrypted)
        await message.reply_text("✅ Cookies saved successfully!")
    except Exception as e:
        await message.reply_text(f"❌ Failed to save cookies: {str(e)}")
        logger.error(f"Cookie save error: {e}")
    finally:
        if os.path.exists(path):
            os.remove(path)

@app.on_message(filters.command("removecookies") & filters.private)
async def remove_cookies_cmd(client, message: Message):
    await remove_user_cookies(message.from_user.id)
    await message.reply_text("✅ Your cookies have been removed.")

@app.on_message(filters.command("cookieinfo") & filters.private)
async def cookie_info_cmd(client, message: Message):
    user = await get_user(message.from_user.id)
    if user and user.get('cookies_encrypted'):
        await message.reply_text("✅ You have uploaded cookies.")
    else:
        await message.reply_text("❌ You have not uploaded any cookies.")

@app.on_message(filters.command("cookiecheck") & filters.private)
async def cookie_check_cmd(client, message: Message):
    from bot.utils.helpers import decrypt_cookies, validate_cookie_content
    user = await get_user(message.from_user.id)
    if not user or not user.get('cookies_encrypted'):
        await message.reply_text("❌ No cookies found. Use /setcookies to upload.")
        return
    try:
        content = decrypt_cookies(user['cookies_encrypted'])
        if validate_cookie_content(content):
            await message.reply_text("✅ Cookies appear valid (format check passed).")
        else:
            await message.reply_text("❌ Cookies are invalid or corrupt. Please re-upload.")
    except Exception as e:
        await message.reply_text(f"❌ Error validating cookies: {str(e)}")

# ============ ADMIN COOKIE COMMANDS ============
@app.on_message(filters.command("setownercookies") & filters.private)
async def set_owner_cookies_cmd(client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized.")
        return
    from bot.utils.helpers import encrypt_cookies, validate_cookie_content
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply_text("Reply to a cookies.txt file.")
        return
    doc = message.reply_to_message.document
    path = await client.download_media(doc)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        if not validate_cookie_content(content):
            await message.reply_text("Invalid cookie format.")
            return
        encrypted = encrypt_cookies(content)
        await set_owner_cookies(encrypted)
        await message.reply_text("✅ Owner cookies set successfully.")
    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")
    finally:
        if os.path.exists(path):
            os.remove(path)

@app.on_message(filters.command("removeownercookies") & filters.private)
async def remove_owner_cookies_cmd(client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized.")
        return
    await remove_owner_cookies()
    await message.reply_text("✅ Owner cookies removed.")

@app.on_message(filters.command("checkcookies") & filters.private)
async def check_cookies_cmd(client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized.")
        return
    owner = await get_owner_cookies()
    if owner:
        await message.reply_text("✅ Owner cookies are set.")
    else:
        await message.reply_text("❌ No owner cookies set.")

# ============ ADMIN PREMIUM COMMANDS ============
@app.on_message(filters.command("addpremium") & filters.private)
async def add_premium_cmd(client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized.")
        return
    args = message.text.split()
    if len(args) != 3:
        await message.reply_text("Usage: /addpremium <user_id> <days>")
        return
    try:
        user_id = int(args[1])
        days = int(args[2])
    except ValueError:
        await message.reply_text("Invalid user_id or days.")
        return
    user = await get_user(user_id)
    if not user:
        await message.reply_text("User not found.")
        return
    await set_premium(user_id, days)
    await message.reply_text(f"✅ Premium added to user {user_id} for {days} days.")
    logger.info(f"Admin {message.from_user.id} added premium to {user_id} for {days} days")

@app.on_message(filters.command("removepremium") & filters.private)
async def remove_premium_cmd(client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized.")
        return
    args = message.text.split()
    if len(args) != 2:
        await message.reply_text("Usage: /removepremium <user_id>")
        return
    try:
        user_id = int(args[1])
    except ValueError:
        await message.reply_text("Invalid user_id.")
        return
    await remove_premium(user_id)
    await message.reply_text(f"✅ Premium removed from user {user_id}.")

# ============ ADMIN COMMANDS (Non‑Premium) ============

@app.on_message(filters.command("stats") & filters.private)
async def stats_cmd(client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized.")
        return
    total_users = await count_users({})
    banned = await count_users({"banned": True})
    total, used, free = shutil.disk_usage(Config.DOWNLOAD_PATH)
    storage = f"{used // (1024**3)} GB / {total // (1024**3)} GB"
    text = (
        f"📊 **Bot Statistics**\n\n"
        f"Total Users: {total_users}\n"
        f"Banned Users: {banned}\n"
        f"Storage Used: {storage}"
    )
    await message.reply_text(text)

@app.on_message(filters.command("ban") & filters.private)
async def ban_cmd(client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized.")
        return
    args = message.text.split()
    if len(args) != 2:
        await message.reply_text("Usage: /ban <user_id>")
        return
    try:
        user_id = int(args[1])
    except ValueError:
        await message.reply_text("Invalid user_id.")
        return
    await ban_user(user_id)
    await message.reply_text(f"✅ User {user_id} banned.")
    logger.info(f"Admin {message.from_user.id} banned {user_id}")

@app.on_message(filters.command("unban") & filters.private)
async def unban_cmd(client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized.")
        return
    args = message.text.split()
    if len(args) != 2:
        await message.reply_text("Usage: /unban <user_id>")
        return
    try:
        user_id = int(args[1])
    except ValueError:
        await message.reply_text("Invalid user_id.")
        return
    await unban_user(user_id)
    await message.reply_text(f"✅ User {user_id} unbanned.")

@app.on_message(filters.command("users") & filters.private)
async def users_cmd(client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized.")
        return
    users = await get_all_users({})
    if not users:
        await message.reply_text("No users found.")
        return
    text = "👥 **Recent Users**\n\n"
    for u in users[:20]:
        text += f"• {u['user_id']} (@{u.get('username', 'N/A')})\n"
    await message.reply_text(text)

@app.on_message(filters.command("get") & filters.private)
async def get_user_cmd(client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized.")
        return
    args = message.text.split()
    if len(args) != 2:
        await message.reply_text("Usage: /get <user_id>")
        return
    try:
        user_id = int(args[1])
    except ValueError:
        await message.reply_text("Invalid user_id.")
        return
    user = await get_user(user_id)
    if not user:
        await message.reply_text("User not found.")
        return
    text = (
        f"User ID: {user['user_id']}\n"
        f"Name: {user['first_name']} {user.get('last_name', '')}\n"
        f"Username: @{user.get('username', 'N/A')}\n"
        f"Banned: {user.get('banned')}\n"
        f"Daily Count: {user.get('daily_count')}\n"
        f"Cookies: {'✅' if user.get('cookies_encrypted') else '❌'}"
    )
    await message.reply_text(text)

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_cmd(client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized.")
        return
    if message.reply_to_message:
        users = await get_all_users({})
        count = 0
        for u in users:
            try:
                await message.reply_to_message.copy(chat_id=u['user_id'])
                count += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Broadcast to {u['user_id']} failed: {e}")
        await message.reply_text(f"✅ Broadcast forwarded to {count} users.")
    else:
        text = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
        if not text:
            await message.reply_text("Provide text after /broadcast or reply to a message.")
            return
        users = await get_all_users({})
        count = 0
        for u in users:
            try:
                await client.send_message(u['user_id'], text)
                count += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Broadcast to {u['user_id']} failed: {e}")
        await message.reply_text(f"✅ Broadcast sent to {count} users.")

# ============ ADMIN COOKIE COMMANDS ============
@app.on_message(filters.command("setownercookies") & filters.private)
async def set_owner_cookies_cmd(client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized.")
        return
    from bot.utils.helpers import encrypt_cookies, validate_cookie_content
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply_text("Reply to a cookies.txt file.")
        return
    doc = message.reply_to_message.document
    path = await client.download_media(doc)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        if not validate_cookie_content(content):
            await message.reply_text("Invalid cookie format.")
            return
        encrypted = encrypt_cookies(content)
        await set_owner_cookies(encrypted)
        await message.reply_text("✅ Owner cookies set successfully.")
    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")
    finally:
        if os.path.exists(path):
            os.remove(path)

@app.on_message(filters.command("removeownercookies") & filters.private)
async def remove_owner_cookies_cmd(client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized.")
        return
    await remove_owner_cookies()
    await message.reply_text("✅ Owner cookies removed.")

@app.on_message(filters.command("checkcookies") & filters.private)
async def check_cookies_cmd(client, message: Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized.")
        return
    owner = await get_owner_cookies()
    if owner:
        await message.reply_text("✅ Owner cookies are set.")
    else:
        await message.reply_text("❌ No owner cookies set.")

# ============ CALLBACK HANDLERS ============
@app.on_callback_query(filters.regex("^help$"))
async def help_callback(client, callback_query: CallbackQuery):
    await callback_query.message.edit_text("Use /help for full command list.")
    await callback_query.answer()

@app.on_callback_query(filters.regex("^plans$"))
async def plans_callback(client, callback_query: CallbackQuery):
    await callback_query.message.edit_text("No premium plans available.")
    await callback_query.answer()

# ============ HELPER: Webhook management ============
async def get_webhook_info():
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/getWebhookInfo"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                return await resp.json()
    except Exception as e:
        logger.error(f"Failed to get webhook info: {e}")
        return None

async def delete_webhook():
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/deleteWebhook"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                result = await resp.json()
                if result.get("ok"):
                    logger.info("✅ Webhook deleted successfully via HTTP.")
                    return True
                else:
                    logger.warning(f"Webhook deletion failed: {result}")
                    return False
    except Exception as e:
        logger.error(f"HTTP webhook deletion error: {e}")
        return False

# ============ MAIN ============
async def main():
    try:
        await db.connect()
        logger.info("✅ Database connected.")
        
        await download_queue.start_workers(count=3)
        logger.info("✅ Download workers started.")
        
        asyncio.create_task(run_web())
        logger.info(f"✅ Web server started on port {Config.PORT}")
        
        logger.info("Starting Telegram bot...")
        await app.start()
        
        await delete_webhook()
        webhook_info = await get_webhook_info()
        if webhook_info and webhook_info.get("ok"):
            url = webhook_info.get("result", {}).get("url")
            if not url:
                logger.info("✅ Webhook cleared. Polling mode active.")
            else:
                logger.warning(f"⚠️ Webhook still set: {url}")
        
        me = await app.get_me()
        logger.info(f"✅ BOT ONLINE! Username: @{me.username}, ID: {me.id}")
        
        if Config.ADMIN_IDS:
            try:
                await app.send_message(
                    Config.ADMIN_IDS[0],
                    f"✅ Bot is online and listening for updates!\n\n"
                    f"Username: @{me.username}\n"
                    f"ID: {me.id}\n\n"
                    "All features are active. Send /start to test."
                )
                logger.info(f"✅ Test message sent to admin")
            except Exception as e:
                logger.error(f"Failed to send test message: {e}")
        
        logger.info("🔄 Bot is now listening for messages...")
        await asyncio.Event().wait()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
    finally:
        try:
            asyncio.run(download_queue.stop_workers())
        except:
            pass
