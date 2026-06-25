import asyncio
import aiohttp
from fastapi import FastAPI
import uvicorn
from pyrogram import Client
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
    api_hash=Config.API_HASH,
    plugins=dict(root="bot.handlers")   # Loads all handlers from handlers/ folder
)

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
