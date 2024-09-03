#!/usr/bin/env python3
#
import timeit

def format_method(x):
    return "</%s>" % (x)

def concat_method(x):
    return "</" + x + ">"

def fstring_method(x):
    return f"</{x}>"

# Test with a short string
x_short = "div"

# Test with a longer string
x_long = "very_long_tag_name_for_testing_purposes"

# Number of iterations
n = 1000000

print("Short string:")
print("Format method: ", timeit.timeit(lambda: format_method(x_short), number=n))
print("Concat method: ", timeit.timeit(lambda: concat_method(x_short), number=n))
print("fstring method:", timeit.timeit(lambda: fstring_method(x_short), number=n))

print("\nLong string:")
print("Format method: ", timeit.timeit(lambda: format_method(x_long), number=n))
print("Concat method: ", timeit.timeit(lambda: concat_method(x_long), number=n))
print("fstring method:", timeit.timeit(lambda: fstring_method(x_long), number=n))
