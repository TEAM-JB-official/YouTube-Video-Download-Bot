import asyncio
import aiohttp
from fastapi import FastAPI
import uvicorn
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.config import Config
from bot.database.models import db
from bot.utils.logger import logger
from bot.utils.queue import DownloadQueue

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

# ============ EXPLICITLY IMPORT ALL HANDLERS ============
# This ensures every handler function is loaded and registered
from bot.handlers.user import (
    start_cmd, help_cmd, account_cmd, plan_cmd,
    myplan_cmd, terms_cmd, status_cmd
)
from bot.handlers.download import handle_url, download_callback, quality_callback
from bot.handlers.thumbnail import set_thumbnail_cmd, rem_thumbnail_cmd
from bot.handlers.upload import set_chat_cmd, remove_chat_cmd
from bot.handlers.cookies import (
    set_cookies_cmd, remove_cookies_cmd, cookie_info_cmd, cookie_check_cmd,
    set_owner_cookies_cmd, remove_owner_cookies_cmd,
    check_cookies_cmd, cookie_stats_cmd
)
from bot.handlers.premium import (
    add_premium_cmd, remove_premium_cmd, check_cmd,
    get_premium_cmd, premium_stats_cmd
)
from bot.handlers.admin import (
    stats_cmd, ban_cmd, unban_cmd, users_cmd,
    get_user_cmd, broadcast_cmd
)
from bot.handlers.callback import help_callback, plans_callback

# ============ REGISTER ALL HANDLERS EXPLICITLY ============
# User commands
app.add_handler(start_cmd)
app.add_handler(help_cmd)
app.add_handler(account_cmd)
app.add_handler(plan_cmd)
app.add_handler(myplan_cmd)
app.add_handler(terms_cmd)
app.add_handler(status_cmd)

# Download commands
app.add_handler(handle_url)
app.add_handler(download_callback)
app.add_handler(quality_callback)

# Thumbnail commands
app.add_handler(set_thumbnail_cmd)
app.add_handler(rem_thumbnail_cmd)

# Upload commands
app.add_handler(set_chat_cmd)
app.add_handler(remove_chat_cmd)

# Cookie commands (user)
app.add_handler(set_cookies_cmd)
app.add_handler(remove_cookies_cmd)
app.add_handler(cookie_info_cmd)
app.add_handler(cookie_check_cmd)

# Cookie commands (admin)
app.add_handler(set_owner_cookies_cmd)
app.add_handler(remove_owner_cookies_cmd)
app.add_handler(check_cookies_cmd)
app.add_handler(cookie_stats_cmd)

# Premium admin commands
app.add_handler(add_premium_cmd)
app.add_handler(remove_premium_cmd)
app.add_handler(check_cmd)
app.add_handler(get_premium_cmd)
app.add_handler(premium_stats_cmd)

# Admin commands
app.add_handler(stats_cmd)
app.add_handler(ban_cmd)
app.add_handler(unban_cmd)
app.add_handler(users_cmd)
app.add_handler(get_user_cmd)
app.add_handler(broadcast_cmd)

# Callbacks
app.add_handler(help_callback)
app.add_handler(plans_callback)

# ============ FALLBACK DEBUG HANDLER ============
# This will log EVERY private message to confirm the bot is receiving updates
@app.on_message(filters.private)
async def debug_all(client: Client, message: Message):
    logger.info(f"📨 DEBUG - Message: '{message.text}' from {message.from_user.id}")

# ============ DOWNLOAD QUEUE ============
download_queue = DownloadQueue()

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
        # Connect to database
        await db.connect()
        logger.info("✅ Database connected.")
        
        # Start download queue workers
        await download_queue.start_workers(count=3)
        logger.info("✅ Download workers started.")
        
        # Start web server
        asyncio.create_task(run_web())
        logger.info(f"✅ Web server started on port {Config.PORT}")
        
        # Start Telegram bot
        logger.info("Starting Telegram bot...")
        await app.start()
        
        # Delete any existing webhook to enable polling
        await delete_webhook()
        webhook_info = await get_webhook_info()
        if webhook_info and webhook_info.get("ok"):
            url = webhook_info.get("result", {}).get("url")
            if not url:
                logger.info("✅ Webhook cleared. Polling mode active.")
            else:
                logger.warning(f"⚠️ Webhook still set: {url}")
        
        # Get bot info
        me = await app.get_me()
        logger.info(f"✅ BOT ONLINE! Username: @{me.username}, ID: {me.id}")
        
        # Send test message to admin
        if Config.ADMIN_IDS:
            try:
                await app.send_message(
                    Config.ADMIN_IDS[0],
                    f"✅ Full bot is online and listening for updates!\n\n"
                    f"Username: @{me.username}\n"
                    f"ID: {me.id}\n\n"
                    "All features are active. Send /start to test."
                )
                logger.info(f"✅ Test message sent to admin")
            except Exception as e:
                logger.error(f"Failed to send test message: {e}")
        
        # 🔥 KEEP THE BOT RUNNING – app.start() already runs the update loop
        logger.info("🔄 Bot is now listening for messages...")
        await asyncio.Event().wait()  # Block forever, letting the client process updates
        
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
