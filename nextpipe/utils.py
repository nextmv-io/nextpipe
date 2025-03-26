import random
import sys
import threading
import time
from functools import wraps

from nextmv.cloud import Application, RunResult, StatusV2

THREAD_NAME_PREFIX = "nextpipe-"


def __get_step_name() -> str:
    """
    Gets the name of the step currently executing in the calling thread.
    """
    if threading.current_thread().name.startswith(THREAD_NAME_PREFIX):
        return threading.current_thread().name[len(THREAD_NAME_PREFIX) :]
    return "main"


def log(message: str) -> None:
    """
    Logs a message using stderr. Furthermore, prepends the name of the calling function if it is a step.
    """
    step_name = __get_step_name()
    if step_name:
        print(f"[{step_name}] {message}", file=sys.stderr)
    else:
        print(message, file=sys.stderr)


def log_internal(message: str) -> None:
    """
    Logs a message using stderr.
    """
    print(f"[nextpipe] {message}", file=sys.stderr)


def wrap_func(function):
    """
    Wraps the given function in a new function that unpacks the arguments given as a tuple.
    """

    @wraps(function)
    def func_wrapper(args):
        return function(*args[0], **args[1])

    return func_wrapper


def convert_to_string_values(input_dict: dict[str, any]) -> dict[str, str]:
    """
    Converts all values of the given dictionary to strings.
    """
    return {key: str(value) for key, value in input_dict.items()}


_INFINITE_TIMEOUT = sys.maxsize


def wait_for_runs(
    app: Application,
    run_ids: list[str],
    timeout: float = _INFINITE_TIMEOUT,
    max_backoff: float = 30,
) -> list[RunResult]:
    """
    Wait until all runs with the given IDs are finished.
    """
    # Wait until all runs are finished or the timeout is reached
    jitter = random.random() * 2.0
    missing = set(run_ids)
    backoff = 2.0 + jitter  # With base and jitter we aim for a backoff start between 2 and 4 seconds
    start_time = time.time()
    while missing and time.time() - start_time < timeout:
        time.sleep(backoff)
        backoff = min(backoff * 2, max_backoff)

        for run_id in missing.copy():
            run_info = app.run_metadata(run_id=run_id)
            if run_info.metadata.status_v2 == StatusV2.succeeded:
                missing.remove(run_id)
                continue
            if run_info.metadata.status_v2 in [
                StatusV2.failed,
                StatusV2.canceled,
            ]:
                raise RuntimeError(f"Run {run_id} {run_info.metadata.status_v2}: {run_info.metadata.error}")

    if missing:
        raise TimeoutError(f"Timeout of {timeout} seconds reached while waiting.")

    return [app.run_result(run_id=run_id) for run_id in run_ids]
