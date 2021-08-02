import os
import yaml
import logging

try:
    from builtins import FileExistsError
except ImportError:
    FileExistsError = OSError

from deepomatic.api.http_helper import HTTPHelper

from .add_images import DEFAULT_USER_AGENT_PREFIX
LOGGER = logging.getLogger(__name__)


class PlatformManager(object):
    def __init__(self, client_cls=HTTPHelper):
        self.drive_client = client_cls()

    def create_app(self, name, description, app_specs):
        if app_specs is None:
            raise ValueError('Specs are mandatory for non workflow apps.')
        # creating an app from scratch
        # require to add the services manually
        data_app = {'name': name, 'desc': description, 'app_specs': app_specs}
        ret = self.drive_client.post('/apps', data=data_app)
        app_id = ret['id']
        return "New app created with id: {}".format(app_id)

    def update_app(self, app_id, name, description):
        data = {}

        if name is not None:
            data['name'] = name

        if description is not None:
            data['desc'] = description

        ret = self.drive_client.patch('/apps/{}'.format(app_id), data=data)
        return "App {} updated".format(ret['id'])

    def delete_app(self, app_id):
        self.drive_client.delete('/apps/{}'.format(app_id))
        return "App {} deleted".format(app_id)

    def create_app_version(self, app_id, name, description, version_ids):
        data = {
            'app_id': app_id,
            'name': name,
            'recognition_version_ids': version_ids
        }
        if description is not None:
            data['desc'] = description

        ret = self.drive_client.post('/app-versions', data=data)
        return "New app version created with id: {}".format(ret['id'])

    def update_app_version(self, app_version_id, name, description):
        data = {}

        if name is not None:
            data['name'] = name

        if description is not None:
            data['desc'] = description

        ret = self.drive_client.patch('/app-versions/{}'.format(app_version_id), data=data)
        return "App version {} updated".format(ret['id'])

    def delete_app_version(self, app_version_id):
        self.drive_client.delete('/app-versions/{}'.format(app_version_id))
        return "App version {} deleted".format(app_version_id)

    def create_service(self, **data):
        ret = self.drive_client.post('/services', data=data)
        return "New service created with id: {}".format(ret['id'])

    def delete_service(self, service_id):
        self.drive_client.delete('/services/{}'.format(service_id))
        return "Service {} deleted".format(service_id)


class EngagePlatformManager(object):
    def __init__(self, client_cls=HTTPHelper):
        try:
            ENGAGE_API_URL = os.environ['ENGAGE_API_URL']
        except KeyError as e:
            raise SystemExit(e, "environment variable ENGAGE_API_URL is missing.")

        try:
            slug = os.environ['ORGANIZATION_SLUG']
            FS_URL_PREFIX = "engage/fs/on-site/orgs/{}".format(slug)
        except KeyError as e:
            raise SystemExit(e, "environment variable ORGANIZATION_SLUG is missing.")

        user_agent_prefix = DEFAULT_USER_AGENT_PREFIX
        self.engage_client = client_cls(host=ENGAGE_API_URL,
                                        user_agent_prefix=user_agent_prefix,
                                        version="")

        self.apps_workflow_endpoint = "{}/apps-workflow".format(FS_URL_PREFIX)

    def create(self, name, workflow_path, custom_nodes_path):

        with open(workflow_path, 'r') as f:
            workflow = yaml.safe_load(f)
        app_specs = [{
            "queue_name": "{}.forward".format(node['name']),
            "recognition_spec_id": node['args']['model_id']
        } for node in workflow['workflow']['steps'] if node["type"] == "Inference"]

        data_app = {"name": name, "app_specs": app_specs}
        with open(workflow_path, 'r') as w:
            files = {'workflow_yaml': w}
            if custom_nodes_path is not None:
                with open(custom_nodes_path, 'r') as c:
                    files['custom_nodes_py'] = c
                    ret = self.engage_client.post('{}'.format(self.apps_workflow_endpoint),
                                                  data=data_app, files=files, content_type='multipart/mixed')
            else:
                ret = self.engage_client.post('{}'.format(self.apps_workflow_endpoint),
                                              data=data_app, files=files, content_type='multipart/mixed')

        drive_app_id = ret['drive_app_id']
        engage_app_id = ret['engage_app_id']

        return "New Engage App created with id: {}. New Drive App created with id: {}".format(engage_app_id, drive_app_id)

    def update(self, id, workflow_path, custom_nodes_path):
        # TODO: Not yet implemented in Engage
        # with open(workflow_path, 'r') as w:
        #     files = {'workflow_yaml': w}
        #     if custom_nodes_path is not None:
        #         with open(custom_nodes_path, 'r') as c:
        #             files['custom_nodes_py'] = c
        #             ret = self.engage_client.patch(f'{self.apps_workflow_endpoint}/{id}',
        #                                            data=data_app, files=files, content_type='multipart/mixed')
        #     else:
        #         ret = self.engage_client.patch(f'/apps-workflow{id}', data=data_app,
        #                                        files=files, content_type='multipart/mixed')
        #         ret = self.engage_client.patch(f'{self.apps_workflow_endpoint}/{id}',
        #                                        data=data_app, files=files, content_type='multipart/mixed')
        # return "Engage App {} updated".format(ret['id'])
        raise NotImplementedError()

    def delete(self, id):
        self.engage_client.delete('{}/{}'.format(self.apps_workflow_endpoint, id))
        return "Engage App {} deleted".format(id)
