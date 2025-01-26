import threading
import time
from typing import Callable, Optional


class Job:
    def __init__(self, target: Callable, args: Optional[tuple] = None):
        self.target = target
        self.args = args
        self.done = False
        self.result = None

    def run(self):
        if self.args:
            self.result = self.target(*self.args)
        else:
            self.result = self.target()
        self.done = True


class Pool:
    def __init__(self, max_threads: int):
        self.max_threads = max_threads
        self.counter = 0  # Used to assign unique IDs to threads
        self.waiting = {}
        self.running = {}
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)

    def run(self, job: Job) -> None:
        with self.lock:
            self.counter += 1
            thread_id = self.counter
            self.waiting[thread_id] = job

        def worker(job: Job, thread_id: int):
            try:
                job.run()
            finally:
                with self.lock:
                    self.running.pop(thread_id, None)
                    self.cond.notify_all()  # Notify others that a thread is available

        while True:
            with self.lock:
                if len(self.running) < self.max_threads:
                    # Move job from waiting to running
                    thread = threading.Thread(target=worker, args=(job, thread_id))
                    self.running[thread_id] = thread
                    self.waiting.pop(thread_id, None)
                    thread.start()
                    break  # Successfully assigned the job to a thread
                else:
                    self.cond.wait()  # Wait until a thread is available

    def join(self) -> None:
        with self.cond:
            while self.waiting or self.running:
                self.cond.wait()  # Wait until all jobs are finished


def test_pool():
    def target(*args):
        print(f"Running job with args: {args}")
        time.sleep(0.5)  # Simulate work

    pool = Pool(2)
    for i in range(1, 7):  # Submit 6 jobs
        pool.run(Job(target, (i,)))
    pool.join()
    print("All jobs completed.")


if __name__ == "__main__":
    test_pool()
