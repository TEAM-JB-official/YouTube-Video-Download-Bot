import asyncio
from fastapi import FastAPI
import uvicorn
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.config import Config
from bot.database.models import db
from bot.utils.logger import logger

# ============ WEB SERVER ============
web_app = FastAPI()

@web_app.get("/")
@web_app.head("/")
async def root():
    return {"status": "ok"}

@web_app.get("/health")
@web_app.head("/health")
async def health():
    return {"status": "ok"}

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

# ---------- COMMAND HANDLERS ----------
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client: Client, message: Message):
    logger.info(f"✅ /start received from {message.from_user.id}")
    await message.reply_text(
        f"👋 Welcome {message.from_user.first_name}!\n\n"
        "I can download videos from YouTube.\n"
        "Send me a YouTube URL to get started.\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/help - Get help\n"
        "/account - Your account info\n"
        "/plan - Premium plans",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📚 Help", callback_data="help"),
             InlineKeyboardButton("💰 Plans", callback_data="plans")]
        ])
    )

@app.on_message(filters.command("help") & filters.private)
async def help_cmd(client: Client, message: Message):
    logger.info(f"✅ /help received from {message.from_user.id}")
    await message.reply_text(
        "📖 **Help**\n\n"
        "Send me a YouTube URL to download.\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/account - Your account info\n"
        "/plan - Premium plans\n"
        "/status - Queue status"
    )

@app.on_message(filters.command("account") & filters.private)
async def account_cmd(client: Client, message: Message):
    logger.info(f"✅ /account received from {message.from_user.id}")
    await message.reply_text(
        "📊 **Account Info**\n\n"
        f"ID: `{message.from_user.id}`\n"
        f"Name: {message.from_user.first_name}\n"
        "Premium: ❌ Free\n"
        "Daily Downloads: 0/5"
    )

@app.on_message(filters.command("plan") & filters.private)
async def plan_cmd(client: Client, message: Message):
    await message.reply_text(
        "💰 **Premium Plans**\n\n"
        "**Premium** – $5/month\n"
        "✅ Unlimited downloads\n"
        "✅ Priority queue\n"
        "✅ File size up to 2GB\n"
        "✅ Playlist downloads\n\n"
        "Contact @admin to purchase."
    )

@app.on_message(filters.command("status") & filters.private)
async def status_cmd(client: Client, message: Message):
    await message.reply_text("📋 **Queue Status**\n\nPending: 0\nProcessing: 0")

@app.on_message(filters.command("ping") & filters.private)
async def ping_cmd(client: Client, message: Message):
    logger.info(f"✅ /ping received from {message.from_user.id}")
    await message.reply_text("🏓 Pong! Bot is alive!")

# ---------- URL HANDLER ----------
@app.on_message(filters.private & filters.regex(r'^(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.'))
async def handle_url(client: Client, message: Message):
    logger.info(f"✅ URL received from {message.from_user.id}: {message.text}")
    await message.reply_text(
        "📥 **URL Received!**\n\n"
        f"URL: {message.text}\n\n"
        "I'm processing your request. Please wait..."
    )

# ---------- CALLBACK HANDLERS ----------
@app.on_callback_query()
async def handle_callback(client: Client, callback_query: CallbackQuery):
    logger.info(f"✅ Callback received: {callback_query.data}")
    if callback_query.data == "help":
        await callback_query.message.edit_text("Use /help for full command list.")
        await callback_query.answer()
    elif callback_query.data == "plans":
        await callback_query.message.edit_text("Use /plan for premium details.")
        await callback_query.answer()
    else:
        await callback_query.answer("Working on it...")

# ---------- DEBUG: Log all messages ----------
@app.on_message(filters.private)
async def debug_all(client: Client, message: Message):
    logger.info(f"📨 DEBUG - Message: '{message.text}' from {message.from_user.id}")

# ============ MAIN ============
async def main():
    try:
        # Connect to database
        await db.connect()
        logger.info("✅ Database connected.")
        
        # Start web server
        asyncio.create_task(run_web())
        logger.info(f"✅ Web server started on port {Config.PORT}")
        
        # Start Telegram bot
        logger.info("Starting Telegram bot...")
        await app.start()
        
        # 🔥 CRITICAL FIX: Delete any existing webhook to enable polling
        try:
            await app.delete_webhook()
            logger.info("✅ Webhook deleted (if any) – polling is now active.")
        except Exception as e:
            logger.warning(f"Could not delete webhook: {e}")
        
        # Get bot info
        me = await app.get_me()
        logger.info(f"✅ BOT ONLINE! Username: @{me.username}, ID: {me.id}")
        
        # Send test message to admin
        if Config.ADMIN_IDS:
            try:
                await app.send_message(
                    Config.ADMIN_IDS[0],
                    f"✅ Bot is online and polling!\n\n"
                    f"Username: @{me.username}\n"
                    f"ID: {me.id}\n\n"
                    "Send /start to test."
                )
                logger.info(f"✅ Test message sent to admin")
            except Exception as e:
                logger.error(f"Failed to send test message: {e}")
        
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
