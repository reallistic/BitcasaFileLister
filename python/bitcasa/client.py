import json
import urllib
import requests

from bitcasa.filesystem import BitcasaFile, BitcasaFolder
from bitcasa.exception import BitcasaException

BASEURL = 'https://developer.api.bitcasa.com/v1/'

class BitcasaClient(object):
    def __init__(self, id, secret, redirect_url, access_token=None):
        self.id = id
        self.secret = secret
        self.redirect_url = redirect_url
        self.access_token = access_token

    @property
    def login_url(self):
        query_string = urllib.urlencode({
                'client_id': self.id,
                'redirect': self.redirect_url
            })
        return '{0}oauth2/authenticate?{1}'.format(BASEURL, query_string)

    def authenticate(self, code):
        url = '{0}oauth2/access_token'.format(BASEURL)
        params = {
                'secret': self.secret,
                'code': code
            }
        response = requests.get(url, params=params)
        result = json.loads(response.content)
        if response.status_code != 200:
            raise BitcasaException(result['error']['code'], result['error']['message'])
        access_token = result['result']['access_token']
        self.access_token = access_token

    def create_folder(self, path, name):
        url = '{0}folders{1}'.format(BASEURL, path)
        params = {
            'access_token': self.access_token
        }
        data = {
            'folder_name': name
        }
        response = requests.post(url, params=params, data=data)
        result = json.loads(response.content)
        if response.status_code != 200:
            raise BitcasaException(result['error']['code'], result['error']['message'])
        new_path = result['result']['items'][0]['path']
        return BitcasaFolder.folder_from_response(self, name, new_path, None)


    def get_folder(self, path, name='root'):
        url = '{0}folders{1}'.format(BASEURL, path)
        params = {
            'access_token': self.access_token
        }
        response = requests.get(url, params=params)
        try:
            result = json.loads(response.content)
        except ValueError:
             raise BitcasaException(response.status_code, "Failed to decode response")

        if response.status_code != 200:
            raise BitcasaException(result['error']['code'], result['error']['message'])
        return BitcasaFolder.folder_from_response(self, name, path, result['result']['items'])

    def _delete(self, type, path):
        url = '{0}{1}/'.format(BASEURL, type)
        params = {
            'access_token': self.access_token
        }
        data = {
            'path': path
        }
        response = requests.delete(url, params=params, data=data)
        result = json.loads(response.content)
        if response.status_code != 200:
            raise BitcasaException(result['error']['code'], result['error']['message'])
        result = json.loads(response.content)
        if response.status_code != 200:
            raise BitcasaException(result['error']['code'], result['error']['message'])

    def delete_folder(self, path):
        return self._delete('folders', path)

    def delete_file(self, path):
        return self._delete('files', path)

    def upload_file(self, f, filename, path, exists='fail'):
        url = '{0}files/{1}'.format(BASEURL, path)
        files = {'file':(filename, f)}
        data = {
                'exists': exists,
            }
        params = {
                'access_token': self.access_token
            }
        response = requests.post(url, params=params, files=files, data=data)
        result = json.loads(response.content)
        if response.status_code != 200:
            raise BitcasaException(result['error']['code'], result['error']['message'])
        item = result['result']['items'][0]
        f = BitcasaFile(self, item['path'], item['name'], item['extension'], item['size'])
        return f

    def _operation(self, type, operation, from_path, to_path, filename, exists='rename'):
        url = '{0}{1}/'.format(BASEURL, type)
        params = {
            'access_token': self.access_token,
            'operation': operation
        }
        data = {
            'from': from_path,
            'filename': filename,
            'exists': exists
        }
        if to_path:
            data['to'] = to_path
        response = requests.post(url, params=params, data=data)
        result = json.loads(response.content)
        if response.status_code != 200:
            raise BitcasaException(result['error']['code'], result['error']['message'])
        if type == 'folders':
            new_path = result['result']['items'][0]['path']
            new_name = result['result']['items'][0]['name']
            return BitcasaFolder.folder_from_response(self, new_name, new_path, None)
        elif type == 'files':
            item = result['result']['items'][0]
            f = BitcasaFile(self, item['path'], item['name'], item['extension'], item['size'])
            return f

    def copy_folder(self, from_path, to_path, filename, exists='rename'):
        return self._operation('folders', 'copy', from_path, to_path, filename, exists)

    def move_folder(self, from_path, to_path, filename, exists='rename'):
        return self._operation('folders', 'move', from_path, to_path, filename, exists)

    def copy_file(self, from_path, to_path, filename, exists='rename'):
        return self._operation('files', 'copy', from_path, to_path, filename, exists)

    def move_file(self, from_path, to_path, filename, exists='rename'):
        return self._operation('files', 'move', from_path, to_path, filename, exists)

    def rename_folder(self, path, new_name, exists='rename'):
        return self._operation('folders', 'rename', path, None, new_name, exists)

    def rename_file(self, path, new_name, exists='rename'):
        return self._operation('files', 'rename', path, None, new_name, exists)

    def get_file_contents(self, filename, *paths):
        url = '{0}files/{1}'.format(BASEURL, filename)
        params = [
            ('access_token', self.access_token)
        ]
        for path in paths:
            params.append(('path', path))
        qs = urllib.urlencode(params)
        url += '?' + qs
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            result = json.loads(response.content)
            raise BitcasaException(result['error']['code'], result['error']['message'])
        return response.iter_content(chunk_size=1024)
