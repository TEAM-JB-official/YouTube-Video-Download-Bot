import os
import tempfile
from cryptography.fernet import Fernet
from bot.config import Config
from bot.utils.logger import logger

_fernet = None

def get_fernet():
    global _fernet
    if _fernet is None:
        if not Config.COOKIE_ENCRYPTION_KEY:
            logger.warning("COOKIE_ENCRYPTION_KEY not set. Cookie encryption disabled.")
            return None
        try:
            _fernet = Fernet(Config.COOKIE_ENCRYPTION_KEY.encode())
        except Exception as e:
            logger.error(f"Failed to initialize Fernet: {e}. Cookie encryption disabled.")
            return None
    return _fernet

def encrypt_cookies(plain_text: str) -> str:
    fernet = get_fernet()
    if not fernet:
        logger.warning("Encryption disabled, storing cookies in plain text!")
        return plain_text
    return fernet.encrypt(plain_text.encode()).decode()

def decrypt_cookies(encrypted: str) -> str:
    fernet = get_fernet()
    if not fernet:
        logger.warning("Encryption disabled, returning cookies as plain text!")
        return encrypted
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
