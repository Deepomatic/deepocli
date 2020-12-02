from ...utils import Command


class ModelCommand(Command):
    """
        Model related commands.
    """

    from .noop import NoopCommand
    from .draw import DrawCommand
    from .blur import BlurCommand
    from .infer import InferCommand
