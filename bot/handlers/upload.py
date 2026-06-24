from pyrogram import Client, filters
from pyrogram.types import Message
from bot.database.crud import set_user_upload_chat, remove_user_upload_chat
from bot.utils.decorators import rate_limit, check_ban
from bot.utils.logger import logger
import os

@Client.on_message(filters.command("setchat") & filters.private)
@rate_limit(limit=3, per=10)
@check_ban
async def set_chat_cmd(client, message: Message):
    args = message.text.split()
    if len(args) != 2:
        await message.reply_text("Usage: /setchat <chat_id> (negative for group/channel)")
        return
    try:
        chat_id = int(args[1])
    except ValueError:
        await message.reply_text("Invalid chat ID.")
        return
    await set_user_upload_chat(message.from_user.id, chat_id)
    await message.reply_text(f"✅ Upload destination set to chat ID: {chat_id}")

@Client.on_message(filters.command("removechat") & filters.private)
@rate_limit(limit=3, per=10)
@check_ban
async def remove_chat_cmd(client, message: Message):
    await remove_user_upload_chat(message.from_user.id)
    await message.reply_text("✅ Upload destination removed. Files sent to DM.")

async def upload_file(user_id: int, file_path: str, chat_id: int, caption: str, thumbnail_path=None) -> bool:
    from bot.main import app
    try:
        if file_path.lower().endswith(('.mp4', '.mkv', '.avi')):
            if thumbnail_path and os.path.exists(thumbnail_path):
                await app.send_video(chat_id, video=file_path, caption=caption, thumb=thumbnail_path, supports_streaming=True)
            else:
                await app.send_video(chat_id, video=file_path, caption=caption, supports_streaming=True)
        elif file_path.lower().endswith(('.mp3', '.m4a')):
            if thumbnail_path and os.path.exists(thumbnail_path):
                await app.send_audio(chat_id, audio=file_path, caption=caption, thumb=thumbnail_path)
            else:
                await app.send_audio(chat_id, audio=file_path, caption=caption)
        else:
            await app.send_document(chat_id, document=file_path, caption=caption)
        logger.info(f"Uploaded {file_path} to {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return False
