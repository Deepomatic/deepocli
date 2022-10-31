from ...utils import Command


class EngageAppVersionCommand(Command):
    """EngageAppVersion related commands."""

    from .create import CreateCommand
    from .create_from import CreateFromCommand
    from .delete import DeleteCommand
