from subprocess import PIPE, run
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKFLOW_PATH = ROOT / 'workflow.yaml'
CUSTOM_NODES_PATH = ROOT / 'custom_nodes.py'


def call(command, args):

    args = args.split()
    return run([command] + args, stdout=PIPE, stderr=PIPE, universal_newlines=True)


@contextmanager
def app():
    args = f"platform app create -n test -d abc -w {WORKFLOW_PATH} -c {CUSTOM_NODES_PATH}"
    result = call("deepo", args)
    _, app_id = result.stdout.strip().split(':')

    yield app_id

    args = f"platform app delete --id {app_id}"
    result = call("deepo", args)


@contextmanager
def app_version():
    with app() as app_id:
        args = f"platform appversion create -n test_av -d abc -a {app_id} -r 41522 41522"
        result = call("deepo", args)
        _, app_version_id = result.stdout.strip().split(':')

        yield app_version_id
        args = f"platform appversion delete --id {app_version_id}"
        result = call("deepo", args)


class TestPlatform(object):
    command = "deepo"

    def test_app(self):
        args = f"platform app create -n test -d abc -w {WORKFLOW_PATH} -c {CUSTOM_NODES_PATH}"
        result = call(self.command, args)
        assert result.returncode == 0
        message, app_id = result.stdout.strip().split(':')
        assert message == 'New app created with id'

        args = f"platform app update --id {app_id} -d ciao"
        result = call(self.command, args)
        assert result.returncode == 0
        message = result.stdout.strip()
        assert message == f'App{app_id} updated'

        args = f"platform app delete --id {app_id}"
        result = call(self.command, args)
        assert result.returncode == 0
        message = result.stdout.strip()
        assert message == f'App{app_id} deleted'

    def test_appversion(self):
        with app() as app_id:
            args = f"platform appversion create -n test_av -d abc -a {app_id} -r 41522 41522"
            result = call(self.command, args)
            assert result.returncode == 0
            message, app_version_id = result.stdout.strip().split(':')
            assert message == 'New app version created with id'

            args = f"platform appversion update --id {app_version_id} -d ciao"
            result = call(self.command, args)
            assert result.returncode == 0
            message = result.stdout.strip()
            assert message == f'App version{app_version_id} updated'

            args = f"platform appversion delete --id {app_version_id}"
            result = call(self.command, args)
            assert result.returncode == 0
            message = result.stdout.strip()
            assert message == f'App version{app_version_id} deleted'

    def test_site(self):
        with app_version() as app_version_id:
            args = f"platform site create -n test_si -d xyz -v {app_version_id}"
            result = call(self.command, args)
            assert result.returncode == 0
            message, site_id = result.stdout.strip().split(':')
            assert message == 'New site created with id'

            args = f"platform site update --id {site_id} --app_version_id {app_version_id}"
            result = call(self.command, args)
            assert result.returncode == 0
            message = result.stdout.strip()
            assert message == f'Site{site_id} updated'

            args = f"platform site delete --id {site_id}"
            result = call(self.command, args)
            assert result.returncode == 0
            message = result.stdout.strip()
            assert message == f'Site{site_id} deleted'
