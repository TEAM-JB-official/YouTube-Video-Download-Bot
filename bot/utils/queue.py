import asyncio
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable
from bot.config import Config
from bot.utils.logger import logger

@dataclass
class DownloadJob:
    user_id: int
    url: str
    format_type: str          # 'video', 'audio', 'playlist'
    quality: str
    rename: Optional[str]
    caption: Optional[str]
    upload_chat: Optional[int]
    is_premium: bool
    priority: int = 0
    retries: int = 0
    callback: Optional[Callable[[dict], Awaitable[None]]] = None

class DownloadQueue:
    def __init__(self):
        self.queue = asyncio.PriorityQueue(maxsize=Config.QUEUE_MAX_SIZE)
        self.processing = set()
        self.pending_count = 0
        self.workers = []
        self.running = False

    async def add_job(self, job: DownloadJob):
        """Add a download job to the queue."""
        # Premium users get higher priority (lower number)
        priority = -10 if job.is_premium else 0
        await self.queue.put((priority, job))
        self.pending_count += 1
        logger.info(f"Job added for user {job.user_id}: {job.url} (priority {priority})")

    async def start_workers(self, count: int = 3):
        """Start the specified number of worker coroutines."""
        self.running = True
        for _ in range(count):
            worker = asyncio.create_task(self._worker())
            self.workers.append(worker)
        logger.info(f"Started {count} download workers.")

    async def stop_workers(self):
        """Stop all worker coroutines gracefully."""
        self.running = False
        for w in self.workers:
            w.cancel()
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        logger.info("All download workers stopped.")

    async def _worker(self):
        """Worker loop that processes jobs from the queue."""
        # Lazy imports to avoid circular dependencies
        from bot.utils.ytdl import YouTubeDL
        from bot.database.crud import add_system_log

        while self.running:
            try:
                # Wait for a job with a timeout to allow checking self.running
                priority, job = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                self.pending_count -= 1
                self.processing.add(job.user_id)

                try:
                    ytdl = YouTubeDL(user_id=job.user_id, is_premium=job.is_premium)
                    success = await ytdl.process_job(job)

                    if not success and job.retries < Config.MAX_RETRIES:
                        job.retries += 1
                        await self.add_job(job)
                        logger.warning(f"Retrying job for user {job.user_id} (attempt {job.retries})")
                    elif not success:
                        logger.error(f"Job failed after {Config.MAX_RETRIES} attempts: {job.url}")
                        await add_system_log("ERROR", f"Download failed: {job.url}", job.user_id)
                except Exception as e:
                    logger.error(f"Worker error: {e}")
                finally:
                    self.processing.discard(job.user_id)
                    self.queue.task_done()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected worker error: {e}")
                continue

# ============ GLOBAL INSTANCE ============
# This instance is imported and used across the bot
download_queue = DownloadQueue()
