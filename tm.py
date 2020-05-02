
"""TaskMaster core library"""

import csv
import datetime
import dateutil.parser


class Item:
    """Item on todo list"""

    def __init__(self, what, category=None, timelines=None, lst=None):
        self.what = what
        self.category = category
        self.lst = lst
        self.schedules = []
        if isinstance(timelines, dict):
            for k, v in timelines.items():
                self.add_schedule(k, v)
        elif timelines:
            for timeline in timelines:
                self.add_schedule(timeline[0], timeline[1])

    def add_schedule(self, timeline, pri):
        """Schedule this todo item for a given priority on a given schedule"""
        if isinstance(timeline, Timeline):
            if self.lst:
                self.lst.add_timeline(timeline)
        else:
            if self.lst:
                candidate = self.lst.get_timeline(timeline)
                if candidate:
                    timeline = candidate
                else:
                    timeline = Timeline(timeline)
                    self.lst.add_timeline(timeline)
            else:
                timeline = Timeline(timeline)
        self.schedules.append((timeline, pri))

    def get_dict(self):
        """Return dict form of self; suitable for JSON or CSV"""
        retdict = {s[0].get_text(): s[1] for s in self.schedules}
        retdict['Item'] = self.what
        retdict['Cat'] = self.category
        return retdict


class List:
    """A list of todos"""

    def add_item(self, item, category=None, timelines=None):
        """Add an item to this todo list

        Can be either simple string OR an Item object
        """
        if isinstance(item, Item):
            assert not category
            assert not timelines
        else:
            item = Item(item, category, timelines, self)
        self.items.append(item)

    def add_items(self, items):
        """Add multiple Item objects or strings to list"""
        for item in items:
            self.add_item(item)

    def __init__(self, title, csvfile=None, items=None, defyear=None):
        self.title = title
        self.items = []
        self.timelines = []
        self.cateories = set()
        if not defyear:
            defyear = datetime.date.today().year
        self.defyear = defyear
        if items:
            self.add_items(items)
        if csvfile:
            self.import_csv(csvfile)

    def import_csv(self, csvfile):
        """Import a CSV file into this list"""
        reader = csv.DictReader(csvfile)
        for row in reader:
            item = row.pop('Item')
            cat = row.pop('Cat')
            self.add_item(item, cat, row)

    def get_timelines(self):
        """Return list of all Timeline objects"""
        return self.timelines

    def add_timeline(self, timeline):
        """Add Timeline object to our DB if not there already"""
        if timeline not in self.timelines:
            self.timelines.append(timeline)

    def get_timeline(self, end):
        """Return a particular Timeline object based on end time"""
        if not isinstance(end, datetime.date):
            end = Timeline.str2date(end)
        for timeline in self.timelines:
            if timeline.end == end:
                return timeline
        return None

    def export_csv(self, csvfile):
        """Write a CSV file of this list"""
        fieldnames = (['Item', 'Cat'] +
                      [t.get_text() for t in self.get_timelines()])
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for item in self.items:
            writer.writerow(item.get_dict())


class Timeline:
    """A timeline in which something ought to be done"""

    def __init__(self, end, start=None, lst=None, items=None):
        if not isinstance(end, datetime.date):
            end = self.str2date(end)
        self.end = end
        # TODO figure out what do do with start...
        # TODO what do we do with lst and items?
        self.start = start

    def get_text(self):
        """Get text representation of this timeline, usually the end"""
        return str(self.end)

    @staticmethod
    def str2date(stringy):
        """Return a date object from a string"""
        return dateutil.parser.parse(stringy).date()
