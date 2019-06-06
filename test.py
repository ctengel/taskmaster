#!/usr/bin/env python3

import tm
import pprint
import shelve

with open('ABC Buckets - Sheet1.csv', newline='') as csvfile:
    mylist = tm.List('ABC Buckets', csvfile)

with open('test.csv', 'w', newline='') as csvfile:
    mylist.export_csv(csvfile)

with shelve.open('test.pyshelve') as shelf:
    shelf['test'] = mylist

with shelve.open('test.pyshelve') as s2:
    unsh = s2['test']

with open('t2.csv', 'w', newline='') as c2:
    unsh.export_csv(c2)
