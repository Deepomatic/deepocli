import os
import shutil
import tempfile

from contextlib import contextmanager
from subprocess import PIPE, run

from .workflow import CUSTOM_NODE_TEMPLATE, WORKFLOW_YAML_TEMPLATE


def call(command, args):
    return run([command, args], stdout=PIPE, stderr=PIPE, universal_newlines=True)


def build(stdout):
    return stdout


def touch(path):
    with open(path, 'a'):
        os.utime(path, None)
    return path


@contextmanager
def setup():
    tmp_dir = tempfile.mkdtemp()
    workflow_path = touch(tmp_dir + "/workflow.yaml")
    with open(workflow_path, "w+") as f:
        f.write(WORKFLOW_YAML_TEMPLATE)

    custom_nodes_path = touch(tmp_dir + "/custom_nodes.py")
    with open(custom_nodes_path, "w+") as f:
        f.write(CUSTOM_NODE_TEMPLATE)

    try:
        yield tmp_dir
    finally:
        shutil.rmtree(tmp_dir)


class TestPlatform(object):
    def test_all(self):
        with setup() as tmp_dir:

            # test_create_update_app
            command = "deepo platform app create"
            args = f"-n test -d abc -w f{tmp_dir}/workflow.yaml -c f{tmp_dir}/custom_nodes.py"
            result = call(command, args)
            assert result.returncode == 0
            json = build(result.stdout)
            id = json['id']

            command = "deepo platform app update"
            args = f" --id {id}"
            result = call(command, args)
            assert result.returncode == 0

            # test_create_update_appversion
            command = "deepo platform appversion create"
            args = " -n test_av -d abc -a d3b357fd-d6a4-411c-bdc5-a39977424c03 -r 39663 38132 38125 39628 39708 39654"
            result = call(command, args)
            assert result.returncode == 0

            id = "d3b357fd-d6a4-411c-bdc5-a39977424c03"

            command = "deepo platform appversion update"
            args = f" --id {id}"
            result = call(command, args)
            assert result.returncode == 0

            # test_site_update_appversion

            app_version_id = "d3b357fd-d6a4-411c-bdc5-a39977424c03"
            command = "deepo platform site create"
            args = f" -n test_av -d abc -v {app_version_id}"
            result = call(command, args)
            assert result.returncode == 0

            id = "d3b357fd-d6a4-411c-bdc5-a39977424c03"

            command = "deepo platform site update"
            args = f" --id {id} --app_version_id {app_version_id}"
            result = call(command, args)
            assert result.returncode == 0
