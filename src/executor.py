import gc
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import logging

# Create a logger
logger = logging.getLogger(__name__)

# Set the level of logging. It can be DEBUG, INFO, WARNING, ERROR, CRITICAL
logger.setLevel(logging.DEBUG)

# Create a file handler for outputting log messages to a file
file_handler = logging.FileHandler('/home/etlas/ThreadPool.log')

# Create a formatter and add it to the handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(file_handler)


"""A class that inherits ThreadPoolExecutor for verbosity"""
class ThreadPoolMonitor:
    def __init__(self, max_workers):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.lock = threading.Lock()
        self.active_tasks = 0
        self.completed_tasks = 0
        self.submitted_tasks = 0
        self.monitoring_thread = threading.Thread(target=self._monitor_queue_length)
        self.monitoring_thread.daemon = True  # This makes the thread exit when the main program exits
        self.monitoring_thread.start()

    def submit(self, func, *args, **kwargs):
        with self.lock:
            self.submitted_tasks += 1
            self.active_tasks += 1
        logging.info("Task submitted. Total submitted: {}".format(self.submitted_tasks))
        future = self.executor.submit(self._run, func, *args, **kwargs)
        future.add_done_callback(self._task_complete)
        return future

    def _run(self, func, *args, **kwargs):
        logging.info("Thread started running a task.")
        result = func(*args, **kwargs)
        logging.info("Thread completed running a task.")
        return result

    def _task_complete(self, future):
        with self.lock:
            self.active_tasks -= 1
            self.completed_tasks += 1
        logging.info("Task completed. Total completed: {}".format(self.completed_tasks))

    def get_queue_length(self):
        with self.lock:
            return self.submitted_tasks - (self.active_tasks + self.completed_tasks)

    def _monitor_queue_length(self):
        while True:
            queue_length = self.get_queue_length()
            logging.info(f"Current queue length: {queue_length}")
            time.sleep(60*30)  # Interval between logs can be adjusted
            gc.collect()

    def shutdown(self, wait=True):
        logging.info("Shutting down thread pool.")
        self.executor.shutdown(wait=wait)


# Usage
max_workers = 16
thread_pool_executor = ThreadPoolMonitor(max_workers=max_workers)
