#!/usr/bin/env python3

"""Script to take a shelved List and turn it into a CSV file"""

import shelve

with shelve.open('test.pyshelve') as s2:
    unsh = s2['test']

with open('t2.csv', 'w', newline='') as c2:
    unsh.export_csv(c2)
