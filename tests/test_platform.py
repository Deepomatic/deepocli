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
WORKFLOW2_PATH = ROOT + '/workflow.yaml'
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

    def test_engage_app_version(self, no_error_logs):
        """Test engage-app-version create command.

        Scenarii:
            * create first EngageAppVersion without previous_engage_app_version_id
            * use a modified workflow.yaml file and create a second EngageAppVersion
            with previous_engage_app_version_id from step1 command.
            * try to create new EngageAppVersion with previous_engage_app_version from
            step1: should fail
        """
        engage_app_version_cmd = "platform app-version create -a {} -w {} -c {} -r 44363 44364"
        engage_app_version_previous_cmd = engage_app_version_cmd + " -p {}"

        with engage_app() as engage_app_id:
            # Output of create command: New app version 'v<major.minor>' created with id: <id>
            result = call_deepo(
                engage_app_version_cmd.format(engage_app_id, WORKFLOW_PATH, CUSTOM_NODES_PATH)
            )
            engage_app_version_id = result[-36:]
            assert result[0:18] == 'New app version \'v'
            assert result[17:21] == "v1.0"

            result = call_deepo(
                engage_app_version_previous_cmd.format(
                    engage_app_id, WORKFLOW2_PATH, CUSTOM_NODES_PATH, engage_app_version_id
                )
            )
            assert result[0:18] == 'New app version \'v'
            assert result[17:21] == "v1.1"

            with pytest.raises(ClientError) as err:
                result = call_deepo(
                    engage_app_version_previous_cmd.format(
                        engage_app_id, WORKFLOW_PATH, CUSTOM_NODES_PATH, engage_app_version_id
                    )
                )
                assert "Bad status code 400" in err
                assert "Version already exists v1.1" in err

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
