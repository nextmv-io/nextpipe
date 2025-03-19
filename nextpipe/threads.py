import multiprocessing
import threading
import traceback
from typing import Callable, Optional


class Job:
    def __init__(
        self,
        target: Callable,
        callback: Callable,
        args: Optional[list] = None,
        reference: any = None,
    ):
        self.target = target
        self.callback = callback
        self.args = args
        self.reference = reference
        self.done = False
        self.result = None
        self.error = None

    def run(self):
        if self.args:
            self.result = self.target(*self.args)
        else:
            self.result = self.target()
        self.done = True


class Pool:
    def __init__(self, max_threads: int = 0):
        if max_threads <= 0:
            max_threads = multiprocessing.cpu_count()
        self.max_threads = max_threads
        self.counter = 0  # Used to assign unique IDs to threads
        self.waiting = {}
        self.running = {}
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)

    def run(self, job: Job) -> None:
        """
        The run method submits a job to the pool. The job is executed by a worker thread.
        """
        with self.lock:
            self.counter += 1
            thread_id = self.counter
            self.waiting[thread_id] = job

        def worker(job: Job, thread_id: int):
            try:
                job.run()
            except Exception as e:
                job.error = f"Error in thread {thread_id}: {e}\n{traceback.format_exc()}"
            finally:
                with self.lock:
                    self.running.pop(thread_id, None)
                    self.cond.notify_all()  # Notify others that a thread is available
                if job.callback:
                    job.callback(job)

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

    def wait_one(self) -> None:
        """
        Wait for one job to finish.
        """
        with self.lock:
            self.cond.wait()

    def join(self) -> None:
        """
        Wait for all jobs to finish.
        """
        with self.cond:
            while self.waiting or self.running:
                self.cond.wait()  # Wait until all jobs are finished
