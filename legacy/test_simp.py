#!/usr/bin/env python3

"""Simple test executable script

Relies on a specific csv file existing.
"""

import shelve
import tm

# CSV to list object
with open('todo-from-ods - Sheet2.csv', newline='') as csvfile:
    with open('tr.csv', newline='') as simpcsv:
        mylist = tm.List('todo from ods', csvfile, simpcsv=simpcsv)

# List object to CSV
with open('test_simp.csv', 'w', newline='') as csvfile:
    mylist.export_csv(csvfile)

# Send object to a shelf
with shelve.open('test_simp.pyshelve') as shelf:
    shelf['test'] = mylist

# Load same object from shelf
with shelve.open('test_simp.pyshelve') as s2:
    unsh = s2['test']

# Export it to CSV
with open('test_simp_2.csv', 'w', newline='') as c2:
    unsh.export_csv(c2)

# It's not tested, but really test.csv and t2.csv should be nearly identical
# They may differ a little from original list object but be roughly the same
