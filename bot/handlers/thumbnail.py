from pyrogram import Client, filters
from pyrogram.types import Message
from bot.database.crud import set_user_thumbnail, remove_user_thumbnail
from bot.utils.decorators import rate_limit, check_ban

@Client.on_message(filters.command("setthumbnail") & filters.private)
@rate_limit(limit=3, per=10)
@check_ban
async def set_thumbnail_cmd(client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.photo:
        await message.reply_text("Reply to a photo to set as custom thumbnail.")
        return
    file_id = message.reply_to_message.photo.file_id
    await set_user_thumbnail(message.from_user.id, file_id)
    await message.reply_text("✅ Thumbnail set successfully!")

@Client.on_message(filters.command("remthumbnail") & filters.private)
@rate_limit(limit=3, per=10)
@check_ban
async def rem_thumbnail_cmd(client, message: Message):
    await remove_user_thumbnail(message.from_user.id)
    await message.reply_text("✅ Thumbnail removed.")
