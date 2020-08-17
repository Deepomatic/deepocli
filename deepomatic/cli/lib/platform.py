import yaml
try:
    from builtins import FileExistsError
except ImportError:
    FileExistsError = OSError

from deepomatic.api.exceptions import BadStatus
from deepomatic.api.http_helper import HTTPHelper


class PlatformManager(object):
    def __init__(self, client_cls=HTTPHelper):
        self.client = client_cls()

    def create_site(self, name, description, app_version_id):
        data = {
            'name': name,
            'app_version_id': app_version_id
        }
        if description is not None:
            data['desc'] = description

        try:
            ret = self.client.post('/sites', data=data)
            print("New site created with id: {}".format(ret['id']))
        except BadStatus:
            print("Failed to create the site: {}".format(ret))

    def update_site(self, site_id, app_version_id):
        data = {
            'app_version_id': app_version_id
        }

        try:
            ret = self.client.patch('/sites/{}'.format(site_id), data=data)
            print("Site {} updated".format(ret['id']))
        except BadStatus:
            print("Failed to update the site: {}".format(ret))

    def create_app(self, name, description, workflow_path, custom_nodes_path):

        files = {}
        with open(workflow_path, 'r') as f:
            files['workflow_yaml'] = f
            workflow = yaml.safe_load(f)

        if custom_nodes_path is not None:
            files['custom_nodes_py'] = open(custom_nodes_path, 'r')

        # create using workflow server
        app_specs = [{
            "queue_name": "{}.forward".format(node['name']),
            "recognition_spec_id": node['args']['model_id']
        } for node in workflow['workflow']['steps'] if node["type"] == "Inference"]

        data_app = {"name": name, "app_specs": app_specs}
        if description is not None:
            data_app['desc'] = description

        try:
            ret = self.client.post('/apps-workflow', data=data_app, files=files, content_type='multipart/mixed')
            print("New app created with id: {}".format(ret['app_id']))
        except BadStatus:
            print("Failed to create the app: {}".format(ret))

    def update_app(self, app_id):
        NotImplementedError()

    def create_app_version(self, app_id, name, description, version_ids):
        data = {
            'app_id': app_id,
            'name': name,
            'recognition_version_ids': version_ids
        }
        if description is not None:
            data['desc'] = description

        try:
            ret = self.client.post('/app-versions', data=data)
            print("New app version created with id: {}".format(ret['id']))
        except BadStatus:
            print("Failed to create the app_version: {}".format(ret))

    def update_app_version(self, app_version_id):
        NotImplementedError()

    def infer(self, input):
        raise NotImplementedError()

    def inspect(self, workflow_path):
        raise NotImplementedError()

    def publish_workflow(self, workflow_path):
        with open(workflow_path, 'r') as f:
            workflow = yaml.load(f, Loader=yaml.FullLoader)

        app_specs = [{
            "queue_name": "{}.forward".format(node['name']),
            "recognition_spec_id": node['args']['spec_id']
        } for node in workflow['workflow']['nodes'] if node["type"] == "Recognition"]

        data_app = {"name": workflow['workflow']['name'], "app_specs": app_specs}
        files = {'workflow_yaml': open(workflow_path, 'r')}

        try:
            ret = self._client.post('/apps-workflow/', data=data_app, files=files, content_type='multipart/mixed')
            print("New app created with id: {}".format(ret['id']))
        except BadStatus:
            print("Failed to create app: {}".format(ret))

    def train(self):
        raise NotImplementedError()

    def upload(self):
        raise NotImplementedError()

    def validate(self):
        # TODO: implement
        return True
