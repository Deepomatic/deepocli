from ...utils import Command
from ..utils import PlatformManager


class DockerComposeCommand(Command):
    """
        Get a docker-compose deploy manifest
    """

    def setup(self, subparsers):
        parser = super(DockerComposeCommand, self).setup(subparsers)
        parser.add_argument('-i', '--id', required=True, type=str, help="Site id")
        return parser

    def run(self, id, **kwargs):
        return PlatformManager().get_site_deploy_manifest(id, 'docker-compose', '')
