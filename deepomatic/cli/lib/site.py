import errno
import requests
import json
import os
import os.path
import shutil
import subprocess

from git import Repo
from deepomatic.api.http_helper import HTTPHelper


DEEPOMATIC_SITE_PATH = os.path.join(os.path.expanduser('~'), '.deepomatic', 'sites')


def makedirs(folder, *args, **kwargs):
    # python2/3 compatible implementation of os.makedirs(exist_ok=True)
    # cf https://stackoverflow.com/a/60371380
    try:
        return os.makedirs(folder, exist_ok=True, *args, **kwargs)
    except TypeError:
        # Unexpected arguments encountered
        pass

    try:
        # Should work is TypeError was caused by exist_ok, eg., Py2
        return os.makedirs(folder, *args, **kwargs)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

        if os.path.isfile(folder):
            # folder is a file, raise OSError just like os.makedirs() in Py3
            raise


class SiteManager(object):
    def __init__(self, path=DEEPOMATIC_SITE_PATH, client_cls=HTTPHelper):
        makedirs(path)
        self._repo = Repo.init(path)
        self._client = client_cls()

        api_key = os.getenv('DEEPOMATIC_API_KEY')
        self.session = requests.Session()
        self.session.headers.update({'Content-type': 'application/json',
                                     'Authorization': 'Token {}'.format(api_key)})

    def get(self, site_id):
        return self._client.get('/sites/{}'.format(site_id))

    def create(self, name, description, app_version_id):
        data = {
            'name': name,
            'app_version_id': app_version_id
        }
        if description is not None:
            data['desc'] = description

        ret = self._client.post('/sites', data=data)
        return "New site created with id: {}".format(ret['id'])

    def update(self, site_id, app_version_id):
        data = {
            'app_version_id': app_version_id
        }

        ret = self._client.patch('/sites/{}'.format(site_id), data=data)
        return "Site {} updated".format(ret['id'])

    def delete(self, site_id):
        self._client.delete('/sites/{}'.format(site_id))
        return "Site {} deleted".format(site_id)

    def current(self):
        return str(self._repo.head.reference)

    def current_app(self):
        return self._repo.head.commit.message

    def get_deployment_manifest(self, site_id, target):
        uri = '/sites/{}/deployment-manifest?target={}'.format(site_id, target)
        return self._client.get(uri).decode()

    def install(self, site_id):
        site = self.get(site_id)
        docker_compose = self.get_deployment_manifest(site_id, 'docker-compose')
        try:
            # create branch
            self._repo.git.checkout(site_id, orphan=True)
        except Exception:
            return None

        docker_compose_path = os.path.join(self._repo.working_tree_dir, 'docker-compose.yml')
        with open(docker_compose_path, 'w') as f:
            f.write(docker_compose)

        # add to index
        self._repo.index.add([docker_compose_path])

        # commit
        self._repo.index.commit(site['app']['id'])

        return site['app']['id']

    def list(self):
        return [head.name for head in self._repo.heads]

    def load(self, archive_path):
        self._repo.git.bundle('verify', archive_path)
        site_id = self._repo.git.bundle('list-heads', archive_path).split('/')[-1]
        return self._repo.git.fetch(archive_path, '{}:{}'.format(site_id, site_id))

    def logs(self):
        return self._run_docker_compose("logs", "-f", "-t")

    def rollback(self, n=1):
        self._repo.git.reset("HEAD~{}".format(n), hard=True)
        return self._repo.head.commit.committed_datetime

    def save(self, site_id, archive_path):
        return self._repo.git.bundle('create', archive_path, site_id)

    def start(self):
        return self._run_docker_compose("up", "-d")

    def status(self):
        return self._run_docker_compose("ps")

    def stop(self):
        return self._run_docker_compose("down", "-v")

    def uninstall(self, site_id):
        try:
            self._repo.git.branch(site_id, D=True)
        except Exception:
            # last site, we can delete the repo
            shutil.rmtree(self._repo.working_tree_dir)

    def upgrade(self):
        site_id = self.current()
        site = self.get(site_id)

        if (self._repo.head.commit.message == site['app']['id']):
            return

        docker_compose = self.get_deployment_manifest(site_id, 'docker-compose')

        docker_compose_path = os.path.join(self._repo.working_tree_dir, 'docker-compose.yml')
        with open(docker_compose_path, 'w') as f:
            f.write(docker_compose)

        # add to index
        self._repo.index.add([docker_compose_path])

        # commit
        self._repo.index.commit(site['app']['id'])

        return site['app']['id']

    def use(self, site_id):
        if hasattr(self._repo.heads, site_id):
            getattr(self._repo.heads, site_id).checkout()
            return True
        else:
            # site does not exist
            return False

    def _run_docker_compose(self, *args):
        site_id = self.current()
        command = ' '.join(["docker-compose", "-f", os.path.join(DEEPOMATIC_SITE_PATH, "docker-compose.yml")] + list(args))
        env = {
            "DEEPOMATIC_SITE_ID": site_id
        }
        p = subprocess.Popen(command, env=env, shell=True)
        try:
            p.wait()
        except KeyboardInterrupt:
            try:
                p.terminate()
            except OSError:
                pass
            p.wait()

    def make_work_order_url(self, base_url):
        return "{}/v0.2/work-orders".format(base_url)

    def create_work_order(self, base_url, name, metadata):
        work_order_url = self.make_work_order_url(base_url)
        data = {
            'name': name,
            'metadata': metadata
        }
        res = self.session.post(work_order_url + '/', data=json.dumps(data))
        if res.status_code == 201:
            return res.json()['id']
        else:
            return res.text

    def status_work_order(self, base_url, work_order_id):
        work_order_url = self.make_work_order_url(base_url)
        res = self.session.get('{}/{}'.format(work_order_url, work_order_id))
        if res.status_code == 200:
            return res.json()
        else:
            return res.text

    def delete_work_order(self, base_url, work_order_id):
        work_order_url = self.make_work_order_url(base_url)
        res = self.session.delete('{}/{}'.format(work_order_url, work_order_id))
        if res.status_code == 204:
            return "Work order deleted"
        else:
            return res.text

    def make_work_order_inference(self, base_url, work_order_id, entries, metadata):
        work_order_url = self.make_work_order_url(base_url)
        input_data_url = "{}/{}/analyze".format(work_order_url, work_order_id)
        data = {
            'inputs': entries,
            "metadata": metadata
        }
        res = self.session.post(input_data_url + '/', data=json.dumps(data))
        if res.status_code == 200:
            return res.json()
        else:
            return res.text
