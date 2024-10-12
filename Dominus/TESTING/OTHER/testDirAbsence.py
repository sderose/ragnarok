#!/usr/bin/env python3

class E:
    def __init__(self):
        self.attributes = None

thing = E()

print("Whole dir:")
for k in dir(thing):
    print("    %-16s '%s'" % (k, getattr(thing, k)))

print("attributes: %s, type %s." % (thing.attributes, type(thing.attributes)))
