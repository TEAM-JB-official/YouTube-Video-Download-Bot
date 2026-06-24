from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.database.crud import get_user, create_user
from bot.utils.decorators import rate_limit, check_ban
from bot.config import Config
from datetime import datetime

@Client.on_message(filters.command("start") & filters.private)
@rate_limit(limit=3, per=10)
@check_ban
async def start_cmd(client, message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        user = await create_user(message.from_user.__dict__)
    await message.reply_text(
        f"👋 Welcome {user['first_name']}!\n\nSend me a YouTube URL to download.\nUse /help for commands.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📚 Help", callback_data="help"),
             InlineKeyboardButton("💰 Plans", callback_data="plans")]
        ])
    )

@Client.on_message(filters.command("help") & filters.private)
@rate_limit(limit=3, per=10)
@check_ban
async def help_cmd(client, message: Message):
    text = (
        "📖 **Help & Commands**\n\n"
        "**Download**\nSend a YouTube URL (video, Short, playlist, live).\nMultiple URLs per line for batch.\n\n"
        "**Account**\n/account - Your info\n/plan - Plans\n/myplan - Your plan\n/terms - ToS\n/status - Queue status\n\n"
        "**Upload**\n/setchat <chat_id> - Set upload destination\n/removechat - Remove it\n\n"
        "**Thumbnail**\n/setthumbnail (reply to photo) - Set custom\n/remthumbnail - Remove\n\n"
        "**Cookies**\n/setcookies (reply to cookies.txt) - Upload\n/removecookies - Remove\n/cookieinfo - Check\n/cookiecheck - Validate\n\n"
        "**Premium**\nUnlimited downloads, priority, larger files, playlists, live streams."
    )
    await message.reply_text(text)

@Client.on_message(filters.command("account") & filters.private)
@rate_limit(limit=3, per=10)
@check_ban
async def account_cmd(client, message: Message):
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

@Client.on_message(filters.command("plan") & filters.private)
@rate_limit(limit=3, per=10)
@check_ban
async def plan_cmd(client, message: Message):
    text = (
        "💰 **Premium Plans**\n\n"
        "**Premium** – $5/month\n"
        "✅ Unlimited downloads\n"
        "✅ Priority queue\n"
        "✅ File size up to 2GB\n"
        "✅ Playlist downloads\n"
        "✅ Live stream recording\n"
        "✅ No daily limits\n\n"
        "Contact @admin to purchase."
    )
    await message.reply_text(text)

@Client.on_message(filters.command("myplan") & filters.private)
@rate_limit(limit=3, per=10)
@check_ban
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

@Client.on_message(filters.command("terms") & filters.private)
@rate_limit(limit=3, per=10)
@check_ban
async def terms_cmd(client, message: Message):
    text = (
        "📜 **Terms of Service**\n\n"
        "1. Personal use only.\n"
        "2. Do not share copyrighted content.\n"
        "3. You are responsible for the content you download.\n"
        "4. We reserve the right to ban users who misuse the bot.\n"
        "5. Premium subscriptions are non-refundable.\n"
        "6. We do not store your personal data (except user ID and settings).\n"
        "7. Cookies are encrypted and only used for downloads."
    )
    await message.reply_text(text)

@Client.on_message(filters.command("status") & filters.private)
@rate_limit(limit=3, per=10)
@check_ban
async def status_cmd(client, message: Message):
    from bot.main import download_queue
    pending = download_queue.pending_count
    processing = len(download_queue.processing)
    await message.reply_text(f"📋 **Queue Status**\n\nPending: {pending}\nProcessing: {processing}")
