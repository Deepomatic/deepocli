from ..utils import Command


class PlatformCommand(Command):
    """
        Operations on the Deepomatic Platform (studio)
    """

    from .app import AppCommand
    from .app_version import AppVersionCommand
    from .service import ServiceCommand
