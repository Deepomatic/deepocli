from ...utils import Command


class AppCommand(Command):
    """
        App related commands
    """

    from .create import CreateCommand
    from .delete import DeleteCommand
    from .update import UpdateCommand
    from .inspect import InspectCommand
    from .publish import PublishCommand
    from .validate import ValidateCommand
    from .infer import InferCommand
