import asyncio
from fastapi import FastAPI, Response
import uvicorn
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.config import Config
from bot.database.models import db
from bot.utils.logger import logger
from bot.utils.queue import DownloadQueue

# Web server
web_app = FastAPI()

@web_app.get("/")
@web_app.head("/")
async def root():
    return {"status": "ok", "service": "YouTube Downloader Bot", "version": "1.0.0"}

@web_app.get("/health")
@web_app.head("/health")
async def health():
    try:
        await db.connect()
        await db.db.command('ping')
        return {"status": "ok", "database": "connected", "version": "1.0.0"}
    except Exception as e:
        return {"status": "error", "database": "disconnected", "error": str(e)}

async def run_web():
    config = uvicorn.Config(web_app, host="0.0.0.0", port=Config.PORT, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

# Telegram bot
app = Client(
    "youtube_bot",
    bot_token=Config.BOT_TOKEN,
    api_id=Config.API_ID,
    api_hash=Config.API_HASH
)

download_queue = DownloadQueue()

# ---------- DIRECT HANDLERS (no plugins) ----------
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message: Message):
    from bot.handlers.user import start_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message: Message):
    from bot.handlers.user import help_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("account") & filters.private)
async def account_cmd(client, message: Message):
    from bot.handlers.user import account_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("plan") & filters.private)
async def plan_cmd(client, message: Message):
    from bot.handlers.user import plan_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("myplan") & filters.private)
async def myplan_cmd(client, message: Message):
    from bot.handlers.user import myplan_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("terms") & filters.private)
async def terms_cmd(client, message: Message):
    from bot.handlers.user import terms_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("status") & filters.private)
async def status_cmd(client, message: Message):
    from bot.handlers.user import status_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("setthumbnail") & filters.private)
async def set_thumbnail_cmd(client, message: Message):
    from bot.handlers.thumbnail import set_thumbnail_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("remthumbnail") & filters.private)
async def rem_thumbnail_cmd(client, message: Message):
    from bot.handlers.thumbnail import rem_thumbnail_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("setchat") & filters.private)
async def set_chat_cmd(client, message: Message):
    from bot.handlers.upload import set_chat_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("removechat") & filters.private)
async def remove_chat_cmd(client, message: Message):
    from bot.handlers.upload import remove_chat_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("setcookies") & filters.private)
async def set_cookies_cmd(client, message: Message):
    from bot.handlers.cookies import set_cookies_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("removecookies") & filters.private)
async def remove_cookies_cmd(client, message: Message):
    from bot.handlers.cookies import remove_cookies_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("cookieinfo") & filters.private)
async def cookie_info_cmd(client, message: Message):
    from bot.handlers.cookies import cookie_info_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("cookiecheck") & filters.private)
async def cookie_check_cmd(client, message: Message):
    from bot.handlers.cookies import cookie_check_cmd as handler
    await handler(client, message)

@app.on_message(filters.private & filters.regex(r'^(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.'))
async def handle_url(client, message: Message):
    from bot.handlers.download import handle_url as handler
    await handler(client, message)

# Admin Commands
@app.on_message(filters.command("stats") & filters.private)
async def stats_cmd(client, message: Message):
    from bot.handlers.admin import stats_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("ban") & filters.private)
async def ban_cmd(client, message: Message):
    from bot.handlers.admin import ban_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("unban") & filters.private)
async def unban_cmd(client, message: Message):
    from bot.handlers.admin import unban_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("users") & filters.private)
async def users_cmd(client, message: Message):
    from bot.handlers.admin import users_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("get") & filters.private)
async def get_user_cmd(client, message: Message):
    from bot.handlers.admin import get_user_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_cmd(client, message: Message):
    from bot.handlers.admin import broadcast_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("addpremium") & filters.private)
async def add_premium_cmd(client, message: Message):
    from bot.handlers.premium import add_premium_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("removepremium") & filters.private)
async def remove_premium_cmd(client, message: Message):
    from bot.handlers.premium import remove_premium_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("check") & filters.private)
async def check_cmd(client, message: Message):
    from bot.handlers.premium import check_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("getpremium") & filters.private)
async def get_premium_cmd(client, message: Message):
    from bot.handlers.premium import get_premium_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("premiumstats") & filters.private)
async def premium_stats_cmd(client, message: Message):
    from bot.handlers.premium import premium_stats_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("setownercookies") & filters.private)
async def set_owner_cookies_cmd(client, message: Message):
    from bot.handlers.cookies import set_owner_cookies_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("removeownercookies") & filters.private)
async def remove_owner_cookies_cmd(client, message: Message):
    from bot.handlers.cookies import remove_owner_cookies_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("checkcookies") & filters.private)
async def check_cookies_cmd(client, message: Message):
    from bot.handlers.cookies import check_cookies_cmd as handler
    await handler(client, message)

@app.on_message(filters.command("cookie_stats") & filters.private)
async def cookie_stats_cmd(client, message: Message):
    from bot.handlers.cookies import cookie_stats_cmd as handler
    await handler(client, message)

# ---------- Callbacks ----------
@app.on_callback_query()
async def handle_callback(client, callback_query):
    from bot.handlers.download import download_callback, quality_callback
    from bot.handlers.callback import help_callback, plans_callback
    
    data = callback_query.data
    
    if data.startswith("dl_"):
        await download_callback(client, callback_query)
    elif data.startswith("q_"):
        await quality_callback(client, callback_query)
    elif data == "help":
        await help_callback(client, callback_query)
    elif data == "plans":
        await plans_callback(client, callback_query)
    else:
        await callback_query.answer("Unknown action")

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
