from ..utils import JsonOutputCommand
from ...lib.site import SiteManager


class DeleteCommand(JsonOutputCommand):
    """Delete a Site."""

    def setup(self, subparsers):
        parser = super(DeleteCommand, self).setup(subparsers)
        parser.add_argument('-i', '--site_id', required=True, type=str, help="Site id")
        return parser

    def run(self, site_id, **kwargs):
        return SiteManager().delete(site_id)
