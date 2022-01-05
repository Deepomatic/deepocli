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
RECOG_MODELS = "44363 44364"
# Keep this to ease test on staging:
# RECOG_MODELS = "75384 75385"
# /!\ use correct model id in workflow: `model_id: 91711`


def call_deepo(args, api_key=None, json_output=True):
    args = args.split()
    if json_output:
        args.append("--json-output")
    if api_key:
        with modified_environ(DEEPOMATIC_API_KEY=api_key):
            res = run(args)
    else:
        res = run(args)

    if json_output:
        return res.to_json()

    return res.to_str()


@contextmanager
def drive_app():
    args = "platform drive-app create -n test -d abc -s worker-nn -s workflow-server"
    result = call_deepo(args)

    drive_app_id = result.get("drive_app_id")

    try:
        yield drive_app_id
    finally:
        args = f"platform drive-app delete -i {drive_app_id}"
        result = call_deepo(args)
        assert result.get("drive_app_id")


@contextmanager
def drive_app_version(drive_app_id):
    with open(WORKFLOW_PATH, 'r') as f:
        workflow = yaml.safe_load(f)

    app_specs = [{
        "queue_name": "{}.forward".format(node['name']),
        "recognition_spec_id": node['args']['model_id']
    } for node in workflow['workflow']['steps'] if node["type"] == "Inference"]

    args = "platform drive-app-version create -n test_av -d abc -i {} -r {} -s {}".format(
        drive_app_id,
        RECOG_MODELS,
        json.dumps(app_specs, indent=None, separators=(',', ':'))
    )
    result = call_deepo(args)

    drive_app_version_id = result.get("drive_app_version_id")

    try:
        yield drive_app_version_id
    finally:
        args = f"platform drive-app-version delete -v {drive_app_version_id}"
        result = call_deepo(args)
        assert result.get("drive_app_version_id")


@contextmanager
def engage_app(application_type=None):
    """Context manager around engage_app creation command.

    Take care of engage_app delete.
    """
    args = "platform engage-app create -n test"
    if application_type:
        args += f" --application_type {application_type}"

    result = call_deepo(args)
    assert result.get("drive_app_id")
    engage_app_id = result.get("engage_app_id")

    try:
        yield engage_app_id
    finally:
        args = f"platform engage-app delete -i {engage_app_id}"
        result = call_deepo(args)
        assert result.get("engage_app_id")


def engage_app_version_wrapper(engage_app_id,
                               workflow,
                               custom_node=None,
                               from_major=None):
    """Wrapper around engage_app_version create command.

    Return:
        version (str), engage_app_version_id (str)
    """
    args = f"platform engage-app-version create -i {engage_app_id} -w {workflow} -r {RECOG_MODELS}"
    if custom_node:
        args += f" -c {custom_node}"
    if from_major:
        args += f" --base_major_version {from_major}"

    result = call_deepo(args)

    engage_app_version_id = result.get("engage_app_version_id")
    major = result.get("major")
    minor = result.get("minor")
    assert result.get("drive_app_version_id")

    return "{}.{}".format(major, minor), engage_app_version_id


class TestPlatform(object):

    def test_drive_app(no_error_logs):
        with drive_app() as drive_app_id:
            args = "platform drive-app update -i {} -d ciao".format(drive_app_id)
            result = call_deepo(args)
            assert result.get("drive_app_id")

    def test_drive_app_version(self, no_error_logs):
        with drive_app() as drive_app_id:
            with drive_app_version(drive_app_id) as drive_app_version_id:
                args = f"platform drive-app-version update -v {drive_app_version_id} -d ciao"
                result = call_deepo(args)
                assert result.get("drive_app_version_id")

    def test_engage_app(self, no_error_logs):
        """Test engage-app create command."""
        application_types = ["WORKFLOW", "INFERENCE", "VIDEO", "FIELD_SERVICES", None]
        unvalid_application_type = "NOT_A_VALID_TYPE"

        for application_type in application_types:
            with engage_app(application_type):
                # No assert here, everything is tested in `engage_app`
                pass

        with pytest.raises(ClientError):
            with engage_app(unvalid_application_type):
                # No assert here
                pass

    def test_engage_app_version(self, no_error_logs):
        """Test engage-app-version create command.

        workflow2: must include breaking change (testing major/minor)

        Scenario:
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
            version_number1, engage_app_version_id1 = engage_app_version_wrapper(
                engage_app_id=engage_app_id,
                workflow=WORKFLOW_PATH,
                custom_node=CUSTOM_NODES_PATH
            )
            assert version_number1 == "1.0"

            version_number2, engage_app_version_id2 = engage_app_version_wrapper(
                engage_app_id=engage_app_id,
                workflow=WORKFLOW_PATH,
                custom_node=CUSTOM_NODES_PATH
            )
            assert version_number2 == "2.0"
            assert engage_app_version_id1 != engage_app_version_id2

            version_number, _ = engage_app_version_wrapper(
                engage_app_id=engage_app_id,
                workflow=WORKFLOW_PATH,
                custom_node=CUSTOM_NODES_PATH,
                from_major=version_number1[0]
            )
            assert version_number == "1.1"

            with pytest.raises(ClientError):
                engage_app_version_wrapper(
                    engage_app_id=engage_app_id,
                    workflow=WORKFLOW2_PATH,
                    custom_node=CUSTOM_NODES_PATH,
                    from_major=version_number[0]
                )

            version_number, _ = engage_app_version_wrapper(
                engage_app_id=engage_app_id,
                workflow=WORKFLOW2_PATH,
                custom_node=CUSTOM_NODES_PATH
            )
            assert version_number == "3.0"

    def test_engage_app_version_from(self, no_error_logs):
        """Test engage-app-version create-from command.

        Test various arguments being present or not.
        Should work from no args to all args beging present.

        Scenario:
            * Create an EngageApp version with --from
            * Create an EngageApp version with --workflow and --from
            * Create an EngageApp version with --workflow, --from, -r, -c
        """
        create_from_cmd = "platform engage-app-version create-from --from {}"

        with engage_app() as engage_app_id:
            _, engage_app_version_id = engage_app_version_wrapper(
                engage_app_id=engage_app_id,
                workflow=WORKFLOW_PATH,
                custom_node=CUSTOM_NODES_PATH
            )
            result = call_deepo(create_from_cmd.format(engage_app_version_id))
            assert result.get("engage_app_version_id")
            assert result.get("major")
            assert result.get("minor")
            assert result.get("origin")

            create_from_cmd += f" -w {WORKFLOW_PATH}"
            result = call_deepo(create_from_cmd.format(engage_app_version_id))
            assert result.get("engage_app_version_id")
            assert result.get("major")
            assert result.get("minor")
            assert result.get("origin")

            create_from_cmd += f" -c {CUSTOM_NODES_PATH} -r {RECOG_MODELS}"
            result = call_deepo(create_from_cmd.format(engage_app_version_id))
            assert result.get("engage_app_version_id")
            assert result.get("major")
            assert result.get("minor")
            assert result.get("origin")
