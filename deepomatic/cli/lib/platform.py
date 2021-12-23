import os
import logging

try:
    from builtins import FileExistsError
except ImportError:
    FileExistsError = OSError

from deepomatic.api.http_helper import HTTPHelper
from deepomatic.cli.cmds.utils import PlatformCommandResult

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
        return PlatformCommandResult(
            ["[created] drive_app_id: {drive_app_id}"],
            {"drive_app_id": app_id}
        )

    def update_app(self, app_id, name, description):
        data = {}

        if name is not None:
            data['name'] = name

        if description is not None:
            data['desc'] = description

        ret = self.drive_client.patch('/apps/{}'.format(app_id), data=data)
        return ("[updated] drive_app_id: {drive_app_id}",), {"drive_app_id": ret["id"]}

    def delete_app(self, app_id):
        self.drive_client.delete('/apps/{}'.format(app_id))
        return ("[deleted] drive_app_id: {drive_app_id}",), {"drive_app_id": app_id}

    def create_app_version(self, app_id, name, description, version_ids):
        data = {
            'app_id': app_id,
            'name': name,
            'recognition_version_ids': version_ids
        }
        if description is not None:
            data['desc'] = description

        ret = self.drive_client.post('/app-versions', data=data)
        return ("[created] drive_app_version_id: {drive_app_version_id}",), {"drive_app_version_id": ret['id']}

    def update_app_version(self, app_version_id, name, description):
        data = {}

        if name is not None:
            data['name'] = name

        if description is not None:
            data['desc'] = description

        ret = self.drive_client.patch('/app-versions/{}'.format(app_version_id), data=data)
        return ("[updated] drive_app_version_id: {drive_app_version_id}",), {"drive_app_version_id": ret['id']}

    def delete_app_version(self, app_version_id):
        self.drive_client.delete('/app-versions/{}'.format(app_version_id))
        return ("[deleted] drive_app_version_id: {drive_app_version_id}",), {"drive_app_version_id": app_id}

    def create_service(self, **data):
        ret = self.drive_client.post('/services', data=data)
        return ("[created] service_id: {service_id}",), {"service_id": ret["id"]}

    def delete_service(self, service_id):
        self.drive_client.delete('/services/{}'.format(service_id))
        return ("[deleted] service_id: {service_id}",), {"service_id": service_id}


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

    def create_app(self, name, application_type):
        data = {"name": name}

        if application_type:
            data.update({"application_type": application_type})

        response = self.engage_client.post(
            '{}'.format(self.engage_app_endpoint),
            data=data
        )

        return (
            ("[created] engage_app_id: {engage_app_id}", "[created] drive_app_id: {drive_app_id}"),
            {
                "engage_app_id": response['id'],
                "drive_app_id": response['drive_app_id']
            }
        )

    def delete_app(self, app_id):
        self.engage_client.delete('{}/{}'.format(self.engage_app_endpoint, app_id))
        return ("[deleted] engage_app_id: {engage_app_id}",), {"engage_app_id": app_id}

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

        return (
            ("[created] engage_app_version_id: {engage_app_version_id} (v{major}.{minor})",),
            {
                "major": response['major'],
                "minor": response['minor'],
                "engage_app_version_id": response['id']
            }
        )

    def clone_app_version(self, version_id, recognition_version_ids):
        data = {'recognition_version_ids': recognition_version_ids}

        response = self.engage_client.post(
            '{}'.format(
                self.version_clone_endpoint.format(version_id)
            ),
            data=data
        )

        return (
            ("[cloned] from engage_app_version_id {version_id} to engage_app_version_id {engage_app_version_id}",),
            {
                "version_id": version_id,
                "engage_app_version_id": response['id']
            }
        )
