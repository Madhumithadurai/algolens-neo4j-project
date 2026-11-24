"""AlgoLens backend: Flask API + static frontend.

Run:  python app.py      then open http://127.0.0.1:5000
"""
import random
import time
import uuid

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

import config
from algorithms import (AVLTree, bellman_ford, binary_search, binary_search_fast, dijkstra,
                        floyd_warshall, floyd_warshall_path, reconstruct_path)
from services.benchmark import measure, system_info
from services.benchmark_runner import run_benchmark
from services.generators import generate_graph, generate_sorted_array
from services.json_safe import sanitize
from services.neo4j_service import Neo4jService
from services.validation import (clamp_float, clamp_int, graph_density, parse_graph,
                                 parse_number_list, to_number)

app = Flask(__name__, static_folder=config.FRONTEND_DIR, static_url_path="")
app.json.sort_keys = False

neo = Neo4jService(config.NEO4J_URI, config.NEO4J_USER, config.NEO4J_PASSWORD, config.NEO4J_DATABASE)
ENV = system_info()

GRAPH_FUNCS = {"dijkstra": dijkstra, "bellman-ford": bellman_ford, "floyd-warshall": floyd_warshall}


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


# ---- helpers -------------------------------------------------------------------
def respond(data, status=200):
    return jsonify(sanitize(data)), status


def body():
    data = request.get_json(silent=True)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("The request body must be a JSON object.")
    return data


def require_neo():
    if not neo.is_available(force=True):
        raise ApiError("Neo4j is not connected. Start the database and check NEO4J_* settings "
                       f"in backend/.env. Details: {neo.last_error}", 503)


def record_experiment(props, dataset_id=None):
    """Store one run in Neo4j. Returns (experimentId, note)."""
    if not neo.is_available():
        return None, "Neo4j is not connected, so this run was not recorded."
    data = {"experimentId": str(uuid.uuid4()), "status": "completed",
            "pythonVersion": ENV["pythonVersion"], "machine": ENV["platform"], **props}
    clean = {k: v for k, v in sanitize(data).items()
             if v is not None and isinstance(v, (str, int, float, bool))}
    try:
        neo.save_experiment(clean, dataset_id)
        return clean["experimentId"], None
    except Exception as exc:  # noqa: BLE001
        app.logger.warning("Could not record experiment: %s", exc)
        return None, f"Could not record the run in Neo4j: {exc}"


def resolve_keys(p):
    """Keys come either from the request or from a Neo4j array dataset."""
    dataset_id = p.get("datasetId") or None
    db_ms = None
    if p.get("array") is None and dataset_id:
        require_neo()
        start = time.perf_counter()
        ds = neo.load_dataset(dataset_id)
        db_ms = (time.perf_counter() - start) * 1000
        if ds is None:
            raise ApiError(f"Dataset '{dataset_id}' was not found in Neo4j.", 404)
        if ds["type"] != "array":
            raise ValueError("That dataset is a graph. Choose a dataset of keys.")
        values = parse_number_list(ds["values"], "Dataset values", config.WEB_LIMITS["array_max"])
    else:
        values = parse_number_list(p.get("array"), "Keys", config.WEB_LIMITS["array_max"])
    return values, db_ms, dataset_id


# ---- error handling ------------------------------------------------------------
@app.errorhandler(ValueError)
def on_value_error(err):
    return respond({"error": str(err)}, 400)


@app.errorhandler(ApiError)
def on_api_error(err):
    return respond({"error": str(err)}, err.status)


@app.errorhandler(Exception)
def on_error(err):
    if isinstance(err, HTTPException):
        return respond({"error": err.description}, err.code)
    app.logger.exception("Unhandled error")
    return respond({"error": f"Internal error: {err}"}, 500)


# ---- pages -----------------------------------------------------------------------
@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/health")
def api_health():
    up = neo.is_available(force=True)
    return respond({"status": "ok", "neo4j": up, "neo4jError": None if up else neo.last_error,
                    "neo4jUri": config.NEO4J_URI, "environment": ENV})


