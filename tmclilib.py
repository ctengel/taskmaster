"""Task Master Client Library"""

import datetime
import requests


class Task:
    """Single task object that exists in DB"""
    # TODO allow this to be used for new, arbitrary updates, etc
    # TODO check for conflicts
    # TODO triage

    def __init__(self, api, dct):
        self.api = api
        self.dct = dct
        self.tid = dct['id']

    def export(self):
        """Dictionary representation"""
        # TODO convert to datetime here!
        return self.dct

    def close(self):
        """Close this task"""
        # TODO duplicate... return if so
        self.dct = self.api.close_task(self.tid)[0]
        return None

    def update(self, ptch):
        """Update with a dictionary"""
        self.dct = self.api.update_task(self.tid, ptch)

    def warm(self, un=False):
        """Prepare for execution

        Set un to unwarm
        """
        # TODO set schedule to now if not yet...?
        self.update({'warm': not un})

    def schedule(self, when):
        """Set a schedule"""
        # TODO allow NOW... or server side
        self.update({'wakeup': when.isoformat()})

    def getsched(self):
        """Get datetime object corresponding to wakeup"""
        # TODO this should just be native
        if not self.dct['wakeup']:
            return None
        return datetime.datetime.fromisoformat(self.dct['wakeup'])

    def set_due(self, when):
        """Set a due date"""
        self.update({'due': when.isoformat()})

    def get_due(self):
        """Get due date"""
        if not self.dct['due']:
            return None
        return datetime.datetime.fromisoformat(self.dct['due'])

    def __repr__(self):
        return 'Task({}, {}, {}, {})'.format(self.tid,
                                             self.api.url,
                                             self.dct['mode'],
                                             self.dct['name'])

    def uif(self):
        """Return an Urgent/Important/Frog string"""
        outstr = ''
        for item in ['urgent', 'important', 'frog']:
            if self.dct.get(item):
                outstr += item[0].upper()
            else:
                outstr += ' '
        return outstr


class TMApi:
    """TM API/list"""

    def __init__(self, url):
        self.tlcache = [None, None]
        self.ctcache = [None, None]
        self.url = url

    def post(self, url, data):
        """Run a post API"""
        r = requests.post(self.url + url, json=data)
        r.raise_for_status()
        return r.json()

    def get(self, url, params=None):
        """Run a get API"""
        r = requests.get(self.url + url, params)
        r.raise_for_status()
        return r.json()

    def put(self, url, data):
        """Run a put/patch API"""
        r = requests.put(self.url + url, json=data)
        r.raise_for_status()
        return r.json()

    def new_task(self, td):
        """Create a new task with a dictionary

        At a minimum add 'name'
        """
        return Task(self, self.post('tasks/', td))

    def all_tasks(self, mode=None, until=None, context=None):
        """Return all Task objects

        mode corresponds to server mode
        """
        params = None
        if mode:
            params = {'mode': mode}
            if until:
                params['until'] = until.isoformat()
            if context:
                params['context'] = context
        return [Task(self, x) for x in self.get('tasks/', params)]

    def search_tasks(self, task_search):
        """Return Tasks matching a string"""
        params = {'search': task_search}
        return [Task(self, x) for x in self.get('tasks/', params)]

    def one_task(self, tid):
        """Return one task, given an ID"""
        return Task(self, self.get('tasks/' + str(tid)))

    def update_task(self, tid, newdata):
        """Do a PUT/PATCH of a given task with dictionary

        See also Task.update()
        """
        return self.put('tasks/' + str(tid), newdata)

    def close_task(self, tid, duplicate=False):
        """Close a given task with ID, optionally also duplicating it

        See also Task.close()
        """
        res = self.post('tasks/' + str(tid) + '/action', {'close': True, 'duplicate': duplicate})
        return res

    def duplicate_task(self, tid):
        """Duplicate a task with given task ID"""
        return self.post('tasks/' + str(tid) + '/action', {'duplicate': True})[1]['id']

    def timelines(self, get_all=False, force_refresh=False):
        """Return commonly used timelines"""
        if force_refresh:
            self.tlcache = [None, None]
        if not self.tlcache[0] \
                or self.tlcache[0] <= datetime.datetime.now() - datetime.timedelta(minutes=1):
            self.tlcache[0] = datetime.datetime.now()
            self.tlcache[1] = [datetime.datetime.fromisoformat(x['timeline'])
                               for x in self.get('timelines/')]
        if get_all:
            return self.tlcache[1]
        return self.tlcache[1][0:3]

    def timelines_native(self, force_refresh=False):
        """All timelines in order"""
        return sorted(self.timelines(get_all=True, force_refresh=force_refresh))

    def contexts(self):
        """Return valid contexts"""
        if not self.ctcache[0] \
                or self.ctcache[0] <= datetime.datetime.now() - datetime.timedelta(minutes=2):
            self.ctcache[0] = datetime.datetime.now()
            self.ctcache[1] = self.get('contexts/')
        return self.ctcache[1]
