import yaml
import logging

try:
    from builtins import FileExistsError
except ImportError:
    FileExistsError = OSError

from deepomatic.api.http_helper import HTTPHelper


LOGGER = logging.getLogger(__name__)


class PlatformManager(object):
    def __init__(self, client_cls=HTTPHelper):
        self.client = client_cls()

    def create_app(self, name, description, workflow_path, custom_nodes_path, app_specs):

        if custom_nodes_path and not workflow_path:
            raise ValueError('Custom nodes require a workflow yaml.')

        if workflow_path:
            if app_specs is not None:
                raise ValueError('Specs are deduced from workflow yaml, no need to specify them.')
            ret = self.create_workflow_app(name, description, workflow_path, custom_nodes_path)
            app_id = ret['app_id']
        else:
            if app_specs is None:
                raise ValueError('Specs are mandatory for non workflow apps.')
            # creating an app from scratch
            # require to add the services manually
            data_app = {'name': name, 'desc': description, 'app_specs': app_specs}
            ret = self.client.post('/apps', data=data_app)
            app_id = ret['id']
        return "New app created with id: {}".format(app_id)

    def create_workflow_app(self, name, description, workflow_path, custom_nodes_path):
        with open(workflow_path, 'r') as f:
            workflow = yaml.safe_load(f)

        # create using workflow server
        app_specs = [{
            "queue_name": "{}.forward".format(node['name']),
            "recognition_spec_id": node['args']['model_id']
        } for node in workflow['workflow']['steps'] if node["type"] == "Inference"]

        data_app = {"name": name, "app_specs": app_specs}
        if description is not None:
            data_app['desc'] = description

        with open(workflow_path, 'r') as w:
            files = {'workflow_yaml': w}
            if custom_nodes_path is not None:
                with open(custom_nodes_path, 'r') as c:
                    files['custom_nodes_py'] = c
                    ret = self.client.post('/apps-workflow', data=data_app, files=files, content_type='multipart/mixed')
            else:
                ret = self.client.post('/apps-workflow', data=data_app, files=files, content_type='multipart/mixed')
            return ret

    def update_app(self, app_id, name, description):
        data = {}

        if name is not None:
            data['name'] = name

        if description is not None:
            data['desc'] = description

        ret = self.client.patch('/apps/{}'.format(app_id), data=data)
        return "App {} updated".format(ret['id'])

    def delete_app(self, app_id):
        self.client.delete('/apps/{}'.format(app_id))
        return "App {} deleted".format(app_id)

    def create_app_version(self, app_id, name, description, version_ids):
        data = {
            'app_id': app_id,
            'name': name,
            'recognition_version_ids': version_ids
        }
        if description is not None:
            data['desc'] = description

        ret = self.client.post('/app-versions', data=data)
        return "New app version created with id: {}".format(ret['id'])

    def update_app_version(self, app_version_id, name, description):
        data = {}

        if name is not None:
            data['name'] = name

        if description is not None:
            data['desc'] = description

        ret = self.client.patch('/app-versions/{}'.format(app_version_id), data=data)
        return "App version {} updated".format(ret['id'])

    def delete_app_version(self, app_version_id):
        self.client.delete('/app-versions/{}'.format(app_version_id))
        return "App version {} deleted".format(app_version_id)

    def create_service(self, **data):
        ret = self.client.post('/services', data=data)
        return "New service created with id: {}".format(ret['id'])

    def delete_service(self, service_id):
        self.client.delete('/services/{}'.format(service_id))
        return "Service {} deleted".format(service_id)
