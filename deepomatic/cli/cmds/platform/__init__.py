from ..utils import Command


class PlatformCommand(Command):
    """
        Operations on the Deepomatic Platform (studio)
    """

    from .drive_app import DriveAppCommand
    from .drive_app_version import DriveAppVersionCommand
    from .engage_app import EngageAppCommand
    from .engage_app_version import EngageAppVersionCommand
    from .model import ModelCommand
    from .add_images import AddImagesCommand
