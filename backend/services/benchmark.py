"""Timing and memory measurement.

* Time:   time.perf_counter_ns(), garbage collector paused, repeated runs;
          the median is the headline figure.
* Memory: a separate run under tracemalloc, reporting the peak number of bytes
          allocated by Python during the call. It is done separately because
          tracemalloc slows code down and would distort the timings.
"""
import gc
import os
import platform
import statistics
import time
import tracemalloc


def time_callable(fn, repeats, warmup=1):
    for _ in range(warmup):
        fn()
    times = []
    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        for _ in range(repeats):
            start = time.perf_counter_ns()
            fn()
            times.append((time.perf_counter_ns() - start) / 1e6)
    finally:
        if gc_was_enabled:
            gc.enable()
    return {
        "medianMs": statistics.median(times),
        "meanMs": statistics.fmean(times),
        "stdevMs": statistics.stdev(times) if len(times) > 1 else 0.0,
        "minMs": min(times),
        "maxMs": max(times),
        "repeats": repeats,
    }


def peak_memory_kb(fn):
    gc.collect()
    already = tracemalloc.is_tracing()
    if not already:
        tracemalloc.start()
    tracemalloc.reset_peak()
    base, _ = tracemalloc.get_traced_memory()
    try:
        fn()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        if not already:
            tracemalloc.stop()
    return max(peak - base, 0) / 1024


def measure(fn, repeats, warmup=1):
    stats = time_callable(fn, repeats, warmup)
    stats["peakMemoryKb"] = peak_memory_kb(fn)
    return stats


def system_info():
    return {
        "pythonVersion": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or platform.machine(),
        "cpuCount": os.cpu_count(),
    }
