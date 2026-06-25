import asyncio
from fastapi import FastAPI
import uvicorn
from pyrogram import Client
from bot.config import Config
from bot.database.models import db
from bot.utils.logger import logger
from bot.utils.queue import DownloadQueue

# Web server
web_app = FastAPI()

@web_app.get("/")
@web_app.head("/")
async def root():
    return {"status": "ok", "service": "YouTube Downloader Bot"}

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

# Create bot with plugin loading
app = Client(
    "youtube_bot",
    bot_token=Config.BOT_TOKEN,
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    plugins=dict(root="bot.handlers")  # This loads all handlers from handlers/ folder
)

download_queue = DownloadQueue()

async def main():
    try:
        # Connect to database
        await db.connect()
        logger.info("✅ Database connected successfully.")
        
        # Start download queue
        await download_queue.start_workers(count=3)
        logger.info("✅ Download workers started.")
        
        # Start web server
        asyncio.create_task(run_web())
        logger.info(f"✅ Web server started on port {Config.PORT}")
        
        # Start Telegram bot
        logger.info("Starting Telegram bot...")
        await app.start()
        
        # Get bot info to confirm it's working
        me = await app.get_me()
        logger.info(f"✅ Bot started successfully! Username: @{me.username}, ID: {me.id}")
        
        # Keep running
        await asyncio.Event().wait()
        
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
