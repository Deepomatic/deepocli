from .utils import _SiteCommand, SiteManager


class SaveCommand(_SiteCommand):
    """
        save a site to an archive
    """

    def setup(self, subparsers):
        parser = super(SaveCommand, self).setup(subparsers)
        parser.add_argument('archive_dst', type=str, help="path to archive", default=None)
        return parser

    def run(self, site_id, archive_dst, **kwargs):
        SiteManager().save(site_id, archive_dst)
        # TODO: feedback