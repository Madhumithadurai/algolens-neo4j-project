"""Make results JSON-safe: Infinity / NaN are not valid JSON, so they become null."""
import math


def sanitize(obj):
    if isinstance(obj, float):
        if math.isinf(obj) or math.isnan(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {str(k): sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize(v) for v in obj]
    if isinstance(obj, set):
        return [sanitize(v) for v in sorted(obj, key=str)]
    return obj
