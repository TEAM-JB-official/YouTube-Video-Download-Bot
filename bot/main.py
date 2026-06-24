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
@web_app.get("/health")
async def health():
    try:
        await db.connect()
        await db.db.command('ping')
        return {"status": "ok", "database": "connected", "version": "1.0.0"}
    except Exception as e:
        return {"status": "error", "database": "disconnected", "error": str(e)}

async def run_web():
    config = uvicorn.Config(web_app, host="0.0.0.0", port=Config.PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

# Telegram bot
app = Client(
    "youtube_bot",
    bot_token=Config.BOT_TOKEN,
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    plugins=dict(root="bot.handlers")
)

download_queue = DownloadQueue()

async def main():
    try:
        # Connect to database
        await db.connect()
        logger.info("Database connected successfully.")
        
        # Start download queue
        await download_queue.start_workers(count=3)
        logger.info("Download workers started.")
        
        # Start web server
        asyncio.create_task(run_web())
        logger.info(f"Web server started on port {Config.PORT}")
        
        # Start Telegram bot
        logger.info("Starting Telegram bot...")
        await app.start()
        logger.info("✅ Bot started successfully! Ready for commands.")
        
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
