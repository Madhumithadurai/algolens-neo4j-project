"""Input validation. Every function raises ValueError with a readable message."""
import math
import re


def to_number(value, name):
    if isinstance(value, bool) or value is None or value == "":
        raise ValueError(f"{name} must be a number.")
    try:
        num = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number (got '{value}').")
    if not math.isfinite(num):
        raise ValueError(f"{name} must be a finite number.")
    if num.is_integer() and abs(num) < 2 ** 53:
        return int(num)
    return num


def parse_number_list(value, name, max_len):
    if value is None:
        raise ValueError(f"{name} is required.")
    if isinstance(value, str):
        parts = [p for p in re.split(r"[\s,;]+", value.strip()) if p]
    elif isinstance(value, list):
        parts = value
    else:
        raise ValueError(f"{name} must be a list of numbers.")
    if not parts:
        raise ValueError(f"{name} must contain at least one number.")
    if len(parts) > max_len:
        raise ValueError(f"{name} may contain at most {max_len:,} values (got {len(parts):,}).")
    return [to_number(p, f"{name} value") for p in parts]


def clamp_int(value, default, lo, hi, name):
    if value is None or value == "":
        return default
    try:
        v = int(float(value))
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a whole number.")
    if v < lo or v > hi:
        raise ValueError(f"{name} must be between {lo:,} and {hi:,}.")
    return v


def clamp_float(value, default, lo, hi, name):
    if value is None or value == "":
        return default
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number.")
    if not math.isfinite(v) or v < lo or v > hi:
        raise ValueError(f"{name} must be between {lo} and {hi}.")
    return v


def _node_name(value):
    if value is None:
        raise ValueError("Vertex names cannot be empty.")
    name = str(value).strip()
    if not name:
        raise ValueError("Vertex names cannot be empty.")
    if len(name) > 40:
        raise ValueError(f"Vertex name '{name[:40]}…' is longer than 40 characters.")
    return name


def parse_graph(payload, max_vertices, max_edges):
    directed = bool(payload.get("directed", True))
    raw_nodes = payload.get("nodes") or []
    raw_edges = payload.get("edges") or []
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
        raise ValueError("'nodes' and 'edges' must be lists.")

    nodes, seen = [], set()

    def add(name):
        if name not in seen:
            seen.add(name)
            nodes.append(name)

    for n in raw_nodes:
        add(_node_name(n.get("id") if isinstance(n, dict) else n))

    edges = []
    for i, e in enumerate(raw_edges, 1):
        if not isinstance(e, dict):
            raise ValueError(f"Edge {i} must be an object with source, target and weight.")
        s = _node_name(e.get("source"))
        t = _node_name(e.get("target"))
        w = to_number(e.get("weight"), f"Weight of edge {s}→{t}")
        add(s)
        add(t)
        edges.append({"source": s, "target": t, "weight": w})

    if not nodes:
        raise ValueError("The graph has no vertices.")
    if len(nodes) > max_vertices:
        raise ValueError(f"This algorithm accepts at most {max_vertices:,} vertices here "
                         f"(the graph has {len(nodes):,}). Use the Benchmark tab for larger runs.")
    if len(edges) > max_edges:
        raise ValueError(f"At most {max_edges:,} edges are accepted (the graph has {len(edges):,}).")
    return {"nodes": nodes, "edges": edges, "directed": directed}


def graph_density(vertices, edges, directed):
    if vertices < 2:
        return 0.0
    possible = vertices * (vertices - 1) if directed else vertices * (vertices - 1) / 2
    return edges / possible
