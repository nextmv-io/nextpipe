import ast
import importlib
import inspect
import random
import sys
import threading
import time
from functools import wraps
from typing import Callable

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
    stop_waiting: Callable[[], bool] = lambda: False,
) -> list[RunResult]:
    """
    Wait until all runs with the given IDs are finished.
    """
    # Wait until all runs are finished or the timeout is reached
    jitter = random.random() * 2.0
    missing = set(run_ids)
    backoff = 2.0 + jitter  # With base and jitter we aim for a backoff start between 2 and 4 seconds
    next_check = time.time() + backoff  # First check with some delay as external runs are not that fast
    internal_poll_interval = 0.5
    start_time = time.time()
    while missing and time.time() - start_time < timeout:
        # Check if the user wants to stop waiting
        if stop_waiting():
            raise RuntimeError("The job was canceled.")

        # Check whether it is time to check the status of the runs. This allows quicker
        # early termination if cancelled.
        time.sleep(internal_poll_interval)
        now = time.time()
        if now < next_check:
            continue
        backoff = min(backoff * 2, max_backoff)
        next_check = now + backoff

        # Check if all runs are finished
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


def __is_running_in_notebook():
    """
    Check if the code is running in a Jupyter notebook.
    """
    try:
        from IPython import get_ipython

        # Check if the IPython instance is a notebook
        if "IPKernelApp" in get_ipython().config:
            return True
        else:
            return False
    except ImportError:
        return False
    except AttributeError:
        return False


def __get_notebook_ast_root(obj: object) -> ast.ClassDef:
    """
    Find the root AST of the given object in a Jupyter notebook.
    """
    from IPython import get_ipython

    # Get the current IPython instance
    ipython = get_ipython()

    # Go backwards in the history to find the cell where the object's class was defined.
    for i in range(len(ipython.history_manager.input_hist_parsed), 0, -1):
        # Parse the code of the cell into an AST.
        tree = ast.parse(ipython.history_manager.input_hist_parsed[i])

        # Find the class definition for the given object.
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == obj.__class__.__name__:
                return node

    raise ValueError(f"Could not find AST root for {obj.__class__.__name__} in notebook.")


def __get_normal_ast_root(obj: object) -> ast.ClassDef:
    """
    Find the root AST of the given object.
    """
    module = importlib.import_module(obj.__module__)
    class_name = obj.__name__
    tree = ast.parse(inspect.getsource(module)).body
    root = [n for n in tree if isinstance(n, ast.ClassDef) and n.name == class_name][0]
    return root


def get_ast_root(obj: object) -> ast.ClassDef:
    """
    Find the root AST of the given object.
    """
    if __is_running_in_notebook():
        return __get_notebook_ast_root(obj)
    else:
        return __get_normal_ast_root(obj)