# ---- searching -------------------------------------------------------------------
@app.post("/api/search/binary")
def api_binary():
    p = body()
    values, db_ms, ds_id = resolve_keys(p)
    target = to_number(p.get("target"), "Target key")
    was_sorted = all(values[i] <= values[i + 1] for i in range(len(values) - 1))
    if not was_sorted:
        if p.get("autoSort", True) is False:
            raise ValueError("Binary search needs sorted keys. Sort the input first.")
        values = sorted(values)

    res = binary_search(values, target, record_steps=True)

    repeats = clamp_int(p.get("repeats"), 7, 1, 50, "Repeats")
    inner = 1000                                   # one search is too fast to time alone

    def run():
        f = binary_search_fast
        for _ in range(inner):
            f(values, target)

    stats = measure(run, repeats)
    per_us = stats["medianMs"] * 1000 / inner
    metrics = {
        "timePerSearchUs": per_us,
        "meanPerSearchUs": stats["meanMs"] * 1000 / inner,
        "stdevPerSearchUs": stats["stdevMs"] * 1000 / inner,
        "peakMemoryKb": stats["peakMemoryKb"],
        "repeats": repeats, "innerLoop": inner, "dbLoadMs": db_ms,
    }

    exp_id, note = None, "Recording is switched off for this run."
    if p.get("save", True):
        exp_id, note = record_experiment({
            "algorithm": "binary", "category": "search", "mode": "single",
            "inputSize": len(values), "executionTimeMs": per_us / 1000,
            "memoryKb": stats["peakMemoryKb"], "repeats": repeats, "dbLoadMs": db_ms,
            "found": res["found"], "comparisons": res["comparisons"]}, ds_id)

    return respond({
        "algorithm": "binary",
        "input": {"size": len(values), "target": target, "wasSorted": was_sorted},
        "result": {
            "found": res["found"], "index": res["index"], "comparisons": res["comparisons"],
            "steps": res["steps"],
            "sortedArray": values if len(values) <= config.BINARY_ARRAY_RETURN_LIMIT else None,
        },
        "metrics": metrics, "experimentId": exp_id, "recordNote": note,
    })


@app.post("/api/search/avl")
def api_avl():
    p = body()
    keys, db_ms, ds_id = resolve_keys(p)
    target = to_number(p.get("target"), "Target key")

    snapshots = len(keys) <= config.AVL_SNAPSHOT_LIMIT
    tree = AVLTree(record_steps=True, snapshots=snapshots, max_steps=config.MAX_STEPS)
    for k in keys:
        tree.insert(k)
    found = tree.search(target)

    repeats = clamp_int(p.get("repeats"), 7, 1, 50, "Repeats")

    def build():
        t = AVLTree()
        for k in keys:
            t.insert(k)
        return t

    build_stats = measure(build, repeats if len(keys) <= 20_000 else min(repeats, 3))
    fast_tree = build()
    inner = 1000

    def run():
        f = fast_tree.contains
        for _ in range(inner):
            f(target)

    search_stats = measure(run, repeats)
    per_us = search_stats["medianMs"] * 1000 / inner
    peak = max(build_stats["peakMemoryKb"], search_stats["peakMemoryKb"])
    metrics = {
        "timePerSearchUs": per_us,
        "meanPerSearchUs": search_stats["meanMs"] * 1000 / inner,
        "stdevPerSearchUs": search_stats["stdevMs"] * 1000 / inner,
        "buildTimeMs": build_stats["medianMs"], "buildStdevMs": build_stats["stdevMs"],
        "peakMemoryKb": peak, "repeats": repeats, "innerLoop": inner, "dbLoadMs": db_ms,
    }

    exp_id, note = None, "Recording is switched off for this run."
    if p.get("save", True):
        exp_id, note = record_experiment({
            "algorithm": "avl", "category": "search", "mode": "single",
            "inputSize": tree.size, "executionTimeMs": per_us / 1000,
            "buildTimeMs": build_stats["medianMs"], "memoryKb": peak, "repeats": repeats,
            "dbLoadMs": db_ms, "found": found["found"], "comparisons": found["comparisons"],
            "rotations": tree.rotations, "treeHeight": tree.height()}, ds_id)

    return respond({
        "algorithm": "avl",
        "input": {"size": len(keys), "target": target},
        "result": {
            "found": found["found"], "comparisons": found["comparisons"], "path": found["path"],
            "height": tree.height(), "size": tree.size, "rotations": tree.rotations,
            "duplicatesIgnored": len(keys) - tree.size,
            "insertSteps": tree.steps, "stepsTruncated": tree.truncated, "snapshots": snapshots,
            "tree": tree.to_dict() if tree.size <= config.AVL_TREE_RETURN_LIMIT else None,
        },
        "metrics": metrics, "experimentId": exp_id, "recordNote": note,
    })


