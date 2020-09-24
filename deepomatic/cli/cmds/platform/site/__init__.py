from ...utils import Command


class SiteCommand(Command):
    """
        Site related commands
    """

    from .create import CreateCommand
    from .update import UpdateCommand
    from .delete import DeleteCommand
    from .kubernetes import KubernetesCommand
    from .docker_compose import DockerComposeCommand
