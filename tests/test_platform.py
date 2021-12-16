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
    """Context manager around engage_app creation command.

    Take care of engage_app delete.
    """
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


def engage_app_version_wrapper(engage_app_id,
                               workflow,
                               custom_node=None,
                               from_major=None):
    """Wrapper around engage_app_version create command.

    Return:
        version (str), engage_app_version_id (str)
    """
    args = f"platform engage-app-version create -a {engage_app_id} -w {workflow} -r 75384 75385"
    if custom_node:
        args += f" -c {custom_node}"
    if from_major:
        args += f" --base_major_version {from_major}"

    result = call_deepo(args)
    _, rhs = result.split(':')
    engage_app_version_id = rhs.strip()

    assert len(engage_app_version_id) == APP_ID_LEN
    assert result[0:18] == 'New app version \'v'

    return result[18:21], engage_app_version_id


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
        with engage_app() as engage_app_id:
            # Output of create command: New app version 'v<major.minor>' created with id: <id>
            version1, engage_app_version_id1 = engage_app_version_wrapper(
                engage_app_id=engage_app_id,
                workflow=WORKFLOW_PATH,
                custom_node=CUSTOM_NODES_PATH
            )
            assert version1 == "1.0"

            version2, engage_app_version_id2 = engage_app_version_wrapper(
                engage_app_id=engage_app_id,
                workflow=WORKFLOW_PATH,
                custom_node=CUSTOM_NODES_PATH
            )
            assert version2 == "2.0"
            assert engage_app_version_id1 != engage_app_version_id2

            version, _ = engage_app_version_wrapper(
                engage_app_id=engage_app_id,
                workflow=WORKFLOW_PATH,
                custom_node=CUSTOM_NODES_PATH,
                from_major=version1[0]
            )
            assert version == "1.1"

            with pytest.raises(ClientError) as err:
                engage_app_version_wrapper(
                    engage_app_id=engage_app_id,
                    workflow=WORKFLOW2_PATH,
                    custom_node=CUSTOM_NODES_PATH,
                    from_major=version[0]
                )
                assert "Bad status code 400" in err
                assert f"Version already exists v{version}" in err

            version, _ = engage_app_version_wrapper(
                engage_app_id=engage_app_id,
                workflow=WORKFLOW2_PATH,
                custom_node=CUSTOM_NODES_PATH
            )
            assert version == "3.0"

    # TODO: Endpoint not yet implemented. Remove xfail when it's done.
    @pytest.mark.xfail(raises=ClientError)
    def test_engage_app_version_clone(self, no_error_logs):
        """Test engage-app-version clone command."""

        clone_cmd = "platform engage-app-version clone --version_id {} -r 75384 75385"

        with engage_app() as engage_app_id:
            _, engage_app_version_id = engage_app_version_wrapper(
                engage_app_id=engage_app_id,
                workflow=WORKFLOW_PATH,
                custom_node=CUSTOM_NODES_PATH
            )
            result = call_deepo(clone_cmd.format(engage_app_version_id))
            assert result == "Clone"

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
