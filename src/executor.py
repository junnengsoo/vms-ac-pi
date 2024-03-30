from concurrent.futures import ThreadPoolExecutor

# Define the maximum number of threads in the pool
MAX_WORKERS = 8

# Create a ThreadPoolExecutor to be shared across modules
thread_pool_executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
