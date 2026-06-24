from pyrogram import Client, filters
from pyrogram.types import Message
from bot.database.crud import set_premium, remove_premium, check_premium, get_user, get_all_users, count_users
from bot.utils.decorators import rate_limit, check_ban, admin_only
from bot.utils.logger import logger
from datetime import datetime

@Client.on_message(filters.command("addpremium") & filters.private & admin_only)
async def add_premium_cmd(client, message: Message):
    args = message.text.split()
    if len(args) != 3:
        await message.reply_text("Usage: /addpremium <user_id> <days>")
        return
    try:
        user_id = int(args[1])
        days = int(args[2])
    except ValueError:
        await message.reply_text("Invalid input.")
        return
    user = await get_user(user_id)
    if not user:
        await message.reply_text("User not found.")
        return
    await set_premium(user_id, days)
    await message.reply_text(f"✅ Premium added to user {user_id} for {days} days.")
    logger.info(f"Admin {message.from_user.id} added premium to {user_id}")

@Client.on_message(filters.command("removepremium") & filters.private & admin_only)
async def remove_premium_cmd(client, message: Message):
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

@Client.on_message(filters.command("check") & filters.private & admin_only)
async def check_cmd(client, message: Message):
    args = message.text.split()
    if len(args) != 2:
        await message.reply_text("Usage: /check <user_id>")
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
    premium = await check_premium(user_id)
    status = "Premium" if premium else "Free"
    expiry = user.get('premium_expiry')
    expiry_str = expiry.strftime('%Y-%m-%d %H:%M') if expiry else "N/A"
    text = f"User {user_id}:\nStatus: {status}\nExpiry: {expiry_str}\nBanned: {user.get('banned', False)}"
    await message.reply_text(text)

@Client.on_message(filters.command("getpremium") & filters.private & admin_only)
async def get_premium_cmd(client, message: Message):
    users = await get_all_users({"is_premium": True, "premium_expiry": {"$gt": datetime.utcnow()}})
    if not users:
        await message.reply_text("No active premium users.")
        return
    text = "💎 **Active Premium Users**\n\n"
    for u in users:
        expiry = u['premium_expiry'].strftime('%Y-%m-%d')
        text += f"• {u['user_id']} (@{u.get('username', 'N/A')}) – expires {expiry}\n"
    await message.reply_text(text)

@Client.on_message(filters.command("premiumstats") & filters.private & admin_only)
async def premium_stats_cmd(client, message: Message):
    total = await count_users()
    premium = await count_users({"is_premium": True, "premium_expiry": {"$gt": datetime.utcnow()}})
    await message.reply_text(f"📊 Premium Stats\nTotal Users: {total}\nPremium Users: {premium}")
