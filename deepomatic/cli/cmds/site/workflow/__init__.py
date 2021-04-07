from ...utils import Command


class WorkflowCommand(Command):
    """
        Site Workflow related commands.
    """

    from .noop import NoopCommand
    from .draw import DrawCommand
    from .blur import BlurCommand
    from .infer import InferCommand
