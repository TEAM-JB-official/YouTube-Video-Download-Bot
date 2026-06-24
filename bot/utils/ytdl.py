import os
import asyncio
import yt_dlp
from datetime import datetime
from typing import Optional, Tuple
from bot.database.crud import get_user, get_owner_cookies, add_download_log, increment_daily_count
from bot.database.models import db
from bot.config import Config
from bot.utils.helpers import decrypt_cookies, create_temp_cookie_file
from bot.utils.logger import logger
from bot.handlers.upload import upload_file

class YouTubeDL:
    def __init__(self, user_id: int, is_premium: bool):
        self.user_id = user_id
        self.is_premium = is_premium
        self.progress = {}

    async def get_cookie_file(self) -> Optional[str]:
        # 1. Owner cookies
        owner_enc = await get_owner_cookies()
        if owner_enc:
            try:
                owner_content = decrypt_cookies(owner_enc)
                if owner_content and len(owner_content) > 10:
                    return create_temp_cookie_file(owner_content)
            except Exception as e:
                logger.error(f"Owner cookie decryption failed: {e}")
        # 2. User cookies
        user = await get_user(self.user_id)
        if user and user.get('cookies_encrypted'):
            try:
                user_content = decrypt_cookies(user['cookies_encrypted'])
                if user_content and len(user_content) > 10:
                    return create_temp_cookie_file(user_content)
            except Exception as e:
                logger.error(f"User cookie decryption failed: {e}")
        return None

    async def process_job(self, job) -> bool:
        if not self.is_premium:
            user = await get_user(self.user_id)
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            if user.get('last_download_date') != today:
                await db.db.users.update_one({"user_id": self.user_id}, {"$set": {"daily_count": 0, "last_download_date": today}})
            if user.get('daily_count', 0) >= Config.DAILY_LIMIT:
                logger.warning(f"User {self.user_id} daily limit reached.")
                return False

        if job.format_type == 'audio':
            result = await self.download_audio(job)
        elif job.format_type == 'playlist':
            result = await self.download_playlist(job)
        else:
            result = await self.download_video(job)

        if not result:
            return False
        file_path, info = result
        size = os.path.getsize(file_path)
        max_size = Config.MAX_FILE_SIZE_PREMIUM if self.is_premium else Config.MAX_FILE_SIZE_FREE
        if size > max_size:
            logger.warning(f"File too large ({size} > {max_size}) for user {self.user_id}")
            os.remove(file_path)
            return False

        upload_chat = job.upload_chat if job.upload_chat else self.user_id
        caption = job.caption or self.build_caption(info)
        thumbnail = await self.get_thumbnail(info) or await self.get_user_thumbnail()
        success = await upload_file(self.user_id, file_path, upload_chat, caption, thumbnail)
        if success:
            await increment_daily_count(self.user_id)
            await add_download_log(self.user_id, job.url, os.path.basename(file_path), size, job.format_type, str(upload_chat))
            os.remove(file_path)
            return True
        else:
            os.remove(file_path)
            return False

    async def download_video(self, job) -> Optional[Tuple[str, dict]]:
        cookie_file = await self.get_cookie_file()
        opts = {
            'format': job.quality if job.quality != 'best' else 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'outtmpl': os.path.join(Config.DOWNLOAD_PATH, str(self.user_id), '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'quiet': True, 'no_warnings': True, 'ignoreerrors': True,
            'continuedl': True, 'nooverwrites': True,
            'writesubtitles': True, 'writeautomaticsub': True,
            'subtitleslangs': ['en'], 'writeinfojson': True,
            'writethumbnail': True, 'embedthumbnail': True, 'embedmetadata': True,
        }
        if cookie_file:
            opts['cookiefile'] = cookie_file
        if job.rename:
            opts['outtmpl'] = os.path.join(Config.DOWNLOAD_PATH, str(self.user_id), f"{job.rename}.%(ext)s")
        os.makedirs(os.path.join(Config.DOWNLOAD_PATH, str(self.user_id)), exist_ok=True)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, job.url, download=True)
                file_path = ydl.prepare_filename(info)
                if not os.path.exists(file_path):
                    for ext in ['.mp4', '.mkv', '.webm']:
                        test_path = file_path.rsplit('.', 1)[0] + ext
                        if os.path.exists(test_path):
                            file_path = test_path
                            break
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"File not found for {job.url}")
                return file_path, info
        except Exception as e:
            logger.error(f"yt-dlp error: {e}")
            return None
        finally:
            if cookie_file and os.path.exists(cookie_file):
                os.remove(cookie_file)

    async def download_audio(self, job) -> Optional[Tuple[str, dict]]:
        cookie_file = await self.get_cookie_file()
        quality = job.quality
        preferred_codec = 'mp3' if 'mp3' in quality else 'm4a'
        bitrate = quality.replace('mp3', '').replace('m4a', '') or '192'
        opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': preferred_codec,
                'preferredquality': bitrate,
            }],
            'outtmpl': os.path.join(Config.DOWNLOAD_PATH, str(self.user_id), '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'quiet': True, 'no_warnings': True, 'ignoreerrors': True,
            'continuedl': True, 'nooverwrites': True,
            'writethumbnail': True, 'embedthumbnail': True, 'embedmetadata': True,
        }
        if cookie_file:
            opts['cookiefile'] = cookie_file
        if job.rename:
            opts['outtmpl'] = os.path.join(Config.DOWNLOAD_PATH, str(self.user_id), f"{job.rename}.%(ext)s")
        os.makedirs(os.path.join(Config.DOWNLOAD_PATH, str(self.user_id)), exist_ok=True)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, job.url, download=True)
                file_path = ydl.prepare_filename(info)
                if not os.path.exists(file_path):
                    base = file_path.rsplit('.', 1)[0]
                    for ext in ['.mp3', '.m4a']:
                        test_path = base + ext
                        if os.path.exists(test_path):
                            file_path = test_path
                            break
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"Audio file not found for {job.url}")
                return file_path, info
        except Exception as e:
            logger.error(f"yt-dlp audio error: {e}")
            return None
        finally:
            if cookie_file and os.path.exists(cookie_file):
                os.remove(cookie_file)

    async def download_playlist(self, job) -> Optional[Tuple[str, dict]]:
        from bot.utils.queue import DownloadJob
        from bot.main import download_queue
        cookie_file = await self.get_cookie_file()
        opts = {'extract_flat': True, 'quiet': True, 'no_warnings': True}
        if cookie_file:
            opts['cookiefile'] = cookie_file
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, job.url, download=False)
                if 'entries' in info:
                    for entry in info['entries']:
                        sub_job = DownloadJob(
                            user_id=job.user_id,
                            url=entry['url'],
                            format_type='video',
                            quality=job.quality,
                            rename=job.rename,
                            caption=job.caption,
                            upload_chat=job.upload_chat,
                            is_premium=job.is_premium,
                            priority=job.priority
                        )
                        await download_queue.add_job(sub_job)
                    return True
                else:
                    return await self.download_video(job)
        except Exception as e:
            logger.error(f"Playlist error: {e}")
            return None
        finally:
            if cookie_file and os.path.exists(cookie_file):
                os.remove(cookie_file)

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total:
                self.progress[d['filename']] = d['downloaded_bytes'] / total
        elif d['status'] == 'finished':
            self.progress[d['filename']] = 1.0

    async def get_thumbnail(self, info) -> Optional[str]:
        thumb = info.get('thumbnail')
        if thumb:
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(thumb) as resp:
                        if resp.status == 200:
                            path = os.path.join(Config.DOWNLOAD_PATH, str(self.user_id), 'thumb.jpg')
                            with open(path, 'wb') as f:
                                f.write(await resp.read())
                            return path
            except:
                pass
        return None

    async def get_user_thumbnail(self) -> Optional[str]:
        user = await get_user(self.user_id)
        return user.get('thumbnail_file_id') if user else None

    def build_caption(self, info) -> str:
        title = info.get('title', 'Unknown')
        duration = info.get('duration', 'N/A')
        uploader = info.get('uploader', 'Unknown')
        views = info.get('view_count', 'N/A')
        return f"📹 {title}\n👤 {uploader}\n⏱ {duration}s\n👁 {views} views"
