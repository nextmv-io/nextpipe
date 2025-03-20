import threading
import time
import unittest

from nextpipe.threads import Job, Pool


class TestLogger(unittest.TestCase):
    def test_pool(self):
        test_lock = threading.Lock()
        numbers = {1, 2, 3, 4, 5, 6}
        numbers_seen = set()

        def target(i):
            time.sleep(0.1)  # Simulate work
            with test_lock:
                numbers_seen.add(i)

        pool = Pool(2)
        for i in numbers:  # Submit 6 jobs
            pool.run(Job(target, None, (i,)))
        pool.join()

        self.assertEqual(numbers_seen, numbers)

    test_lock = threading.Lock()

    def test_fail(self):
        def target(_):
            time.sleep(0.1)  # Simulate work
            raise ValueError("Something went wrong")

        intercepted_exception = None

        def callback(job: Job):
            nonlocal intercepted_exception
            if job.error:
                intercepted_exception = job.error

        pool = Pool(2)
        for i in range(1, 2):  # Submit 1
            pool.run(Job(target, callback, (i,)))
        pool.join()

        self.assertIsNotNone(intercepted_exception)
        self.assertIsInstance(intercepted_exception, str)
        self.assertTrue(intercepted_exception.startswith("Error in thread"))
        self.assertIn("ValueError: Something went wrong", intercepted_exception)


if __name__ == "__main__":
    unittest.main()
