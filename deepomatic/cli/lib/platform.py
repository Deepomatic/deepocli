import yaml
import logging

try:
    from builtins import FileExistsError
except ImportError:
    FileExistsError = OSError

from deepomatic.api.http_helper import HTTPHelper


LOGGER = logging.getLogger(__name__)


def get_site_deploy_manifest(client, site_id, manifest_format, target):
    if target:
        target = '?target=' + target
    uri = '/sites/{}/{}{}'.format(site_id, manifest_format, target)
    return client.get(uri).decode()


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

        ret = self.client.post('/sites', data=data)
        return "New site created with id: {}".format(ret['id'])

    def update_site(self, site_id, app_version_id):
        data = {
            'app_version_id': app_version_id
        }

        ret = self.client.patch('/sites/{}'.format(site_id), data=data)
        return "Site {} updated".format(ret['id'])

    def delete_site(self, site_id):
        self.client.delete('/sites/{}'.format(site_id))
        return "Site {} deleted".format(site_id)

    def get_site_deploy_manifest(self, site_id, manifest_format, target):
        return get_site_deploy_manifest(self.client, site_id, manifest_format, target)

    def create_app(self, name, description, workflow_path, custom_nodes_path):

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
            return "New app created with id: {}".format(ret['app_id'])

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

    def infer(self, input):
        raise NotImplementedError()

    def inspect(self, workflow_path):
        raise NotImplementedError()

    def train(self):
        raise NotImplementedError()

    def upload(self):
        raise NotImplementedError()
