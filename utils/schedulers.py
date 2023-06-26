from utils.common import singleton_with_lock
from apscheduler.schedulers.asyncio import AsyncIOScheduler

@singleton_with_lock
class AsyncIOSchedulerWrapper:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def add_job(self, *args, **kwargs):
        return self.scheduler.add_job(*args, **kwargs)
    
    def start(self):
        self.scheduler.start()