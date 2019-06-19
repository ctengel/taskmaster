#!/usr/bin/env python3

import tm
import pprint
import shelve
import sys

with shelve.open('test.pyshelve') as shelf:
    mylist = shelf['test']

mylist.add_item(sys.argv[1])

with shelve.open('test.pyshelve') as shelf:
    shelf['test'] = mylist

