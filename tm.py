
import csv
import datetime
import dateutil.parser

class Item:
    def __init__(self, what, category=None, timelines=None, lst=None):
        self.what=what
        self.category=category
        self.lst=lst
        self.schedules=[]
        if isinstance(timelines, dict):
            for k, v in timelines.items():
                self.add_schedule(k, v)
        elif timelines:
            for timeline in timelines:
                self.add_schedule(timeline[0], timeline[1])

    def add_schedule(self, timeline, pri):
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
        retdict = {s[0].get_text(): s[1] for s in self.schedules}
        retdict['Item'] = self.what
        retdict['Cat'] = self.category
        return  retdict






class List:
    def add_item(self, item, category=None, timelines=None):
        if isinstance(item, Item):
            assert not category
            assert not timelines
        else:
            item = Item(item, category, timelines, self)
        self.items.append(item)

    def add_items(self, items):
        for item in items:
            self.add_item(item)

    def __init__(self, title, csv=None, items=None, defyear=None):
        self.title=title
        self.items=[]
        self.timelines=[]
        self.cateories=set()
        if not defyear:
            defyear = datetime.date.today().year
        self.defyear = defyear
        if items:
            self.add_items(items)
        if csv:
            self.import_csv(csv)


    def import_csv(self, csvfile):
        reader = csv.DictReader(csvfile)
        for row in reader:
            item = row.pop('Item')
            cat = row.pop('Cat')
            self.add_item(item, cat, row)

    def get_timelines(self):
        return self.timelines

    def add_timeline(self, timeline):
        if timeline not in self.timelines:
            self.timelines.append(timeline)

    def get_timeline(self, end):
        if not isinstance(end, datetime.date):
            end = Timeline.str2date(end)
        for timeline in self.timelines:
            if timeline.end == end:
                return timeline
        return None

    def export_csv(self, csvfile):
        fieldnames = ['Item', 'Cat'] + [t.get_text() for t in self.get_timelines()]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for item in self.items:
            writer.writerow(item.get_dict())
        


class Timeline:
    def __init__(self, end, start=None, lst=None, items=None):
        if not isinstance(end, datetime.date):
            end = self.str2date(end)
        self.end=end
        # figure out what do do with start...
        self.start=start

    def get_text(self):
        return str(self.end)

    @staticmethod
    def str2date(stringy):
        return dateutil.parser.parse(stringy).date()


