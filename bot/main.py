import asyncio
import os
from fastapi import FastAPI
import uvicorn
from pyrogram import Client
from bot.config import Config
from bot.database.models import db
from bot.utils.logger import logger
from bot.utils.queue import DownloadQueue

# Web server
web_app = FastAPI()

@web_app.get("/health")
async def health():
    return {"status": "ok"}

async def run_web():
    port = Config.PORT
    config = uvicorn.Config(web_app, host="0.0.0.0", port=port, log_level="info")
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
    await db.init_indexes()
    await download_queue.start_workers(count=3)
    logger.info("Bot is starting...")
    asyncio.create_task(run_web())
    await app.start()
    logger.info("Bot started successfully.")
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
    finally:
        asyncio.run(download_queue.stop_workers())
