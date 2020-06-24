import yaml
from importlib import util  # Python 3.5+
try:
    from builtins import FileExistsError
except ImportError:
    FileExistsError = OSError

from deepomatic.api.http_helper import HTTPHelper


class PlatformManager(object):
    def __init__(self, client_cls=HTTPHelper):
        self.client = client_cls()

    def create_site(self, name, app_version_id):
        data = {
            'name': name,
            'app_version_id': app_version_id
        }

        ret = self.client.post('/sites', data=data)
        if 'id' not in ret:
            print("Failed to create the site: {}".format(ret))
        else:
            id = ret['site_id']
            print("New site created with id: {}".format(id))

    def update_site(self, site_id, app_version_id):
        data = {
            'app_version_id': app_version_id
        }
        ret = self.client.patch('/sites/{}'.format(site_id), data=data)
        if 'id' not in ret:
            print("Failed to update the site: {}".format(ret))
        else:
            id = ret['id']
            print("Site {} updated".format(id))

    def create_app(self, name, workflow_path, custom_nodes_path):
        # Validate the workflow
        with open(workflow_path, 'r') as f:
            workflow = yaml.safe_load(f)

        # Validate the custom_node
        if custom_nodes_path is not None:
            spec = util.spec_from_file_location("custom_nodes", custom_nodes_path)
            util.module_from_spec(spec)

        # create using workflow server
        app_specs = [{
            "queue_name": "{}.forward".format(node['name']),
            "recognition_spec_id": node['args']['model_id']
        } for node in workflow['workflow']['steps'] if node["type"] == "Inference"]

        data_app = {"name": name, "app_specs": app_specs}
        files = {'workflow_yaml': open(workflow_path, 'r')}
        if custom_nodes_path is not None:
            files['custom_nodes_py'] = open(custom_nodes_path, 'r')

        ret = self.client.post('/apps-workflow', data=data_app, files=files, content_type='multipart/mixed')
        if 'app_id' not in ret:
            print("Failed to create app: {}".format(ret))
        else:
            app_id = ret['app_id']
            print("New app created with id: {}".format(app_id))

    def update_app(self, app_id):
        print(app_id)

    def create_app_versions(self, app_id, name, version_ids):
        data = {
            'app_id': app_id,
            'name': name,
            'recognition_version_ids': version_ids
        }
        ret = self.client.post('/app-versions', data=data)
        if 'id' not in ret:
            print("Failed to create app_version: {}".format(ret))
        else:
            id = ret['id']
            print("New app version created with id: {}".format(id))

    def update_app_versions(self, app_version_id):
        print(app_version_id)

    def infer(self, input):
        raise NotImplementedError()

    def inspect(self, workflow_path):
        raise NotImplementedError()

    def publish_workflow(self, workflow_path):
        with open(workflow_path, 'r') as f:
            workflow = yaml.load(f, Loader=yaml.FullLoader)

        # create using workflow server
        app_specs = [{
            "queue_name": "{}.forward".format(node['name']),
            "recognition_spec_id": node['args']['spec_id']
        } for node in workflow['workflow']['nodes'] if node["type"] == "Recognition"]

        data_app = {"name": workflow['workflow']['name'], "app_specs": app_specs}
        files = {'workflow_yaml': open(workflow_path, 'r')}

        # TODO: upload custom_nodes

        ret = self._client.post('/apps-workflow/', data=data_app, files=files, content_type='multipart/mixed')
        if 'app_id' not in ret:
            print("Failed to create app: {}".format(ret))
        else:
            app_id = ret['app_id']
            print("New app created with id: {}".format(app_id))
            ret = self._client.get('/accounts/me/')
            email = ret['account']['email']
            organization = email.split('@')[0].split('-')[0]
            host = self._client.host
            print("Go to {}/{}/deployments to choose your recognition versions!".format(host, organization))

        # TODO: remove prints

    def train(self):
        raise NotImplementedError()

    def upload(self):
        raise NotImplementedError()

    def validate(self):
        # TODO: implement
        return True


# TODO: clone repo ?
CUSTOM_NODE_TEMPLATE = """
from deepomatic.workflows.nodes import CustomNode


class MyNode(CustomNode):
    def __init__(self, config, node_name, input_nodes, concepts):
        super(MyNode, self).__init__(config, node_name, input_nodes)

    def process(self, context, regions):
        return regions

"""
WORKFLOW_YAML_TEMPLATE = {
    "version": 1,
    "workflow": {
        "name": "workflow",
        "nodes": [
            {
                "name": "image_input",
                "type": "Input",
                "args": {
                    "type": "Image"
                }
            },
            {
                "name": "detector",
                "type": "Recognition",
                "input_nodes": [
                    "input"
                ],
                "args": {
                    "spec_id": 0,
                    "concepts": [
                        "item"
                    ]
                }
            }
        ]
    }
}
