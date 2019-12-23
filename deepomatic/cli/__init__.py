from gevent.monkey import patch_all
patch_all(thread=False, time=False)  # NOQA

from .version import __version__

__all__ = ["__version__"]
