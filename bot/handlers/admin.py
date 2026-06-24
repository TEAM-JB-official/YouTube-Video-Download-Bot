from pyrogram import Client, filters
from pyrogram.types import Message
from bot.database.crud import get_all_users, ban_user, unban_user, get_user, count_users
from bot.utils.decorators import admin_only
from bot.utils.logger import logger
from bot.config import Config
import shutil
import asyncio

@Client.on_message(filters.command("stats") & filters.private & admin_only)
async def stats_cmd(client, message: Message):
    total_users = await count_users({})
    premium_users = await count_users({"is_premium": True, "premium_expiry": {"$gt": datetime.utcnow()}})
    banned = await count_users({"banned": True})
    total, used, free = shutil.disk_usage(Config.DOWNLOAD_PATH)
    storage = f"{used // (1024**3)} GB / {total // (1024**3)} GB"
    text = (
        f"📊 **Statistics**\n\n"
        f"Total Users: {total_users}\n"
        f"Premium Users: {premium_users}\n"
        f"Banned Users: {banned}\n"
        f"Storage Used: {storage}"
    )
    await message.reply_text(text)

@Client.on_message(filters.command("ban") & filters.private & admin_only)
async def ban_cmd(client, message: Message):
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

@Client.on_message(filters.command("unban") & filters.private & admin_only)
async def unban_cmd(client, message: Message):
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

@Client.on_message(filters.command("users") & filters.private & admin_only)
async def users_cmd(client, message: Message):
    users = await get_all_users({})
    if not users:
        await message.reply_text("No users found.")
        return
    text = "👥 **Recent Users**\n\n"
    for u in users[:20]:
        text += f"• {u['user_id']} (@{u.get('username', 'N/A')}) – {'Premium' if u.get('is_premium') else 'Free'}\n"
    await message.reply_text(text)

@Client.on_message(filters.command("get") & filters.private & admin_only)
async def get_user_cmd(client, message: Message):
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
        f"Premium: {user.get('is_premium')}\n"
        f"Expiry: {user.get('premium_expiry')}\n"
        f"Banned: {user.get('banned')}\n"
        f"Daily Count: {user.get('daily_count')}\n"
        f"Cookies: {'✅' if user.get('cookies_encrypted') else '❌'}"
    )
    await message.reply_text(text)

@Client.on_message(filters.command("broadcast") & filters.private & admin_only)
async def broadcast_cmd(client, message: Message):
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
