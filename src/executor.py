import gc
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import logging

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('/home/etlas/ThreadPool.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

class ThreadPoolMonitor:
    def __init__(self, max_workers):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.lock = threading.Lock()
        self.task_id_counter = 0
        self.active_tasks = {}
        self.monitoring_thread = threading.Thread(target=self._monitor_queue_length)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()

    def submit(self, func, *args, **kwargs):
        with self.lock:
            task_id = self.task_id_counter
            self.task_id_counter += 1
            self.active_tasks[task_id] = func.__name__  # Track task by name
        logger.info(f"Task {task_id} submitted: {func.__name__}. Total submitted: {len(self.active_tasks)}")
        future = self.executor.submit(self._run, task_id, func, *args, **kwargs)
        future.add_done_callback(lambda f: self._task_complete(task_id, f))
        return future

    def _run(self, task_id, func, *args, **kwargs):
        logger.info(f"Thread started running task {task_id}: {func.__name__}")
        result = func(*args, **kwargs)
        logger.info(f"Thread completed task {task_id}: {func.__name__}")
        return result

    def _task_complete(self, task_id, future):
        with self.lock:
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
        logger.info(f"Task {task_id} completed. Total remaining: {len(self.active_tasks)}")

    def get_queue_length(self):
        with self.lock:
            return len(self.active_tasks)

    def _monitor_queue_length(self):
        while True:
            queue_length = self.get_queue_length()
            logger.info(f"Current queue length: {queue_length}")
            time.sleep(60*30)  # Every 30 minutes
            gc.collect()

    def shutdown(self, wait=True):
        logger.info("Shutting down thread pool.")
        self.executor.shutdown(wait=wait)

# Usage
max_workers = 16
thread_pool_executor = ThreadPoolMonitor(max_workers=max_workers)
