from gevent.monkey import patch_all
patch_all(thread=False, time=False, subprocess=False)  # NOQA

from .version import __version__  # NOQA

__all__ = ["__version__"]
