from .base import *  # noqa: F401, F403
from .source import sourcify  # noqa: F401
from toolz import identity as in_  # noqa: F401

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
