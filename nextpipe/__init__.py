"""Framework for Decision Pipeline modeling and execution."""

from .__about__ import __version__
from .config import Configuration as Configuration
from .decorators import app as app
from .decorators import foreach as foreach
from .decorators import join as join
from .decorators import needs as needs
from .decorators import optional as optional
from .decorators import repeat as repeat
from .decorators import step as step
from .flow import FlowGraph as FlowGraph
from .flow import FlowSpec as FlowSpec
from .schema import AppOption as AppOption
from .schema import AppRunConfig as AppRunConfig
from .utils import log as log

VERSION = __version__
"""The version of the nextpipe package."""
