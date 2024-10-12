#!/usr/bin/env python3
#
import functools

from checkMethodDistribution import categorize

def hidden(func):
    """Attach a magic property to a method, if it's hiding a superclass
    method.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        raise AttributeError(f"'{func.__name__}' is a hidden method")
    wrapper.__is_hidden__ = True
    return wrapper


class A:
    def aardvark(self):
        print("In A.aardvark")

    def basilisk(self):
        print("In A.basilisk")

    def chimera(self):
        print("In A.chimera")

    def dryad(self):
        print("In A.dryad")

class A2(A):
    def basilisk(self):
        print("In A2.basilisk")

class A3(A2):
    def chimera(self):
        print("In A3.chimera")

    @hidden
    def dryad(self):
        raise TypeError


anA = A()
anA2 = A2()

print("A.aardvark " + str(categorize(A, "aardvark")))
print("A.basilisk " + str(categorize(A, "basilisk")))
print("A.chimera " + str(categorize(A, "chimera")))
print("A.dryad " + str(categorize(A, "dryad")))
print("A.nope " + str(categorize(A, "nope")))

print("")
print("A2.aardvark " + str(categorize(A2, "aardvark")))
print("A2.basilisk " + str(categorize(A2, "basilisk")))
print("A2.chimera " + str(categorize(A2, "chimera")))
print("A2.dryad " + str(categorize(A2, "dryad")))
print("A2.nope " + str(categorize(A2, "nope")))

print("")
print("A3.aardvark " + str(categorize(A3, "aardvark")))
print("A3.basilisk " + str(categorize(A3, "basilisk")))
print("A3.chimera " + str(categorize(A3, "chimera")))
print("A3.dryad " + str(categorize(A3, "dryad")))
print("A3.nope " + str(categorize(A3, "nope")))
