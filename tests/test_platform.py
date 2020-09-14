from subprocess import PIPE, run
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKFLOW_PATH = ROOT / 'workflow.yaml'
CUSTOM_NODES_PATH = ROOT / 'custom_nodes.py'


def call(command, args):

    args = args.split()
    result = run([command] + args, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    return result


@contextmanager
def app():
    args = "platform app create -n test -d abc -w {} -c {}".format(WORKFLOW_PATH, CUSTOM_NODES_PATH)
    result = call("deepo", args)
    _, app_id = result.stdout.strip().split(':')

    yield app_id

    args = "platform app delete --id {}".format(app_id)
    result = call("deepo", args)


@contextmanager
def app_version():
    with app() as app_id:
        args = "platform appversion create -n test_av -d abc -a {} -r 41522 41522".format(app_id)
        result = call("deepo", args)
        _, app_version_id = result.stdout.strip().split(':')

        yield app_version_id
        args = "platform appversion delete --id {}".format(app_version_id)
        result = call("deepo", args)


class TestPlatform(object):
    command = "deepo"

    def test_app(self):
        args = "platform app create -n test -d abc -w {} -c {}".format(WORKFLOW_PATH, CUSTOM_NODES_PATH)
        result = call(self.command, args)
        assert result.returncode == 0
        message, app_id = result.stdout.strip().split(':')
        assert message == 'New app created with id'

        args = "platform app update --id {} -d ciao".format(app_id)
        result = call(self.command, args)
        assert result.returncode == 0
        message = result.stdout.strip()
        assert message == 'App{} updated'.format(app_id)

        args = "platform app delete --id {}".format(app_id)
        result = call(self.command, args)
        assert result.returncode == 0
        message = result.stdout.strip()
        assert message == 'App{} deleted'.format(app_id)

    def test_appversion(self):
        with app() as app_id:
            args = "platform appversion create -n test_av -d abc -a {} -r 41522 41522".format(app_id)
            result = call(self.command, args)
            assert result.returncode == 0
            message, app_version_id = result.stdout.strip().split(':')
            assert message == 'New app version created with id'

            args = "platform appversion update --id {} -d ciao".format(app_version_id)
            result = call(self.command, args)
            assert result.returncode == 0
            message = result.stdout.strip()
            assert message == 'App version{} updated'.format(app_version_id)

            args = "platform appversion delete --id {}".format(app_version_id)
            result = call(self.command, args)
            assert result.returncode == 0
            message = result.stdout.strip()
            assert message == 'App version{} deleted'.format(app_version_id)

    def test_site(self):
        with app_version() as app_version_id:
            args = "platform site create -n test_si -d xyz -v {}".format(app_version_id)
            result = call(self.command, args)
            assert result.returncode == 0
            message, site_id = result.stdout.strip().split(':')
            assert message == 'New site created with id'

            args = "platform site update --id {} --app_version_id {}".format(site_id, app_version_id)
            result = call(self.command, args)
            assert result.returncode == 0
            message = result.stdout.strip()
            assert message == 'Site{} updated'.format(site_id)

            args = "platform site delete --id {}".format(site_id)
            result = call(self.command, args)
            assert result.returncode == 0
            message = result.stdout.strip()
            assert message == 'Site{} deleted'.format(site_id)
