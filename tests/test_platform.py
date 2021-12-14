from contextlib import contextmanager
import json
import os.path
import yaml

import pytest

from deepomatic.api.exceptions import ClientError
from deepomatic.cli.cli_parser import run

from utils import modified_environ


ROOT = os.path.dirname(os.path.abspath(__file__))
WORKFLOW_PATH = ROOT + '/workflow.yaml'
WORKFLOW2_PATH = ROOT + '/workflow2.yaml'
CUSTOM_NODES_PATH = ROOT + '/custom_nodes.py'
APP_ID_LEN = 36


def call_deepo(args, api_key=None):
    args = args.split()
    if api_key:
        with modified_environ(DEEPOMATIC_API_KEY=api_key):
            res = run(args)
    else:
        res = run(args)
    try:
        return res.strip()
    except Exception:
        return res


@contextmanager
def drive_app():
    with open(WORKFLOW_PATH, 'r') as f:
        workflow = yaml.safe_load(f)

    app_specs = [{
        "queue_name": "{}.forward".format(node['name']),
        "recognition_spec_id": node['args']['model_id']
    } for node in workflow['workflow']['steps'] if node["type"] == "Inference"]

    args = "platform app create -n test -d abc -s {}".format(json.dumps(app_specs, indent=None, separators=(',', ':')))
    result = call_deepo(args)
    msg, app_id = result.split(':')
    assert msg == "New app created with id"

    yield app_id

    args = "platform app delete --id {}".format(app_id)
    result = call_deepo(args)


@contextmanager
def app_version():
    with drive_app() as app_id:
        args = "platform app-version create -n test_av -d abc -a {} -r 44363 44364".format(app_id)
        result = call_deepo(args)
        _, app_version_id = result.split(':')

        yield app_version_id.strip(), app_id

        args = "platform app-version delete --id {}".format(app_version_id)
        result = call_deepo(args)


@contextmanager
def engage_app():
    args = "platform engage-app create -n test"
    result = call_deepo(args)

    engage_part, drive_part, _ = result.split('.')
    _, engage_app_id = engage_part.split(':')
    engage_app_id = engage_app_id.strip()
    _, drive_app_id = drive_part.split(':')
    drive_app_id = drive_app_id.strip()

    assert 'New Engage App created with id: ' in result
    assert 'Associated Drive App id: ' in result
    assert len(drive_app_id) == APP_ID_LEN
    assert len(engage_app_id) == APP_ID_LEN

    yield engage_app_id

    args = "platform engage-app delete --id {}".format(engage_app_id)
    message = call_deepo(args)
    assert message == 'Engage App {} deleted'.format(engage_app_id)


class TestPlatform(object):

    def test_drive_app(no_error_logs):
        args = "platform app create -n test -d abc"
        with pytest.raises(ValueError):
            # mandatory app specs
            result = call_deepo(args)

        with open(WORKFLOW_PATH, 'r') as f:
            workflow = yaml.safe_load(f)

        app_specs = [{
            "queue_name": "{}.forward".format(node['name']),
            "recognition_spec_id": node['args']['model_id']
        } for node in workflow['workflow']['steps'] if node["type"] == "Inference"]

        args = "platform app create -n test -d abc -s {}".format(json.dumps(app_specs, indent=None, separators=(',', ':')))
        result = call_deepo(args)
        message, app_id = result.split(':')
        app_id = app_id.strip()
        assert message == 'New app created with id'

        args = "platform app update --id {} -d ciao".format(app_id)
        message = call_deepo(args)
        assert message == 'App {} updated'.format(app_id)

        args = "platform app delete --id {}".format(app_id)
        message = call_deepo(args)
        assert message == 'App {} deleted'.format(app_id)

    def test_appversion(self, no_error_logs):
        with drive_app() as app_id:
            args = "platform app-version create -n test_av -d abc -a {} -r 44363 44364".format(app_id)
            result = call_deepo(args)
            message, app_version_id = result.split(':')
            app_version_id = app_version_id.strip()
            assert message == 'New app version created with id'

            args = "platform app-version update --id {} -d ciao".format(app_version_id)
            message = call_deepo(args)
            assert message == 'App version {} updated'.format(app_version_id)

            args = "platform app-version delete --id {}".format(app_version_id)
            message = call_deepo(args)
            assert message == 'App version {} deleted'.format(app_version_id)

    def test_engage_app_version(self, no_error_logs):
        """Test engage-app-version create command.

        workflow2: must include breaking change (testing major/minor)

        Scenarii:
            * create first EngageAppVersion without base_major_version
            * create a second EngageAppVersion without base_major_version
            * create a third EngageAppVersion
            with base_engage_app_version from step1
            * create new EngageAppVersion with base_major_version with
            workflow2: should fail (forbiden, should be a major)
            * create new major app version by giving no base_major_version
            and workflow2
        """
        engage_app_version_cmd = "platform app-version create -a {} -w {} -c {} -r 75384 75385"
        engage_app_version_major = engage_app_version_cmd + " --base_major_version {}"

        with engage_app() as engage_app_id:
            # Output of create command: New app version 'v<major.minor>' created with id: <id>
            result = call_deepo(
                engage_app_version_cmd.format(
                    engage_app_id,
                    WORKFLOW_PATH,
                    CUSTOM_NODES_PATH
                )
            )
            assert result[0:18] == 'New app version \'v'
            assert result[17:21] == "v1.0"

            result = call_deepo(
                engage_app_version_major.format(
                    engage_app_id,
                    WORKFLOW_PATH,
                    CUSTOM_NODES_PATH,
                    result[19]
                )
            )
            assert result[0:18] == 'New app version \'v'
            assert result[17:21] == "v1.1"

            with pytest.raises(ClientError) as err:
                result = call_deepo(
                    engage_app_version_major.format(
                        engage_app_id,
                        WORKFLOW_PATH2,
                        CUSTOM_NODES_PATH,
                        result[19]
                    )
                )
                assert "Bad status code 400" in err
                assert "Version already exists v1.1" in err

            result = call_deepo(
                engage_app_version_cmd.format(
                    engage_app_id,
                    WORKFLOW_PATH2,
                    CUSTOM_NODES_PATH
                )
            )
            assert result[0:18] == 'New app version \'v'
            assert result[17:21] == "v2.0"

    def test_service(self, no_error_logs):
        for service in ['customer-api', 'camera-server']:
            with drive_app() as app_id:
                args = "platform service create -a {} -n {}".format(app_id, service)
                result = call_deepo(args)
                message, service_id = result.split(':')
                service_id = service_id.strip()
                assert message == 'New service created with id'

                args = "platform service delete --id {}".format(service_id)
                message = call_deepo(args)
                assert message == 'Service {} deleted'.format(service_id)
