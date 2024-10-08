"""Framework for Decision Pipeline modeling and execution."""

from .__about__ import __version__
from .decorators import app as app
from .decorators import needs as needs
from .decorators import optional as optional
from .decorators import repeat as repeat
from .decorators import step as step
from .flow import FlowGraph as FlowGraph
from .flow import FlowSpec as FlowSpec

VERSION = __version__
"""The version of the nextpipe package."""
