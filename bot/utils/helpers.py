import os
import tempfile
from cryptography.fernet import Fernet
from bot.config import Config

fernet = Fernet(Config.COOKIE_ENCRYPTION_KEY.encode()) if Config.COOKIE_ENCRYPTION_KEY else None

def encrypt_cookies(plain_text: str) -> str:
    if not fernet:
        raise ValueError("COOKIE_ENCRYPTION_KEY not set")
    return fernet.encrypt(plain_text.encode()).decode()

def decrypt_cookies(encrypted: str) -> str:
    if not fernet:
        raise ValueError("COOKIE_ENCRYPTION_KEY not set")
    return fernet.decrypt(encrypted.encode()).decode()

def validate_cookie_content(content: str) -> bool:
    lines = content.splitlines()
    for line in lines:
        if line.startswith('#') or not line.strip():
            continue
        parts = line.strip().split('\t')
        if len(parts) >= 7:
            return True
    return False

def create_temp_cookie_file(content: str) -> str:
    fd, path = tempfile.mkstemp(suffix='.txt', prefix='cookies_')
    with os.fdopen(fd, 'w') as f:
        f.write(content)
    return path

def format_file_size(size_bytes: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"

def progress_bar(current: int, total: int, width: int = 20) -> str:
    if total == 0:
        return "0%"
    percent = current / total
    filled = int(percent * width)
    bar = '█' * filled + '░' * (width - filled)
    return f"{bar} {percent*100:.1f}%"
