# -*- coding: utf-8 -*-
import os
import sys
import requests
import platform
import json
from six import string_types
from requests.structures import CaseInsensitiveDict


class HTTPHelper(object):
    def __init__(self, token, verify, host, check_query_parameters, user_agent_suffix='', pool_maxsize=20):
        """
        Init the HTTP helper with API key and secret
        """
        if token is None:
            token = os.getenv('DEEPOMATIC_STUDIO_TOKEN')
        if token is None:
            raise RuntimeError("Please specify 'token'either by passing those values to the client or by defining the DEEPOMATIC_STUDIO_TOKEN environment variables.")

        if not host.endswith('/'):
            host += '/'
        python_version = "{0}.{1}.{2}".format(sys.version_info.major, sys.version_info.minor, sys.version_info.micro)

        user_agent_params = {
            'requests_version': requests.__version__,
            'python_version': python_version,
            'platform': platform.platform()
        }

        self.user_agent = 'deepomatic-client-python/(vesta) requests/{requests_version} python/{python_version} platform/{platform}\
            '.format(**user_agent_params)
        if user_agent_suffix:
            self.user_agent = '{} {}'.format(self.user_agent, user_agent_suffix)

        self.token = str(token)
        self.verify = verify
        self.host = host
        self.resource_prefix = host  #version

        headers = {
            'User-Agent': self.user_agent,
            'Authorization': "Token {}".format(self.token),
        }
        self.session = requests.Session()
        requests.adapters.HTTPAdapter(pool_connections=1, pool_maxsize=5)
        self.session.headers.update(headers)
        # Use pool_maxsize to cache connections for the same host
        adapter = requests.adapters.HTTPAdapter(pool_maxsize=pool_maxsize)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def setup_headers(self, headers=None, content_type=None):
        """
        Build additional headers
        """
        if headers is None:
            headers = CaseInsensitiveDict()
        elif isinstance(headers, dict):
            headers = CaseInsensitiveDict(headers)

        if content_type is not None:
            headers['Content-Type'] = content_type
            if 'Accept' not in headers:
                headers['Accept'] = content_type

        return headers

    def format_params(self, data):
        if data:
            for key, value in data.items():
                if isinstance(value, bool):
                    data[key] = int(value)
                elif isinstance(value, dict):
                    data[key] = json.dumps(value)
        return data

    def dump_json_for_multipart(self, data, files):
        def recursive_json_dump(prefix, obj, data, files, omit_dot=False):
            if isinstance(obj, dict):
                if not omit_dot:  # see comment below
                    prefix += '.'
                for key, value in obj.items():
                    recursive_json_dump(prefix + key, value, data, files)
            elif isinstance(obj, list):
                for i, value in enumerate(obj):
                    # omit_dot is True as DRF parses list of dictionnaries like this:
                    # {"parent": [{"subfield": 0}]} would be:
                    # 'parent[0]subfield': 0
                    recursive_json_dump(prefix + '[{}]'.format(i), value, data, files, omit_dot=True)
            elif hasattr(obj, 'read'):  # if is file:
                if prefix in files:
                    raise DeepomaticException("Duplicate key: " + prefix)
                files[prefix] = obj
            else:
                data[prefix] = obj

        if files is None:
            files = {}
        new_data = {}

        recursive_json_dump('', data, new_data, files, omit_dot=True)

        if len(files) == 0:
            files = None
        return new_data, files

    def make_request(self, func, resource, params=None, data=None, content_type='application/json', files=None, stream=False, *args, **kwargs):
        if isinstance(data, dict) or isinstance(data, list):
            if content_type is not None:
                if content_type.strip() == 'application/json':
                    data = json.dumps(data)
                elif content_type.strip() == 'multipart/mixed':
                    content_type = None  # will be automatically set to multipart
                    data, files = self.dump_json_for_multipart(data, files)
                elif content_type.strip() == 'multipart/form':
                    headers = None
                    content_type = None  # let requests detect the content_type
                else:
                    raise RuntimeError("Unsupported Content-Type")

        headers = self.setup_headers(content_type=content_type)
        params = self.format_params(params)

        opened_files = []
        if files is not None:
            if type(files) is dict:
                new_files = {}
                for key, file in files.items():
                    if isinstance(file, string_types):
                        if not os.path.isfile(file):
                            raise RuntimeError("Does not refer to a file: {}".format(file))
                        file = open(file, 'rb')
                        opened_files.append(file)
                    else:
                        file.seek(0)
                    new_files[key] = file
            elif type(files) is list:
                new_files = []
                for key, file in files:
                    if isinstance(file, string_types):
                        if not os.path.isfile(file):
                            raise RuntimeError("Does not refer to a file: {}".format(file))
                        file = open(file, 'rb')
                        opened_files.append(file)
                    else:
                        file.seek(0)
                    new_files.append((key, file))
            files = new_files

        if not resource.startswith('http'):
            resource = self.resource_prefix + resource
        response = func(resource, params=params, data=data, files=files, headers=headers, verify=self.verify, stream=stream, *args, **kwargs)
        # Close opened files
        for file in opened_files:
            file.close()

        if response.status_code == 204:  # delete
            return None

        if response.status_code < 200 or response.status_code >= 300:
            raise RuntimeError(response)

        if stream:
            # we asked for a stream, we let the user download it as he wants or it will load everything in RAM
            # not good for big files
            return response
        elif 'application/json' in response.headers['Content-Type']:
            return response.json()
        else:
            return response.content

    def get(self, resource, *args, **kwargs):
        """
        Perform a GET request
        """
        return self.make_request(self.session.get, resource, *args, **kwargs)

    def delete(self, resource, *args, **kwargs):
        """
        Perform a DELETE request
        """
        return self.make_request(self.session.delete, resource, *args, **kwargs)

    def post(self, resource, *args, **kwargs):
        """
        Perform a POST request
        """
        return self.make_request(self.session.post, resource, *args, **kwargs)

    def put(self, resource, *args, **kwargs):
        """
        Perform a PUT request
        """
        return self.make_request(self.session.put, resource, *args, **kwargs)

    def patch(self, resource, *args, **kwargs):
        """
        Perform a PATCH request
        """
        return self.make_request(self.session.patch, resource, *args, **kwargs)
