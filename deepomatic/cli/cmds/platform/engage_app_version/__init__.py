from ...utils import Command


class EngageAppVersionCommand(Command):
    """App version related commands."""

    from .create import CreateCommand
    from .clone import CloneCommand
    from .delete import DeleteCommand
