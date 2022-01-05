from ...utils import PlatformCommand


class EngageAppVersionCommand(PlatformCommand):
    """EngageAppVersion related commands."""

    from .create import CreateCommand
    from .create_from import CreateFromCommand
    from .delete import DeleteCommand
