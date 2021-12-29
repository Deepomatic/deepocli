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
        self.version_create_from_endpoint = FS_URL_PREFIX + "/app-versions/{}/create-from"

    def create_app(self, name, application_type):
        data = {"name": name}

        if application_type:
            data["application_type"] = application_type

        response = self.engage_client.post(
            '{}'.format(self.engage_app_endpoint),
            data=data
        )

        return "EngageApp created with id: {}. DriveApp id: {}".format(
            response['id'],
            response['drive_app_id']
        )

    def delete_app(self, app_id):
        self.engage_client.delete('{}/{}'.format(self.engage_app_endpoint, app_id))
        return "EngageApp {} deleted".format(app_id)

    def create_app_version(self,
                           app_id,
                           workflow_path,
                           custom_nodes_path,
                           recognition_version_ids,
                           base_major_version):

        data = {'recognition_version_ids': recognition_version_ids}

        if base_major_version:
            data['base_major_version'] = base_major_version

        try:
            files = {'workflow_yaml': open(workflow_path, 'r')}
            if custom_nodes_path:
                files['custom_nodes_py'] = open(custom_nodes_path, 'r')

            response = self.engage_client.post(
                '{}/{}/versions'.format(self.engage_app_endpoint, app_id),
                data=data,
                files=files,
                content_type='multipart/mixed'
            )
        finally:
            for file in files.values():
                file.close()

        return "EngageApp version 'v{}.{}' created with id: {}. DriveApp version id: {}".format(
            response['major'],
            response['minor'],
            response['id'],
            response['drive_app_version_id']
        )

    def create_app_version_from(self,
                                origin,
                                workflow_path,
                                custom_nodes_path,
                                recognition_version_ids):
        data = {}
        files = {}
        kwargs = {}

        if recognition_version_ids:
            data['recognition_version_ids'] = recognition_version_ids
            kwargs['data'] = data
        try:
            if workflow_path:
                files['workflow_yaml'] = open(workflow_path, 'r')
            if custom_nodes_path:
                files['custom_nodes_py'] = open(custom_nodes_path, 'r')
            if files:
                kwargs['files'] = files
                kwargs['content_type'] = "multipart/mixed"

            response = self.engage_client.post(
                self.version_create_from_endpoint.format(origin),
                **kwargs
            )
        finally:
            for file in files.values():
                file.close()

        return "EngageApp version created with id: {} from {}. DriveApp version id: {}".format(
            response['id'],
            origin,
            response['drive_app_version_id']
        )
