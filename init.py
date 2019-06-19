#!/usr/bin/env python3

import tm
import shelve

mylist = tm.List('ABC Buckets')

with shelve.open('test.pyshelve') as shelf:
    shelf['test'] = mylist

