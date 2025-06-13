"""
Utility functions for nextpipe.

This module provides utility functions used throughout the nextpipe framework
for logging, function wrapping, and AST parsing.

Functions
--------
log
    Log a message with step context.
log_internal
    Log an internal nextpipe message.
wrap_func
    Wrap a function to unpack arguments.
convert_to_string_values
    Convert all dictionary values to strings.
get_ast_root
    Find the AST root of a given object.
"""

import ast
import importlib
import inspect
import sys
import threading
from functools import wraps
from typing import Any

THREAD_NAME_PREFIX = "nextpipe-"
"""str: Prefix for thread names created by nextpipe."""


def __get_step_name() -> str:
    """
    Gets the name of the step currently executing in the calling thread.

    Returns
    -------
    str
        The name of the current step if called from a nextpipe thread,
        or 'main' if called from the main thread.
    """

    if threading.current_thread().name.startswith(THREAD_NAME_PREFIX):
        return threading.current_thread().name[len(THREAD_NAME_PREFIX) :]
    return "main"


def log(message: str) -> None:
    """
    Logs a message using stderr. Furthermore, prepends the name of the calling function if it is a step.

    You can import the `log` function directly from `nextpipe`:

    ```python
    from nextpipe import log
    ```

    This function is useful for debugging and providing execution information during pipeline runs.

    Parameters
    ----------
    message : str
        The message to log.

    Examples
    --------
    >>> from nextpipe import log
    >>> log("Processing data")
    Processing data
    >>> # In a step function, it would show:
    >>> # [step_name] Processing data
    """

    step_name = __get_step_name()
    if step_name:
        print(f"[{step_name}] {message}", file=sys.stderr)
    else:
        print(message, file=sys.stderr)


def log_internal(message: str) -> None:
    """
    Logs a message using stderr.

    This function is used internally by the nextpipe framework to log messages
    with a consistent prefix.

    Parameters
    ----------
    message : str
        The message to log.

    Examples
    --------
    >>> from nextpipe.utils import log_internal
    >>> log_internal("Pipeline initialized")
    [nextpipe] Pipeline initialized
    """

    print(f"[nextpipe] {message}", file=sys.stderr)


def wrap_func(function):
    """
    Wraps the given function in a new function that unpacks the arguments given as a tuple.

    This utility is used internally by nextpipe to pass arguments to functions
    that are executed in threads.

    Parameters
    ----------
    function : callable
        The function to wrap.

    Returns
    -------
    callable
        A new function that unpacks its arguments and calls the original function.

    Examples
    --------
    >>> from nextpipe.utils import wrap_func
    >>> def add(a, b):
    ...     return a + b
    >>> wrapped = wrap_func(add)
    >>> wrapped(([1, 2], {}))
    3
    """

    @wraps(function)
    def func_wrapper(args):
        return function(*args[0], **args[1])

    return func_wrapper


def convert_to_string_values(input_dict: dict[str, Any]) -> dict[str, str]:
    """
    Converts all values of the given dictionary to strings.

    This utility is useful when working with configuration objects where
    string representation of values is required.

    Parameters
    ----------
    input_dict : dict[str, Any]
        The dictionary with values to convert.

    Returns
    -------
    dict[str, str]
        A new dictionary with the same keys but all values converted to strings.

    Examples
    --------
    >>> from nextpipe.utils import convert_to_string_values
    >>> d = {'a': 1, 'b': 2.0, 'c': True}
    >>> convert_to_string_values(d)
    {'a': '1', 'b': '2.0', 'c': 'True'}
    """

    return {key: str(value) for key, value in input_dict.items()}


def __is_running_in_notebook():
    """
    Check if the code is running in a Jupyter notebook.

    This function attempts to detect if the code is running in a Jupyter notebook
    by checking for the presence of IPython with a notebook configuration.

    Returns
    -------
    bool
        True if running in a Jupyter notebook, False otherwise.
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

    This function searches through the notebook execution history to find
    the cell where the object's class was defined, and returns its AST node.

    Parameters
    ----------
    obj : object
        The object whose class definition AST node to find.

    Returns
    -------
    ast.ClassDef
        The AST node representing the class definition.

    Raises
    ------
    ValueError
        If the class definition cannot be found in the notebook history.
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

    This function locates and returns the AST node representing the class definition
    of the provided object by inspecting the source code of its module.

    Parameters
    ----------
    obj : object
        The object whose class definition AST node to find.

    Returns
    -------
    ast.ClassDef
        The AST node representing the class definition.

    Raises
    ------
    IndexError
        If the class definition could not be found in the module.
    """

    module = importlib.import_module(obj.__class__.__module__)
    class_name = obj.__class__.__name__
    tree = ast.parse(inspect.getsource(module)).body
    root = [n for n in tree if isinstance(n, ast.ClassDef) and n.name == class_name][0]
    return root


def get_ast_root(obj: object) -> ast.ClassDef:
    """
    Find the root AST of the given object.

    This function determines whether the code is running in a Jupyter notebook
    or a normal Python module, and calls the appropriate helper function to
    find the AST node representing the class definition of the provided object.

    Parameters
    ----------
    obj : object
        The object whose class definition AST node to find.

    Returns
    -------
    ast.ClassDef
        The AST node representing the class definition.

    Raises
    ------
    ValueError
        If running in a notebook and the class definition cannot be found.
    IndexError
        If not running in a notebook and the class definition cannot be found.

    Examples
    --------
    >>> from nextpipe.utils import get_ast_root
    >>> class Example:
    ...     pass
    >>> obj = Example()
    >>> root = get_ast_root(obj)
    >>> isinstance(root, ast.ClassDef)
    True
    >>> root.name
    'Example'
    """

    if __is_running_in_notebook():
        return __get_notebook_ast_root(obj)
    else:
        return __get_normal_ast_root(obj)
