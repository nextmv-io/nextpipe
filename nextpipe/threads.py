"""
Thread management utilities for parallel job execution.

This module provides classes for managing multithreaded job execution.

Classes
-------
Job
    A callable job that can be submitted to a thread pool.
Pool
    A thread pool for executing jobs in parallel.

The module also provides a thread local storage variable for thread-specific data.
"""

import threading
from collections.abc import Callable
from typing import Any, Optional

DEFAULT_MAX_THREADS = 24
"""
Default maximum number of threads for the thread pool. This is set to 24, to allow
parallel execution of sub-runs in the pipeline (as these are typically not CPU-bound). A
lower value more fit for the respective hardware is recommended when running many
CPU-bound steps.
"""

thread_local = threading.local()
"""Thread-local storage.

This variable provides thread-specific storage that can be used to store data
that is specific to a particular thread.
"""


class Job:
    """A callable job that can be submitted to a thread pool.

    This class represents a job that can be executed by a worker thread in a
    thread pool. It wraps a target callable with arguments and callback functions
    that are executed when the job starts and completes.

    Parameters
    ----------
    target : Callable
        The function to be executed by the job.
    start_callback : Callable
        Function to be called when the job starts. Takes the job as a parameter.
    done_callback : Callable
        Function to be called when the job completes. Takes the job as a parameter.
    args : Optional[list], optional
        Arguments to be passed to the target function, by default None.
    name : str, optional
        Name for the job, by default None.
    reference : Any, optional
        Reference to any object associated with this job, by default None.

    Attributes
    ----------
    target : Callable
        The function to be executed by the job.
    start_callback : Callable
        Function to be called when the job starts.
    done_callback : Callable
        Function to be called when the job completes.
    args : Optional[list]
        Arguments to be passed to the target function.
    name : str
        Name for the job.
    reference : Any
        Reference to any object associated with this job.
    done : bool
        Whether the job has completed.
    result : Any
        The result of the job execution.
    error : Exception
        Any exception that occurred during job execution.

    Examples
    --------
    >>> def my_task(x, y):
    ...     return x + y
    >>> def on_start(job):
    ...     print(f"Starting job {job.name}")
    >>> def on_done(job):
    ...     print(f"Job {job.name} completed with result: {job.result}")
    >>> job = Job(
    ...     target=my_task,
    ...     start_callback=on_start,
    ...     done_callback=on_done,
    ...     args=[5, 10],
    ...     name="addition_job"
    ... )
    """

    def __init__(
        self,
        target: Callable,
        start_callback: Callable,
        done_callback: Callable,
        args: Optional[list] = None,
        name: str = None,
        reference: Any = None,
    ):
        self.target = target
        self.start_callback = start_callback
        self.done_callback = done_callback
        self.args = args
        self.name = name
        self.reference = reference
        self.done = False
        self.result = None
        self.error = None

    def run(self):
        """Execute the job's target function.

        Executes the target function with the provided arguments (if any)
        and sets the done flag to True. The result of the execution is
        stored in the result attribute.
        """

        if self.args:
            self.result = self.target(*self.args)
        else:
            self.result = self.target()
        self.done = True


class Pool:
    """A thread pool for executing jobs in parallel.

    This class provides a thread pool for executing jobs in parallel. The number
    of threads is limited by the max_threads parameter. Jobs are queued and
    executed as threads become available.

    Parameters
    ----------
    max_threads : int, optional
        Maximum number of threads to use, by default 0 (uses CPU count).

    Attributes
    ----------
    max_threads : int
        Maximum number of threads in the pool.
    counter : int
        Counter used to assign unique IDs to threads.
    waiting : dict
        Dictionary of jobs waiting to be executed, keyed by thread ID.
    running : dict
        Dictionary of running thread objects, keyed by thread ID.
    error : Exception
        Any exception that occurred during job execution.
    lock : threading.Lock
        Lock for thread synchronization.
    cond : threading.Condition
        Condition variable for thread synchronization.

    Examples
    --------
    >>> def task(x):
    ...     return x * 2
    >>> def on_start(job):
    ...     print(f"Starting job")
    >>> def on_done(job):
    ...     print(f"Result: {job.result}")
    >>> pool = Pool(max_threads=4)
    >>> for i in range(10):
    ...     job = Job(
    ...         target=task,
    ...         start_callback=on_start,
    ...         done_callback=on_done,
    ...         args=[i]
    ...     )
    ...     pool.run(job)
    >>> pool.join()  # Wait for all jobs to finish
    """

    def __init__(self, max_threads: int = 0):
        """Initialize a thread pool.

        Parameters
        ----------
        max_threads : int, optional
            Maximum number of threads to use, by default 0.
            If <= 0, DEFAULT_MAX_THREADS is used.
        """

        if max_threads <= 0:
            max_threads = DEFAULT_MAX_THREADS
        self.max_threads = max_threads
        self.counter = 0  # Used to assign unique IDs to threads
        self.waiting = {}
        self.running = {}
        self.error = None
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)

    def run(self, job: Job) -> None:
        """Submit a job to the thread pool for execution.

        The job is first placed in the waiting queue and then assigned to a worker
        thread when one becomes available. If all threads are busy, the method will
        wait until a thread becomes available.

        Parameters
        ----------
        job : Job
            The job to be executed.

        Notes
        -----
        Jobs are executed in the order they are submitted, but the completion
        order may vary depending on execution time.
        """

        with self.lock:
            self.counter += 1
            thread_id = self.counter
            self.waiting[thread_id] = job

        def worker(job: Job, thread_id: int):
            try:
                if job.start_callback is not None:
                    job.start_callback(job)
                job.run()
            except Exception as e:
                job.error = e
                raise RuntimeError(f"Error in thread {thread_id}: {e}") from e
            finally:
                with self.lock:
                    self.running.pop(thread_id, None)
                    self.cond.notify_all()  # Notify others that a thread is available
                if job.done_callback is not None:
                    job.done_callback(job)

        while True:
            with self.lock:
                if len(self.running) < self.max_threads:
                    # Move job from waiting to running
                    kw_args = {"target": worker, "args": (job, thread_id)}
                    if job.name:
                        kw_args["name"] = job.name
                    thread = threading.Thread(**kw_args)
                    self.running[thread_id] = thread
                    self.waiting.pop(thread_id, None)
                    thread.start()
                    break  # Successfully assigned the job to a thread
                else:
                    self.cond.wait()  # Wait until a thread is available

    def wait_one(self) -> None:
        """
        Wait for one job to finish.

        This method blocks until at least one job completes execution.
        It's useful when you want to process completed jobs as they finish
        without waiting for all jobs to complete.
        """

        with self.lock:
            self.cond.wait()

    def join(self) -> None:
        """
        Wait for all jobs to finish.

        This method blocks until all submitted jobs have completed execution.
        It's useful to ensure all parallelized work is completed before proceeding.

        Examples
        --------
        >>> pool = Pool(max_threads=4)
        >>> # Submit jobs to the pool
        >>> for i in range(10):
        ...     job = Job(...)
        ...     pool.run(job)
        >>> # Wait for all jobs to complete
        >>> pool.join()
        >>> print("All jobs completed")
        """

        with self.cond:
            while self.waiting or self.running:
                self.cond.wait()  # Wait until all jobs are finished
