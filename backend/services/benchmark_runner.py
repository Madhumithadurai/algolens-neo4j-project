"""Benchmark experiments: run algorithms over increasing input sizes."""
import random

import config
from algorithms import AVLTree, bellman_ford, binary_search_fast, dijkstra, floyd_warshall
from algorithms.common import INF
from services.benchmark import peak_memory_kb, system_info, time_callable
from services.generators import generate_graph, generate_search_queries, generate_sorted_array
from services.validation import clamp_float, clamp_int, graph_density, parse_number_list

SEARCH_ALGOS = ("binary", "avl")
GRAPH_ALGOS = ("dijkstra", "bellman-ford", "floyd-warshall")
GRAPH_FUNCS = {"dijkstra": dijkstra, "bellman-ford": bellman_ford, "floyd-warshall": floyd_warshall}
NAMES = {"binary": "Binary Search", "avl": "AVL Tree Search", "dijkstra": "Dijkstra",
         "bellman-ford": "Bellman-Ford", "floyd-warshall": "Floyd-Warshall"}


def run_benchmark(payload):
    category = payload.get("category")
    if category not in ("search", "graph"):
        raise ValueError("category must be 'search' or 'graph'.")
    allowed = SEARCH_ALGOS if category == "search" else GRAPH_ALGOS
    algorithms = payload.get("algorithms") or list(allowed)
    if not isinstance(algorithms, list):
        raise ValueError("algorithms must be a list.")
    for a in algorithms:
        if a not in allowed:
            raise ValueError(f"'{a}' is not a {category} algorithm. Choose from: {', '.join(allowed)}.")

    max_size = config.BENCH_LIMITS["search"] if category == "search" else max(
        config.BENCH_LIMITS[a] for a in GRAPH_ALGOS)
    sizes = parse_number_list(payload.get("sizes"), "Input sizes", config.MAX_BENCH_SIZES)
    sizes = sorted({int(s) for s in sizes})
    min_size = 1 if category == "search" else 2
    for s in sizes:
        if s < min_size or s > max_size:
            raise ValueError(f"Each input size must be between {min_size} and {max_size:,}.")

    repeats = clamp_int(payload.get("repeats"), 5, 1, 30, "Repeats")
    seed = clamp_int(payload.get("seed"), 42, 0, 2 ** 31 - 1, "Seed")
    params = {"algorithms": algorithms, "sizes": sizes, "repeats": repeats, "seed": seed}

    if category == "search":
        queries = clamp_int(payload.get("queries"), 1000, 1, 100_000, "Queries per run")
        params["queries"] = queries
        rows = _bench_search(algorithms, sizes, repeats, queries, seed)
    else:
        density = clamp_float(payload.get("density"), 0.2, 0.001, 1.0, "Edge density")
        weights = payload.get("weights", "non-negative")
        if weights not in ("non-negative", "negative"):
            raise ValueError("weights must be 'non-negative' or 'negative'.")
        params.update({"density": density, "weights": weights})
        rows = _bench_graph(algorithms, sizes, repeats, density, weights, seed)

    return {"category": category, "parameters": params, "environment": system_info(), "results": rows}


def _bench_search(algorithms, sizes, repeats, queries, seed):
    rows = []
    for size in sizes:
        rng = random.Random(seed * 1_000_003 + size)
        values = generate_sorted_array(size, rng)
        qs = generate_search_queries(values, queries, rng)
        member = set(values)
        expected = sum(1 for q in qs if q in member)
        insertion_order = values[:]
        rng.shuffle(insertion_order)

        for algo in algorithms:
            build_ms = None
            if algo == "binary":
                def run(values=values, qs=qs):
                    f = binary_search_fast
                    hits = 0
                    for q in qs:
                        if f(values, q) >= 0:
                            hits += 1
                    return hits
                hits = run()
                stats = time_callable(run, repeats, warmup=0)
                memory_kb = peak_memory_kb(run)        # binary search needs O(1) extra memory
            else:
                def build(order=insertion_order):
                    t = AVLTree()
                    for k in order:
                        t.insert(k)
                    return t
                build_repeats = min(repeats, 3) if size > 20_000 else repeats
                build_stats = time_callable(build, build_repeats, warmup=0)
                build_ms = build_stats["medianMs"]
                build_mem = peak_memory_kb(build)      # the tree itself: O(n) extra memory
                tree = build()

                def run(tree=tree, qs=qs):
                    f = tree.contains
                    hits = 0
                    for q in qs:
                        if f(q):
                            hits += 1
                    return hits
                hits = run()
                stats = time_callable(run, repeats, warmup=0)
                memory_kb = max(build_mem, peak_memory_kb(run))

            rows.append({
                "algorithm": algo,
                "name": NAMES[algo],
                "status": "ok",
                "inputSize": size,
                "queries": len(qs),
                "executionTimeMs": stats["medianMs"] / len(qs),   # one search
                "perQueryUs": stats["medianMs"] * 1000 / len(qs),
                "totalMedianMs": stats["medianMs"],
                "totalMeanMs": stats["meanMs"],
                "totalStdevMs": stats["stdevMs"],
                "totalMinMs": stats["minMs"],
                "totalMaxMs": stats["maxMs"],
                "buildTimeMs": build_ms,
                "memoryKb": memory_kb,
                "verification": "match" if hits == expected else "mismatch",
            })
    return rows


def _close(a, b):
    if a == INF or b == INF or a is None or b is None:
        return a == b
    return abs(a - b) < 1e-9


def _bench_graph(algorithms, sizes, repeats, density, weights, seed):
    rows = []
    negative = weights == "negative"
    for size in sizes:
        rng = random.Random(seed * 1_000_003 + size)
        try:
            g = generate_graph(size, density, rng, negative=negative, directed=True,
                               max_edges=config.MAX_BENCH_EDGES)
        except ValueError as exc:
            for algo in algorithms:
                rows.append({"algorithm": algo, "name": NAMES[algo], "inputSize": size,
                             "status": "skipped", "note": str(exc)})
            continue

        nodes, edges = g["nodes"], g["edges"]
        source = nodes[0]
        base = {"inputSize": size, "edges": len(edges),
                "graphDensity": round(graph_density(size, len(edges), True), 4)}
        reference = None
        for algo in algorithms:
            row = {"algorithm": algo, "name": NAMES[algo], **base}
            limit = config.BENCH_LIMITS[algo]
            if size > limit:
                rows.append({**row, "status": "skipped",
                             "note": f"Above the {limit:,}-vertex limit for {NAMES[algo]} (see config.py)."})
                continue
            if algo == "dijkstra" and negative:
                rows.append({**row, "status": "skipped",
                             "note": "Dijkstra is not valid when edges can be negative."})
                continue

            f = GRAPH_FUNCS[algo]

            def run(f=f):
                return f(nodes, edges, source, True, False)

            out = run()
            stats = time_callable(run, repeats, warmup=0)
            mem = peak_memory_kb(run)
            dist = out["distances"]
            if reference is None:
                reference, verification = dist, "reference"
            else:
                same = all(_close(reference[n], dist[n]) for n in nodes)
                verification = "match" if same else "mismatch"
            rows.append({**row, "status": "ok",
                         "executionTimeMs": stats["medianMs"],
                         "meanMs": stats["meanMs"], "stdevMs": stats["stdevMs"],
                         "minMs": stats["minMs"], "maxMs": stats["maxMs"],
                         "memoryKb": mem, "verification": verification,
                         "negativeCycle": out.get("negativeCycle", False)})
    return rows
