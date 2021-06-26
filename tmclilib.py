"""Task Master Client Library"""

import requests


class TMApi:
    def __init__(self, url):
        self.url = url

    def post(self, url, data):
        r = requests.post(self.url + url, json=data)
        r.raise_for_status()
        return r.json()

    def get(self, url, params=None):
        r = requests.get(self.url + url, params)
        r.raise_for_status()
        return r.json()

    def put(self, url, data):
        r = requests.put(self.url + url, json=data)
        r.raise_for_status()
        return r.json()

    def new_task(self, name):
        return self.post('tasks/', {'name': name})['id']

    def all_tasks(self, basicfilt=None):
        params = None
        return self.get('tasks/', params)

    def one_task(self, tid=None):
        return self.get('tasks/' + str(tid))

    def update_task(self, tid, newname):
        self.put('tasks/' + str(tid), {'name': newname})

    def close_task(self, tid, duplicate=False):
        res = self.post('tasks/' + str(tid) + '/action', {'close': True, 'duplicate': duplicate})
        if duplicate:
            return res[1]['id']
        return None

    def duplicate_task(self, tid):
        return self.post('tasks/' + str(tid) + '/action', {'duplicate': True})[1]['id']

