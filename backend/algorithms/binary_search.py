"""Binary search on a sorted list: O(log n) time, O(1) extra space."""


def binary_search(arr, target, record_steps=True):
    """Iterative binary search that also records every interval for visualisation."""
    lo, hi = 0, len(arr) - 1
    comparisons = 0
    steps = [] if record_steps else None
    while lo <= hi:
        mid = (lo + hi) // 2
        value = arr[mid]
        comparisons += 1
        if value == target:
            if record_steps:
                steps.append({"low": lo, "high": hi, "mid": mid, "value": value, "action": "found"})
            return {"found": True, "index": mid, "comparisons": comparisons, "steps": steps}
        if value < target:
            if record_steps:
                steps.append({"low": lo, "high": hi, "mid": mid, "value": value, "action": "go-right"})
            lo = mid + 1
        else:
            if record_steps:
                steps.append({"low": lo, "high": hi, "mid": mid, "value": value, "action": "go-left"})
            hi = mid - 1
    if record_steps:
        steps.append({"low": lo, "high": hi, "mid": None, "value": None, "action": "not-found"})
    return {"found": False, "index": -1, "comparisons": comparisons, "steps": steps}


def binary_search_fast(arr, target):
    """Same algorithm without step recording; used for timing."""
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) >> 1
        value = arr[mid]
        if value == target:
            return mid
        if value < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
