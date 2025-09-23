#!/usr/bin/env python3
#
#pylint: disable=W0612
#
import time
import array
from io import StringIO
import statistics
from tabulate import tabulate

from strbuf import StrBuf
from stringioplus import SIO

def warmup():
    """Warm up the Python interpreter to get more consistent timing results"""
    # Do some string operations to warm up
    s = ""
    for _ in range(1000):
        s += "x"

    arr = array.array('u')
    for _ in range(1000):
        arr.append('x')

    sio = StringIO()
    for _ in range(1000):
        sio.write('x')

    lst = []
    for _ in range(1000):
        lst.append('x')

def time_str_concat(size):
    """Time string concatenation using += operator"""
    s = ""
    start = time.perf_counter()
    for _ in range(size):
        s += "x"
    end = time.perf_counter()
    return end - start

def time_array_append(size):
    """Time building string using array.array('u')"""
    arr = array.array('u')
    start = time.perf_counter()
    for _ in range(size):
        arr.append('x')
    s = ''.join(arr)
    end = time.perf_counter()
    return end - start

def time_stringio_write(size):
    """Time building string using StringIO"""
    sio = StringIO()
    start = time.perf_counter()
    for _ in range(size):
        sio.write('x')
    s = sio.getvalue()
    end = time.perf_counter()
    return end - start

def time_SIO_write(size):
    sio = SIO()
    start = time.perf_counter()
    for _ in range(size):
        sio.append('x')
    s = sio.getvalue()
    end = time.perf_counter()
    return end - start

def time_list_append(size):
    """Time building string using list append"""
    lst = []
    start = time.perf_counter()
    for _ in range(size):
        lst.append('x')
    s = ''.join(lst)
    end = time.perf_counter()
    return end - start

def time_prelist(size):
    start = time.perf_counter()
    lst = [None] * size
    for i in range(size):
        lst[i] = 'x'
    s = ''.join(lst)
    end = time.perf_counter()
    return end - start

def time_StrBuf_append(size):
    s = StrBuf("")
    start = time.perf_counter()
    for _ in range(size):
        s.append('x')
    end = time.perf_counter()
    return end - start


def run_benchmark(sizes, trials=5):
    """Run benchmarks for different string building methods"""
    results = []
    methods = {
        'str': time_str_concat,
        'array': time_array_append,
        'StringIO': time_stringio_write,
        'SIO': time_SIO_write,
        'list': time_list_append,
        'prelist': time_prelist,
        'StrBuf': time_StrBuf_append,
    }

    print("Warming up...")
    warmup()

    print("Running benchmarks...")
    for size in sizes:
        row = {'Size': size}
        for method_name, method_func in methods.items():
            # Run multiple trials
            times = [method_func(size) for _ in range(trials)]
            # Use median to reduce impact of outliers
            row[method_name] = statistics.median(times)
        results.append(row)

    return results

def format_results(results):
    """Format results into a pretty table"""
    headers = ['Size', 'str', 'array', 'StringIO', 'SIO', 'list', 'prelist', 'StrBuf' ]
    rows = []
    for result in results:
        row = [
            result['Size'],
            f"{result['str']:.6f}",
            f"{result['array']:.6f}",
            f"{result['StringIO']:.6f}",
            f"{result['SIO']:.6f}",
            f"{result['list']:.6f}",
            f"{result['prelist']:.6f}",
            f"{result['StrBuf']:.6f}"
        ]
        rows.append(row)
    return tabulate(rows, headers=headers, tablefmt='grid')

def main():
    # Test sizes by powers of 2
    sizes = [2**i for i in range(8, 20)]
    results = run_benchmark(sizes)
    print("\nResults (times in seconds):")
    print(format_results(results))

if __name__ == "__main__":
    main()
