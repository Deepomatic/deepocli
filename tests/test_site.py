import os
from uuid import uuid4
from deepomatic.cli.lib.site import SiteManager
from contextlib import contextmanager
import tempfile
import shutil


def generate_site(name, app_version_id, desc):
    site_id = str(uuid4())
    app_id = str(uuid4())
    service_id = str(uuid4())
    resource_id = str(uuid4())
    return {
        "id": site_id,
        "name": name,
        "desc": desc,
        "app": {
            "id": app_id,
            "name": name,
            "desc": desc,
            "date_created": "2020-02-21T17:44:34.688669+01:00",
            "services": [
                {
                    "id": service_id,
                    "app_id": app_id,
                    "name": "worker-nn",
                    "docker_image": "deepomatic/run-neural-worker:0.4.0-native",
                    "resources": [
                            {
                                "id": resource_id,
                                "name": "Workflow",
                                "desc": "",
                                "dest": "/",
                                "kind": "workflow",
                                "service_id": service_id,
                                "data_link": "Nope"
                            }
                    ],
                    "circus_watchers": [
                        "worker-nn"
                    ],
                    "configuration": {
                        "runtime": "nvidia",
                        "volumes": [
                            "deepomatic-resources:/var/lib/deepomatic"
                        ],
                        "environment": [
                            "AUTOSTART_WORKER=false",
                            "AMQP_URL=amqp://$AMQP_USER:$AMQP_PASSWORD@rabbitmq:$AMQP_PORT/$AMQP_VHOST",
                            "DEEPOMATIC_STORAGE_DIR=/var/lib/deepomatic/services/worker-nn",
                            "WORKFLOWS_PATH=/var/lib/deepomatic/services/worker-nn/resources/workflows.json"
                        ]
                    }
                }
            ],
            "app_specs": [
                {
                    "queue_name": "queue",
                    "recognition_spec_id": 1
                }
            ]
        },
        "app_version": {
            "id": app_version_id,
            "name": "1.0",
            "desc": "",
            "date_created": "2020-02-21T17:44:34.881121+01:00",
            "trashed": 'false',
            "app_id": app_id,
            "recognition_version_ids": [
                    1
            ]
        },
        "site_configuration": {
            "AMQP_PORT": 5672,
            "AMQP_USER": "user",
            "AMQP_VHOST": "default",
            "AMQP_PASSWORD": "password",
            "DEEPOMATIC_APP_ID": "",
            "DEEPOMATIC_API_KEY": "",
            "DEEPOMATIC_API_URL": "https://api.deepomatic.com",
            "DEEPOMATIC_SITE_ID": "$DEEPOMATIC_SITE_ID"
        },
        "last_ping": 'null',
        "date_created": "2020-02-21T17:46:27.731257+01:00",
        "license_expiration_date": "2022-12-15",
        "license": "Nope"
    }


class MockApi(object):
    def __init__(self, *args, **kwargs):
        self.sites = {}
        self.session = self
        self.resource_prefix = ''

    def get_site_id_from_path(self, path):
        path = [p for p in path.split('/') if p != '']
        assert path[0] == 'sites'
        return path[1], path[2:]

    def get(self, path):
        site_id, extra_path = self.get_site_id_from_path(path)
        if extra_path and extra_path[0] == 'docker-compose':
            return b'docker-compose'
        return self.sites.get(site_id)

    def post(self, path, data):
        site = generate_site(**data)
        self.sites[site['id']] = site
        return site

    def delete(self, path):
        site_id, extra_path = self.get_site_id_from_path(path)
        del self.sites[site_id]

    def upgrade(self, site_id, app_id):
        self.sites[site_id]['app']['id'] = app_id

    def setup_headers(self, content_type):
        pass


@contextmanager
def tmp():
    tmp_dir = tempfile.mkdtemp()
    try:
        yield tmp_dir
    finally:
        shutil.rmtree(tmp_dir)


@contextmanager
def setup():
    tmp_dir = tempfile.mkdtemp()
    manager = SiteManager(path=tmp_dir, client_cls=MockApi)
    try:
        yield manager
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


class TestSite(object):
    def test_all(self):
        with setup() as manager:
            # create site
            app_version_id = str(uuid4())
            site = manager._client.post('/sites', dict(name='site1', app_version_id=app_version_id, desc='description'))
            site_id = site['id']
            app_id = site['app']['id']

            # install site
            assert(site_id not in manager.list())
            manager.install(site_id)
            assert(site_id in manager.list())
            assert(app_id == manager.current_app())
            assert(site_id == manager.current())

            # upgrade site

            # artificially upgrade the site (only works when using MockApi)
            new_app_id = str(uuid4())
            manager._client.upgrade(site_id, new_app_id)
            ##

            manager.upgrade()
            assert(new_app_id == manager.current_app())

            # rollback site
            manager.rollback()
            assert(app_id == manager.current_app())

            # install another site
            app_version_id2 = str(uuid4())
            site2 = manager._client.post('/sites', dict(name='site2', app_version_id=app_version_id2, desc='description'))
            site_id2 = site2['id']
            app_id2 = site2['app']['id']

            # install site2
            assert(site_id2 not in manager.list())
            manager.install(site_id2)
            assert(site_id2 in manager.list())
            assert(app_id2 == manager.current_app())
            assert(site_id2 == manager.current())

            # use site1
            assert(site_id != manager.current())
            manager.use(site_id)
            assert(site_id == manager.current())

            # uninstall site2
            assert(site_id2 in manager.list())
            manager.uninstall(site_id2)
            assert(site_id2 not in manager.list())

            # save / load site1
            with tmp() as archive_dir:
                # save
                archive_path = os.path.join(archive_dir, 'archive.tar.gz')
                manager.save(site_id, archive_path)

                # install somewhere else
                with setup() as manager2:
                    # load
                    manager2.load(archive_path)
                    assert(site_id in manager2.list())
                    manager2.use(site_id)
                    assert(app_id == manager2.current_app())
                    assert(site_id == manager2.current())

            # uninstall
            assert(site_id in manager.list())
            manager.uninstall(site_id)
            assert(site_id not in manager.list())
