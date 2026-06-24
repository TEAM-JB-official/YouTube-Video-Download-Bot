import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    API_ID = int(os.getenv("API_ID", "25331263"))
    API_HASH = os.getenv("API_HASH", "cab85305bf85125a2ac053210bcd1030")
    
    MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://rs92573993688:pVf4EeDuRi2o92ex@cluster0.9u29q.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    DB_NAME = os.getenv("DB_NAME", "youtube_bot")
    
    ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "1955406483").split(",") if x.strip()]
    
    DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH", "./downloads")
    LOG_PATH = os.getenv("LOG_PATH", "./bot/logs")
    
    DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", 5))
    MAX_FILE_SIZE_FREE = int(os.getenv("MAX_FILE_SIZE_FREE", 52428800))
    MAX_FILE_SIZE_PREMIUM = int(os.getenv("MAX_FILE_SIZE_PREMIUM", 2147483648))
    MAX_BATCH_URLS = int(os.getenv("MAX_BATCH_URLS", 10))
    QUEUE_MAX_SIZE = int(os.getenv("QUEUE_MAX_SIZE", 100))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
    
    COOKIE_ENCRYPTION_KEY = os.getenv("COOKIE_ENCRYPTION_KEY")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    PORT = int(os.getenv("PORT", 8000))
