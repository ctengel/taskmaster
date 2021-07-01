"""Task Master Client Library"""

import requests

# TODO: oo?

class Task:
    # TODO allow this to be used for new, arbitrary updates, etc
    # TODO check for conflicts
    # TODO triage
    def __init__(self, api, dct):
        self.api = api
        self.dct = dct
        self.tid = dct['id']
    def export(self):
        return self.dct
    def close(self):
        # TODO duplicate
        self.api.close_task(tid)
    def update(self, ptch):
        self.dct = self.api.update_task(self.tid, ptch)
    def warm(self, un=False):
        # TODO set schedule to now if not yet...?
        self.update({'warm': not un})
    def schedule(self, when):
        # TODO convert to string
        # TODO allow NOW... or server side
        self.update({'wakeup': when.isoformat()})


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

    def new_task(self, td):
        return Task(self, self.post('tasks/', td))

    def all_tasks(self, mode=None):
        params = None
        if mode:
            params = {'mode': mode}
        return [Task(self, x) for x in self.get('tasks/', params)]

    def one_task(self, tid=None):
        return Task(self, self.get('tasks/' + str(tid)))

    def update_task(self, tid, newdata):
        return self.put('tasks/' + str(tid), newdata)

    def close_task(self, tid, duplicate=False):
        res = self.post('tasks/' + str(tid) + '/action', {'close': True, 'duplicate': duplicate})
        if duplicate:
            return res[1]['id']
        return None

    def duplicate_task(self, tid):
        return self.post('tasks/' + str(tid) + '/action', {'duplicate': True})[1]['id']

