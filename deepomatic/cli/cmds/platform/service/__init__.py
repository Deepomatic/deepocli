from ...utils import Command


class ServiceCommand(Command):
    """
        App version related commands
    """

    from .create import CreateCommand
    from .delete import DeleteCommand
