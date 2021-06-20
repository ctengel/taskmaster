"""Task Master Client Library"""

import requests


class TMApi:
    def __init__(self, url):
        self.url = url

    def post(self, url, data):
        r = requests.post(self.url + url, json=data)
        r.raise_for_status()
        return r.json()

    def get(self, url, params):
        r = requests.get(self.url + url, params)
        r.raise_for_status()
        return r.json()

    def new_task(self, name):
        return self.post('tasks/', {'name': name})['id']

    def all_tasks(self, basicfilt=None):
        params = None
        return self.get('tasks/', params)
