#!/usr/bin/env python3

"""Create an empty shelf"""

import shelve
import tm

mylist = tm.List('ABC Buckets')

with shelve.open('test.pyshelve') as shelf:
    shelf['test'] = mylist
