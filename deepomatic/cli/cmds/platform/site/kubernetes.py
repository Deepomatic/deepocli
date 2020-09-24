from ...utils import Command
from ..utils import PlatformManager


class KubernetesCommand(Command):
    """
        Get a kubernetes deploy manifest
    """

    def setup(self, subparsers):
        parser = super(KubernetesCommand, self).setup(subparsers)
        parser.add_argument('-i', '--id', required=True, type=str, help="Site id")
        parser.add_argument('-t', '--target', required=True, type=str, help="Kubernetes target")
        return parser

    def run(self, id, target, **kwargs):
        return PlatformManager().get_site_deploy_manifest(id, 'kubernetes', target)
