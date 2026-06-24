from functools import wraps
from pyrogram.types import Message
from bot.config import Config
from aiolimiter import AsyncLimiter
from bot.utils.logger import logger

user_limiters = {}

def rate_limit(limit=3, per=10):
    def decorator(func):
        @wraps(func)
        async def wrapper(client, message: Message):
            user_id = message.from_user.id
            if user_id not in user_limiters:
                user_limiters[user_id] = AsyncLimiter(limit, per)
            limiter = user_limiters[user_id]
            try:
                await limiter.acquire()
                return await func(client, message)
            except Exception:
                await message.reply_text("⏳ Too many requests. Please wait.")
        return wrapper
    return decorator

def admin_only(func):
    @wraps(func)
    async def wrapper(client, message: Message):
        if message.from_user.id not in Config.ADMIN_IDS:
            await message.reply_text("⛔ You are not authorized to use this command.")
            return
        return await func(client, message)
    return wrapper

def check_ban(func):
    @wraps(func)
    async def wrapper(client, message: Message):
        # Lazy import to avoid circular import
        from bot.database.crud import is_user_banned
        if await is_user_banned(message.from_user.id):
            await message.reply_text("🚫 You are banned from using this bot.")
            return
        return await func(client, message)
    return wrapper
