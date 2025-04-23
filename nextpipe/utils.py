import ast
import importlib
import inspect
import sys
import threading
from functools import wraps

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
    for i in range(len(ipython.history_manager.input_hist_parsed) - 1, -1, -1):
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
    module = importlib.import_module(obj.__class__.__module__)
    class_name = obj.__class__.__name__
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
