from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.database.crud import get_user, create_user
from bot.utils.decorators import rate_limit, check_ban
from bot.utils.queue import DownloadJob
from bot.main import download_queue
from bot.config import Config
from bot.utils.logger import logger

@Client.on_message(filters.private & filters.regex(r'^(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.'))
@rate_limit(limit=5, per=30)
@check_ban
async def handle_url(client, message: Message):
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

@Client.on_callback_query(filters.regex(r'^dl_(video|audio|playlist|cancel)_(\d+)$'))
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
        await callback_query.answer("No URLs found.", show_alert=True)
        return

    if action == 'video':
        quality = 'best'
        await process_urls(client, callback_query.message, user_id, urls, 'video', quality)
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
        quality = 'best'
        await process_urls(client, callback_query.message, user_id, urls, 'playlist', quality)

@Client.on_callback_query(filters.regex(r'^q_(\d+)(m4a)?_(\d+)$'))
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

async def process_urls(client, message, user_id, urls, format_type, quality):
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
