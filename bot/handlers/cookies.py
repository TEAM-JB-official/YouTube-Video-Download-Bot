from pyrogram import Client, filters
from pyrogram.types import Message
from bot.database.crud import set_user_cookies, remove_user_cookies, get_user, get_owner_cookies, set_owner_cookies, remove_owner_cookies
from bot.utils.decorators import rate_limit, check_ban, admin_only
from bot.utils.helpers import encrypt_cookies, decrypt_cookies, validate_cookie_content
from bot.utils.logger import logger
import os

# User commands
@Client.on_message(filters.command("setcookies") & filters.private)
@rate_limit(limit=3, per=10)
@check_ban
async def set_cookies_cmd(client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply_text("Reply to a `cookies.txt` file.")
        return
    doc = message.reply_to_message.document
    if not doc.file_name.endswith('.txt'):
        await message.reply_text("Please upload a .txt file (Netscape format).")
        return
    path = await client.download_media(doc)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        if not validate_cookie_content(content):
            await message.reply_text("❌ Invalid cookie format. Must be Netscape format.")
            return
        encrypted = encrypt_cookies(content)
        await set_user_cookies(message.from_user.id, encrypted)
        await message.reply_text("✅ Cookies saved successfully! They will be used for your downloads.")
    except Exception as e:
        await message.reply_text(f"❌ Failed to save cookies: {str(e)}")
        logger.error(f"Cookie save error: {e}")
    finally:
        if os.path.exists(path):
            os.remove(path)

@Client.on_message(filters.command("removecookies") & filters.private)
@rate_limit(limit=3, per=10)
@check_ban
async def remove_cookies_cmd(client, message: Message):
    await remove_user_cookies(message.from_user.id)
    await message.reply_text("✅ Your cookies have been removed.")

@Client.on_message(filters.command("cookieinfo") & filters.private)
@rate_limit(limit=3, per=10)
@check_ban
async def cookie_info_cmd(client, message: Message):
    user = await get_user(message.from_user.id)
    if user and user.get('cookies_encrypted'):
        await message.reply_text("✅ You have uploaded cookies.")
    else:
        await message.reply_text("❌ You have not uploaded any cookies.")

@Client.on_message(filters.command("cookiecheck") & filters.private)
@rate_limit(limit=3, per=10)
@check_ban
async def cookie_check_cmd(client, message: Message):
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

# Admin owner cookie commands
@Client.on_message(filters.command("setownercookies") & filters.private & admin_only)
async def set_owner_cookies_cmd(client, message: Message):
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

@Client.on_message(filters.command("removeownercookies") & filters.private & admin_only)
async def remove_owner_cookies_cmd(client, message: Message):
    await remove_owner_cookies()
    await message.reply_text("✅ Owner cookies removed.")

@Client.on_message(filters.command("checkcookies") & filters.private & admin_only)
async def check_cookies_cmd(client, message: Message):
    owner = await get_owner_cookies()
    if owner:
        await message.reply_text("✅ Owner cookies are set.")
    else:
        await message.reply_text("❌ No owner cookies set.")

@Client.on_message(filters.command("cookie_stats") & filters.private & admin_only)
async def cookie_stats_cmd(client, message: Message):
    from bot.database.models import db
    await db.connect()
    count = await db.db.users.count_documents({"cookies_encrypted": {"$ne": None}})
    owner = await get_owner_cookies()
    text = f"🍪 **Cookie Statistics**\n\nUsers with cookies: {count}\nOwner cookies: {'✅ Set' if owner else '❌ Not set'}"
    await message.reply_text(text)
