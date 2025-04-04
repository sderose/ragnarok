#!/usr/bin/env python3
#
import time
import random
import statistics

PUNCTS = "<>[]\\/!?&#%|-+—"  # 15 chars including em-dash
PUNCT_SET = set(PUNCTS)
PUNCT_FROZEN = frozenset(PUNCTS)
PUNCT_LIST = list(PUNCTS)
PUNCT_DICT = dict.fromkeys(PUNCTS)

def gen_test_string(length, punct_ratio=0.1):
    """Generate test string with given ratio of punctuation"""
    chars = []
    for _ in range(length):
        if random.random() < punct_ratio:
            chars.append(random.choice(PUNCTS))
        else:
            chars.append(chr(random.randint(65, 90)))  # A-Z
    return chars

def get_punct_str(chars, start_idx):
    i = start_idx
    result = []
    while i < len(chars) and chars[i] in PUNCTS:
        result.append(chars[i])
        i += 1
    return ''.join(result)

def get_punct_set(chars, start_idx):
    i = start_idx
    result = []
    while i < len(chars) and chars[i] in PUNCT_SET:
        result.append(chars[i])
        i += 1
    return ''.join(result)

def get_punct_frozen(chars, start_idx):
    i = start_idx
    result = []
    while i < len(chars) and chars[i] in PUNCT_FROZEN:
        result.append(chars[i])
        i += 1
    return ''.join(result)

def get_punct_list(chars, start_idx):
    i = start_idx
    result = []
    while i < len(chars) and chars[i] in PUNCT_LIST:
        result.append(chars[i])
        i += 1
    return ''.join(result)

def get_punct_dict(chars, start_idx):
    i = start_idx
    result = []
    while i < len(chars) and chars[i] in PUNCT_DICT:
        result.append(chars[i])
        i += 1
    return ''.join(result)

def benchmark(func, test_chars, repeats=1000):
    """Time the function over multiple repeats"""
    times = []
    for _ in range(repeats):
        start_idx = random.randint(0, len(test_chars) - 1)
        start = time.perf_counter_ns()
        func(test_chars, start_idx)
        end = time.perf_counter_ns()
        times.append(end - start)
    return statistics.mean(times), statistics.stdev(times)

# Test with different input sizes
sizes = [100, 1000, 10000]
print(f"{'Size':>8} {'Method':>10} {'Mean (ns)':>12} {'StdDev':>12}")
print("-" * 44)

for size in sizes:
    test_chars = gen_test_string(size)

    for name, func in [
        ('string', get_punct_str),
        ('set', get_punct_set),
        ('frozenset', get_punct_frozen),
        ('list', get_punct_list),
        ('dict', get_punct_dict),
    ]:
        mean, stdev = benchmark(func, test_chars)
        print(f"{size:>8} {name:>10} {mean:>12.2f} {stdev:>12.2f}")
    print()
