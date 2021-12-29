import os
import logging

try:
    from builtins import FileExistsError
except ImportError:
    FileExistsError = OSError

from deepomatic.api.http_helper import HTTPHelper

from .add_images import DEFAULT_USER_AGENT_PREFIX


LOGGER = logging.getLogger(__name__)


class DrivePlatformManager(object):
    def __init__(self, client_cls=HTTPHelper):
        self.drive_client = client_cls()

    def create_app(self, name, description, services):
        data_app = {
            'name': name,
            'desc': description,
            'services': [{"name": service} for service in services]
        }
        ret = self.drive_client.post('/apps', data=data_app)
        app_id = ret['id']
        return "DriveApp created with id: {}".format(app_id)

    def update_app(self, app_id, name, description):
        data = {}

        if name is not None:
            data['name'] = name

        if description is not None:
            data['desc'] = description

        ret = self.drive_client.patch('/apps/{}'.format(app_id), data=data)
        return "DriveApp {} updated".format(ret['id'])

    def delete_app(self, app_id):
        self.drive_client.delete('/apps/{}'.format(app_id))
        return "DriveApp {} deleted".format(app_id)

    def create_app_version(self, app_id, name, description, app_specs, version_ids):
        data = {
            'app_id': app_id,
            'name': name,
            'app_specs': app_specs,
            'recognition_version_ids': version_ids,
            # FIXME: To update when endpoint are updated.
            'resources': []
        }
        if description is not None:
            data['desc'] = description

        ret = self.drive_client.post('/app-versions', data=data)
        return "DriveApp version created with id: {}".format(ret['id'])

    def update_app_version(self, app_version_id, name, description):
        data = {}

        if name is not None:
            data['name'] = name

        if description is not None:
            data['desc'] = description

        ret = self.drive_client.patch('/app-versions/{}'.format(app_version_id), data=data)
        return "DriveApp version {} updated".format(ret['id'])

    def delete_app_version(self, app_version_id):
        self.drive_client.delete('/app-versions/{}'.format(app_version_id))
        return "DriveApp version {} deleted".format(app_version_id)


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
                                base_major_version,
                                workflow_path,
                                custom_nodes_path,
                                recognition_version_ids):
        data = {}
        files = {}
        kwargs = {}

        if recognition_version_ids:
            data['recognition_version_ids'] = recognition_version_ids
        if base_major_version:
            data['base_major_version'] = base_major_version
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
