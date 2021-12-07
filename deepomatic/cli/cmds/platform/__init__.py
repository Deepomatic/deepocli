from ..utils import Command


class PlatformCommand(Command):
    """
        Operations on the Deepomatic Platform (studio)
    """

    from .app import AppCommand
    from .app_version import AppVersionCommand
    from .engage_app import EngageAppCommand
    from .engage_app_version import EngageAppVersionCommand
    from .service import ServiceCommand
    from .model import ModelCommand
    from .add_images import AddImagesCommand
