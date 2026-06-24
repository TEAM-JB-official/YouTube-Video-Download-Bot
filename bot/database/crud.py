from datetime import datetime, timedelta
from typing import Optional, List
from bot.database.models import db

# ------------------- Users -------------------
async def create_user(user_data: dict) -> dict:
    user = {
        "user_id": user_data["user_id"],
        "username": user_data.get("username"),
        "first_name": user_data.get("first_name"),
        "last_name": user_data.get("last_name"),
        "is_premium": False,
        "premium_expiry": None,
        "daily_count": 0,
        "last_download_date": datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
        "banned": False,
        "thumbnail_file_id": None,
        "upload_chat_id": None,
        "settings": {},
        "cookies_encrypted": None,
        "cookie_uploaded_at": None,
        "use_global_cookies": True,
        "created_at": datetime.utcnow()
    }
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": user}, upsert=True)
    return await get_user(user["user_id"])

async def get_user(user_id: int) -> Optional[dict]:
    return await db.users.find_one({"user_id": user_id})

async def update_user(user_id: int, update: dict):
    await db.users.update_one({"user_id": user_id}, {"$set": update})

async def get_all_users(filter_criteria: dict = {}) -> List[dict]:
    cursor = db.users.find(filter_criteria)
    return await cursor.to_list(length=None)

async def count_users(filter_criteria: dict = {}) -> int:
    return await db.users.count_documents(filter_criteria)

# ------------------- Premium -------------------
async def set_premium(user_id: int, days: int):
    expiry = datetime.utcnow() + timedelta(days=days)
    await update_user(user_id, {"is_premium": True, "premium_expiry": expiry})

async def remove_premium(user_id: int):
    await update_user(user_id, {"is_premium": False, "premium_expiry": None})

async def check_premium(user_id: int) -> bool:
    user = await get_user(user_id)
    if not user:
        return False
    if user.get("is_premium") and user.get("premium_expiry") and user["premium_expiry"] > datetime.utcnow():
        return True
    if user.get("is_premium"):
        await remove_premium(user_id)
    return False

# ------------------- Downloads -------------------
async def add_download_log(user_id: int, url: str, file_name: str, file_size: int, format_type: str, uploaded_to: str):
    log = {
        "user_id": user_id,
        "url": url,
        "file_name": file_name,
        "file_size": file_size,
        "format_type": format_type,
        "uploaded_to": uploaded_to,
        "timestamp": datetime.utcnow()
    }
    await db.downloads.insert_one(log)

async def get_user_downloads(user_id: int, limit: int = 20) -> List[dict]:
    cursor = db.downloads.find({"user_id": user_id}).sort("timestamp", -1).limit(limit)
    return await cursor.to_list(length=limit)

async def increment_daily_count(user_id: int):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    await db.users.update_one(
        {"user_id": user_id},
        {"$inc": {"daily_count": 1}, "$set": {"last_download_date": today}}
    )

# ------------------- Thumbnail -------------------
async def set_user_thumbnail(user_id: int, file_id: str):
    await update_user(user_id, {"thumbnail_file_id": file_id})

async def remove_user_thumbnail(user_id: int):
    await update_user(user_id, {"thumbnail_file_id": None})

# ------------------- Upload Destination -------------------
async def set_user_upload_chat(user_id: int, chat_id: int):
    await update_user(user_id, {"upload_chat_id": chat_id})

async def remove_user_upload_chat(user_id: int):
    await update_user(user_id, {"upload_chat_id": None})

# ------------------- Cookies -------------------
async def set_user_cookies(user_id: int, encrypted_cookies: str):
    await update_user(user_id, {"cookies_encrypted": encrypted_cookies, "cookie_uploaded_at": datetime.utcnow()})

async def remove_user_cookies(user_id: int):
    await update_user(user_id, {"cookies_encrypted": None, "cookie_uploaded_at": None})

async def set_owner_cookies(encrypted_cookies: str):
    await db.global_cookies.update_one(
        {"type": "owner"},
        {"$set": {"cookies_encrypted": encrypted_cookies, "updated_at": datetime.utcnow()}},
        upsert=True
    )

async def get_owner_cookies() -> Optional[str]:
    doc = await db.global_cookies.find_one({"type": "owner"})
    return doc.get("cookies_encrypted") if doc else None

async def remove_owner_cookies():
    await db.global_cookies.delete_one({"type": "owner"})

# ------------------- Ban -------------------
async def ban_user(user_id: int):
    await update_user(user_id, {"banned": True})

async def unban_user(user_id: int):
    await update_user(user_id, {"banned": False})

async def is_user_banned(user_id: int) -> bool:
    user = await get_user(user_id)
    return user.get("banned", False) if user else False

# ------------------- System Log -------------------
async def add_system_log(level: str, message: str, user_id: Optional[int] = None, extra: dict = None):
    log = {
        "level": level,
        "message": message,
        "user_id": user_id,
        "extra": extra or {},
        "timestamp": datetime.utcnow()
    }
    await db.logs.insert_one(log)