# ---- graphs ------------------------------------------------------------------------
@app.post("/api/graph/<algo>")
def api_graph(algo):
    if algo not in GRAPH_FUNCS:
        raise ApiError(f"Unknown algorithm '{algo}'.", 404)
    p = body()
    db_ms = None
    ds_id = p.get("datasetId") or None
    if ds_id and not p.get("edges") and not p.get("nodes"):
        require_neo()
        start = time.perf_counter()
        ds = neo.load_dataset(ds_id)
        db_ms = (time.perf_counter() - start) * 1000
        if ds is None:
            raise ApiError(f"Dataset '{ds_id}' was not found in Neo4j.", 404)
        if ds["type"] != "graph":
            raise ValueError("That dataset holds keys, not a graph.")
        p = {**p, "nodes": [n["id"] for n in ds["nodes"]], "edges": ds["edges"],
             "directed": ds["directed"]}

    g = parse_graph(p, config.WEB_LIMITS[algo], config.WEB_LIMITS["max_edges"])
    nodes, edges, directed = g["nodes"], g["edges"], g["directed"]
    node_set = set(nodes)

    source = p.get("source")
    source = str(source).strip() if source not in (None, "") else nodes[0]
    if source not in node_set:
        raise ValueError(f"Source vertex '{source}' is not in the graph.")
    target = p.get("target")
    target = str(target).strip() if target not in (None, "") else None
    if target is not None and target not in node_set:
        raise ValueError(f"Target vertex '{target}' is not in the graph.")

    f = GRAPH_FUNCS[algo]
    result = f(nodes, edges, source, directed, True, config.MAX_STEPS)
    repeats = clamp_int(p.get("repeats"), 5, 1, 30, "Repeats")
    stats = measure(lambda: f(nodes, edges, source, directed, False), repeats)

    if algo == "floyd-warshall":
        path = floyd_warshall_path(result, source, target) if target else None
        result.pop("next", None)
        if len(nodes) > config.VIZ_MATRIX_LIMIT:
            result["initialMatrix"] = None
            result["steps"] = []
    else:
        path = reconstruct_path(result["previous"], source, target) if target else None
    cost = result["distances"].get(target) if (target and path) else None

    warnings = []
    if not directed and any(e["weight"] < 0 for e in edges):
        warnings.append("In an undirected graph every negative edge u-v forms a negative cycle "
                        "u→v→u, so shortest paths through it are undefined.")
    density = graph_density(len(nodes), len(edges), directed)
    metrics = {k: stats[k] for k in ("medianMs", "meanMs", "stdevMs", "minMs", "maxMs",
                                     "peakMemoryKb", "repeats")}
    metrics["dbLoadMs"] = db_ms

    exp_id, note = None, "Recording is switched off for this run."
    if p.get("save", True):
        exp_id, note = record_experiment({
            "algorithm": algo, "category": "graph", "mode": "single",
            "inputSize": len(nodes), "edgeCount": len(edges),
            "graphDensity": round(density, 4), "directed": directed,
            "executionTimeMs": stats["medianMs"], "memoryKb": stats["peakMemoryKb"],
            "repeats": repeats, "dbLoadMs": db_ms, "source": source,
            "negativeCycle": bool(result.get("negativeCycle"))}, ds_id)

    return respond({
        "algorithm": algo,
        "input": {"vertices": len(nodes), "edges": len(edges), "directed": directed,
                  "density": density, "source": source, "target": target},
        "result": result, "path": path, "pathCost": cost, "warnings": warnings,
        "metrics": metrics, "experimentId": exp_id, "recordNote": note,
    })


# ---- generators ------------------------------------------------------------------------
def _rng(p):
    seed = p.get("seed")
    return random.Random(int(seed)) if seed not in (None, "") else random.Random()


@app.post("/api/generate/array")
def api_generate_array():
    p = body()
    size = clamp_int(p.get("size"), 31, 1, config.WEB_LIMITS["array_max"], "Size")
    return respond({"values": generate_sorted_array(size, _rng(p))})


