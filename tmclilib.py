
import requests
import json_api_doc

CT = 'application/vnd.api+json'

class TMApi:
    def __init__(self, url):
        self.url = url

    def post(self, url, data):
        r = requests.post(self.url + url, json=data, headers={'Content-Type': CT, 'Accept': CT})
        r.raise_for_status()
        return r.json()

    def get(self, url, params):
        r = requests.get(self.url + url, headers={'Accept': CT}, params)
        r.raise_for_status()
        return r.json()

    def new_task(self, name):
        return self.post('tasks', json_api_doc.serialize({'$type': 'tasks', 'name': name}))['data']['id']

    def all_tasks(self, basicfilt=None):
        params = None
        return json_api_doc.deserialize(self.get('tasks', params))
