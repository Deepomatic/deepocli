import os
import logging
import requests
import json

API_URL = os.getenv('DEEPOMATIC_API_URL', "https://api.deepomatic.com")
API_VERSION = os.getenv('DEEPOMATIC_API_VERSION', 'v0.7') 
APP_ID = os.getenv('DEEPOMATIC_APP_ID', None)
API_KEY = os.getenv('DEEPOMATIC_API_KEY', None)

class Api(object):
    def __init__(self, api_url, api_version, headers):
        self.api_url = api_url
        self.api_version = api_version
        self.headers = headers

    def get_app_manifest(self, site_uid):
        logging.info('GET %s/%s/sites/%s/'% (self.api_url, self.api_version, site_uid))
        result = requests.get("%s/%s/sites/%s/" % (self.api_url, self.api_version, site_uid), headers=self.headers).json()
        if 'app' in result:
            logging.info('%s' % json.dumps(result, indent=4, sort_keys=True))
            return result['app']
        else:
            logging.error('App not found for site %s' % site_uid)
            return None

    @staticmethod
    def auth():
        if APP_ID is None or API_KEY is None:
            raise DeepomaticException('DEEPOMATIC_APP_ID and DEEPOMATIC_API_KEY environment variable should be set')

        headers = {
            "X-APP-ID": APP_ID,
            "X-API-KEY": API_KEY,
        }
        return Api(API_URL, API_VERSION, headers)

class Deploy(object):
    def __init__(self, expose=None):
        self.expose = expose
        self.api = Api.auth()

    def __call__(self, site_id):
        app = self.api.get_app_manifest(site_id)
        if app is None:
            return None
        else:
            services = {
                service['name'].encode("utf-8"): DockerService.create(service) for service in app['services']
            }
            services['rabbitmq'] = DockerRabbitMQ(self.expose)
            services['resource-server'] = DockerResourceServer([
                service['name'] for service in app['services']
            ])
            return {
                'version': '2.3',
                'volumes': {
                    service['name'].encode("utf-8"): {} for service in app['services']
                },
                'services': services
            }


class DockerService(object):
    def __init__(self, service):
        self.service = service
        self.environment = []
        self.volumes = []
        self.ports = []
        self.runtime = None
        self.healthcheck = None

    def __dict__(self):
        service = {
            'restart': 'always',
            'image': self.service.get('image', self.service.get('name', '')),
        }
        if len(self.environment):
            service['environment'] = self.environment
        if len(self.ports):
            service['ports'] = self.ports
        if len(self.volumes):
            service['volumes'] = self.volumes
        if self.healthcheck is not None:
            service['healthcheck'] = self.healthcheck
        if self.runtime is not None:
            service['runtime'] = self.runtime
        return service

    def __str__(self):
        return json.dumps(self.__dict__(), indent=4)
    def __repr__(self):
        return self.__str__()

    @staticmethod
    def create(service):
        if 'worker-nn' in service['circus_watchers']:
            return DockerWorkerNNService(service)
        elif 'worker-track' in service['circus_watchers']:
            return DockerWorkerTrackService(service)
        else:
            return DockerService(service)

class DockerRabbitMQ(DockerService):
    def __init__(self, expose=None):
        DockerService.__init__(self, {
            'image': 'rabbitmq:3.6-management',
            'name': 'rabbitmq'
        })
        self.environment = [
            'RABBITMQ_DEFAULT_USER=guest',
            'RABBITMQ_DEFAULT_PASS=password',
            'RABBITMQ_DEFAULT_VHOST=vulcan'
        ]
        if expose is not None:
            self.ports = ['%s:5672' % expose]

class DockerResourceServer(DockerService):
    def __init__(self, services):
        DockerService.__init__(self, {
            'image': 'deepomatic/resource-server-on-premises:0.1.0',
            'name': 'resource-server'
        })
        self.volumes = ['%s:/app/services/%s' % (service, service) for service in services]
        self.volumes.append('/mnt/resource-server/resources:/app/resources')
        self.volumes.append('/mnt/resource-server/apps:/app/apps')
        self.environment = [
            'DEEPOMATIC_API_URL=%s' % API_URL,
            'DEEPOMATIC_API_VERSION=%s' % API_VERSION,
            'DEEPOMATIC_APP_ID=%s' % APP_ID,
            'DEEPOMATIC_API_KEY=%s' % API_KEY,
            'DOWNLOAD_ON_STARTUP=1'
        ]

class DockerWorkerService(DockerService):
    def __init__(self, service):
        DockerService.__init__(self, service)
        self.volumes = [
            '/var/lib/deepomatic/license.bin:/var/lib/deepomatic/license.bin',
            '%s:%s' % (self.service['name'], '/var/lib/deepomatic')
        ]
        self.environment = [
            'ENV_TYPE=prod',
            'AMQP_URL=amqp://guest:password@rabbitmq:5672/vulcan',
            'POSTGRE_URL=',
            'LICENSE_FILENAME=/var/lib/deepomatic/license.bin',
            'MODELS_LOCAL_ROOT=/var/lib/deepomatic/resources',
            'NN_DOWNLOAD_METHOD=none',
            'AUTOSTART_WORKER=false'
        ]
        self.healthcheck = {
            'test': ['CMD', 'test', '-f', '/tmp/worker-nn-ready'],
            'interval': '1s',
            'retries': 600
        }
        self.depends_on = ['rabbitmq']
        self.runtime = 'nvidia'

class DockerWorkerNNService(DockerWorkerService):
    def __init__(self, service):
        DockerWorkerService.__init__(self, {
            'image': 'deepomatic/vulcan-worker-nn-on-premises:0.7.7',
            'name': service['name']
        })

class DockerWorkerTrackService(DockerWorkerService):
    def __init__(self, service):
        DockerWorkerService.__init__(self, {
            'image': 'deepomatic/vulcan-worker-track-on-premises:0.7.3-tf',
            'name': service['name']
        })

def deploy(*args, **kwargs):
    print(Deploy(args[0]['expose'])(args[0]['site_id']))
    