@app.post("/api/generate/graph")
def api_generate_graph():
    p = body()
    vertices = clamp_int(p.get("vertices"), 8, 1, config.WEB_LIMITS["dijkstra"], "Vertices")
    density = clamp_float(p.get("density"), 0.3, 0.0, 1.0, "Density")
    min_w = clamp_int(p.get("minWeight"), 1, 0, 1_000_000, "Minimum weight")
    max_w = clamp_int(p.get("maxWeight"), 20, 0, 1_000_000, "Maximum weight")
    g = generate_graph(vertices, density, _rng(p), min_w, max_w,
                       negative=bool(p.get("negative")), negative_cycle=bool(p.get("negativeCycle")),
                       directed=bool(p.get("directed", True)),
                       max_edges=config.WEB_LIMITS["max_edges"])
    return respond(g)


# ---- benchmark -----------------------------------------------------------------------
@app.post("/api/benchmark")
def api_benchmark():
    p = body()
    out = run_benchmark(p)
    saved, note = 0, None
    if p.get("save", True):
        if neo.is_available():
            for row in out["results"]:
                if row.get("status") != "ok":
                    continue
                exp_id, err = record_experiment({
                    "algorithm": row["algorithm"], "category": out["category"], "mode": "benchmark",
                    "inputSize": row["inputSize"], "edgeCount": row.get("edges"),
                    "graphDensity": row.get("graphDensity"),
                    "executionTimeMs": row["executionTimeMs"], "memoryKb": row["memoryKb"],
                    "buildTimeMs": row.get("buildTimeMs"), "queries": row.get("queries"),
                    "repeats": out["parameters"]["repeats"], "seed": out["parameters"]["seed"],
                    "weights": out["parameters"].get("weights"),
                    "verification": row.get("verification")})
                if exp_id:
                    saved += 1
                    row["experimentId"] = exp_id
                else:
                    note = err
        else:
            note = "Neo4j is not connected, so these results were not recorded."
    else:
        note = "Recording is switched off for this benchmark."
    out["savedCount"] = saved
    out["recordNote"] = note
    return respond(out)


# ---- datasets & experiments ------------------------------------------------------------
@app.get("/api/datasets")
def api_datasets():
    if not neo.is_available():
        return respond({"available": False, "datasets": [],
                        "message": "Neo4j is not connected."})
    return respond({"available": True, "datasets": neo.list_datasets()})


@app.get("/api/datasets/<dataset_id>")
def api_dataset(dataset_id):
    require_neo()
    start = time.perf_counter()
    ds = neo.load_dataset(dataset_id)
    elapsed = (time.perf_counter() - start) * 1000
    if ds is None:
        raise ApiError(f"Dataset '{dataset_id}' was not found.", 404)
    ds["dbLoadMs"] = elapsed
    return respond(ds)


@app.post("/api/datasets")
def api_save_dataset():
    require_neo()
    p = body()
    name = str(p.get("name") or "").strip()
    if not name:
        raise ValueError("Give the dataset a name.")
    if len(name) > 80:
        raise ValueError("Dataset names can be at most 80 characters.")
    description = str(p.get("description") or "")[:300]
    kind = p.get("type", "graph")
    if kind == "array":
        values = parse_number_list(p.get("values"), "Values", config.WEB_LIMITS["array_max"])
        ds_id = neo.save_array_dataset(name, description, values)
    elif kind == "graph":
        g = parse_graph(p, config.BENCH_LIMITS["dijkstra"], config.MAX_BENCH_EDGES)
        coords = p.get("coordinates") if isinstance(p.get("coordinates"), dict) else {}
        ds_id = neo.save_graph_dataset(name, description, g["nodes"], g["edges"], g["directed"], coords)
    else:
        raise ValueError("type must be 'graph' or 'array'.")
    return respond({"datasetId": ds_id, "name": name}, 201)


@app.get("/api/experiments")
def api_experiments():
    algorithm = request.args.get("algorithm") or None
    limit = clamp_int(request.args.get("limit"), 300, 1, 2000, "limit")
    if not neo.is_available():
        return respond({"available": False, "experiments": []})
    return respond({"available": True, "experiments": neo.list_experiments(algorithm, limit)})


if __name__ == "__main__":
    up = neo.is_available(force=True)
    print("=" * 64)
    print(" AlgoLens backend")
    print(f" Open:   http://{config.FLASK_HOST}:{config.FLASK_PORT}")
    print(f" Neo4j:  {'connected' if up else 'NOT connected'} ({config.NEO4J_URI})")
    if not up:
        print(f"         {neo.last_error}")
        print("         The app still runs; runs are just not recorded.")
    print("=" * 64)
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.FLASK_DEBUG, threaded=True)
