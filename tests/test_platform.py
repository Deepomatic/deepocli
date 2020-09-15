import os.path
import subprocess
from contextlib import contextmanager

ROOT = os.path.dirname(os.path.abspath(__file__))
WORKFLOW_PATH = ROOT + '/workflow.yaml'
CUSTOM_NODES_PATH = ROOT + '/custom_nodes.py'

# Using specific api key to run this test
api_key = os.environ['DEEPOMATIC_DEPLOY_API_KEY']
api_url = os.environ['DEEPOMATIC_DEPLOY_API_URL']
deploy_env = os.environ.copy()
deploy_env['DEEPOMATIC_API_KEY'] = api_key
deploy_env['DEEPOMATIC_API_URL'] = api_url


def call_deepo(args):
    args = args.split()
    command = ['deepo'] + args
    try:
        res = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, env=deploy_env)
        assert res.returncode == 0
        assert res.stderr == ''
        return res.stdout.strip()
    except AttributeError:
        # For python 2.7
        res = subprocess.check_output(command, universal_newlines=True, env=deploy_env)
        return res.strip


@contextmanager
def app():
    args = "platform app create -n test -d abc -w {} -c {}".format(WORKFLOW_PATH, CUSTOM_NODES_PATH)
    result = call_deepo(args)
    _, app_id = result.split(':')

    yield app_id

    args = "platform app delete --id {}".format(app_id)
    result = call_deepo(args)


@contextmanager
def app_version():
    with app() as app_id:
        args = "platform appversion create -n test_av -d abc -a {} -r 61307 61306".format(app_id)
        result = call_deepo(args)
        _, app_version_id = result.split(':')

        yield app_version_id
        args = "platform appversion delete --id {}".format(app_version_id)
        result = call_deepo(args)


class TestPlatform(object):
    command = "deepo"

    def test_app(self):
        args = "platform app create -n test -d abc -w {} -c {}".format(WORKFLOW_PATH, CUSTOM_NODES_PATH)
        result = call_deepo(args)
        message, app_id = result.split(':')
        assert message == 'New app created with id'

        args = "platform app update --id {} -d ciao".format(app_id)
        result = call_deepo(args)
        message = result.strip()
        assert message == 'App{} updated'.format(app_id)

        args = "platform app delete --id {}".format(app_id)
        result = call_deepo(args)
        message = result.strip()
        assert message == 'App{} deleted'.format(app_id)

    def test_appversion(self):
        with app() as app_id:
            args = "platform appversion create -n test_av -d abc -a {} -r 61307 61306".format(app_id)
            result = call_deepo(args)
            message, app_version_id = result.split(':')
            assert message == 'New app version created with id'

            args = "platform appversion update --id {} -d ciao".format(app_version_id)
            result = call_deepo(args)
            message = result.strip()
            assert message == 'App version{} updated'.format(app_version_id)

            args = "platform appversion delete --id {}".format(app_version_id)
            result = call_deepo(args)
            message = result.strip()
            assert message == 'App version{} deleted'.format(app_version_id)

    def test_site(self):
        with app_version() as app_version_id:
            args = "platform site create -n test_si -d xyz -v {}".format(app_version_id)
            result = call_deepo(args)
            message, site_id = result.split(':')
            assert message == 'New site created with id'

            args = "platform site update --id {} --app_version_id {}".format(site_id, app_version_id)
            result = call_deepo(args)
            message = result.strip()
            assert message == 'Site{} updated'.format(site_id)

            args = "platform site delete --id {}".format(site_id)
            result = call_deepo(args)
            message = result.strip()
            assert message == 'Site{} deleted'.format(site_id)
