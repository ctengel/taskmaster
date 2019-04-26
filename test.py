#!/usr/bin/env python3

import tm
import pprint

with open('ABC Buckets - Sheet1.csv', newline='') as csvfile:
    mylist = tm.List('ABC Buckets', csvfile)

with open('test.csv', 'w', newline='') as csvfile:
    mylist.export_csv(csvfile)
