from ..utils import Command
from ...lib.site import SiteManager


class ManifestCommand(Command):
    """
        Get a deployment manifest
    """

    def setup(self, subparsers):
        parser = super(ManifestCommand, self).setup(subparsers)
        parser.add_argument('-i', '--id', required=True, type=str, help="Site id")
        parser.add_argument('-t', '--target', required=True, type=str, help="deployment target")
        return parser

    def run(self, id, target, **kwargs):
        return SiteManager().get_deployment_manifest(id, target)
