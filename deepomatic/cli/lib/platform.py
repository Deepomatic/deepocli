import os
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
        self.engage_client = client_cls(
            host=ENGAGE_API_URL,
            user_agent_prefix=user_agent_prefix,
            version=""
        )

        self.engage_app_endpoint = "{}/apps".format(FS_URL_PREFIX)
        self.version_clone_endpoint = FS_URL_PREFIX + "/app-versions/{}/clone"

    def create_app(self, name):
        data = {"name": name}
        response = self.engage_client.post(
            '{}'.format(self.engage_app_endpoint),
            data=data
        )

        return "New Engage App created with id: {}. Associated Drive App id: {}.".format(
            response['id'],
            response['drive_app_id']
        )

    def delete_app(self, app_id):
        self.engage_client.delete('{}/{}'.format(self.engage_app_endpoint, app_id))
        return "Engage App {} deleted".format(app_id)

    def create_app_version(self,
                           app_id,
                           workflow_path,
                           custom_nodes_path,
                           recognition_version_ids,
                           base_major_version):

        data = {'recognition_version_ids': recognition_version_ids}

        if base_major_version:
            data['base_major_version'] = base_major_version

        with open(workflow_path, 'r') as worflow_file:
            files = {'workflow_yaml': worflow_file}

            if custom_nodes_path is not None:
                with open(custom_nodes_path, 'r') as custom_nodes_file:
                    files['custom_nodes_py'] = custom_nodes_file
                    response = self.engage_client.post(
                        '{}/{}/versions'.format(self.engage_app_endpoint, app_id),
                        data=data,
                        files=files,
                        content_type='multipart/mixed'
                    )
            else:
                response = self.engage_client.post(
                    '{}/{}/versions'.format(self.engage_app_endpoint, app_id),
                    data=data,
                    files=files,
                    content_type='multipart/mixed'
                )

        return "New app version 'v{}.{}' created with id: {}".format(
            response['major'],
            response['minor'],
            response['id']
        )

    def clone_app_version(self, version_id, recognition_version_ids):
        data = {'recognition_version_ids': recognition_version_ids}

        response = self.engage_client.post(
            '{}'.format(
                self.version_clone_endpoint.format(version_id)
            ),
            data=data
        )

        return "Cloned from {}. New Engage App created with id: {}. Associated Drive App id: {}.".format(
            version_id,
            response['id'],
            response['drive_app_id']
        )
