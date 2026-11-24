"""Dijkstra's algorithm with a binary heap: O((V + E) log V).

Requires non-negative edge weights.
"""
import heapq
import itertools

from .common import INF, StepRecorder, build_adjacency


def dijkstra(nodes, edges, source, directed=True, record_steps=True, max_steps=3000):
    for e in edges:
        if e["weight"] < 0:
            raise ValueError(
                f"Dijkstra's algorithm needs non-negative edge weights, but edge "
                f"{e['source']}→{e['target']} has weight {e['weight']}. "
                f"Use Bellman-Ford for graphs with negative weights.")

    adj = build_adjacency(nodes, edges, directed)
    dist = dict.fromkeys(nodes, INF)
    prev = dict.fromkeys(nodes)
    dist[source] = 0
    rec = StepRecorder(record_steps, max_steps)

    counter = itertools.count()          # tie-breaker so the heap never compares names
    heap = [(0, next(counter), source)]
    visited = set()
    order = []
    relaxations = 0
    pushes = 1

    while heap:
        d, _, u = heapq.heappop(heap)
        if u in visited:
            continue                      # stale heap entry
        visited.add(u)
        order.append(u)
        if record_steps:
            rec.add({"type": "visit", "node": u, "dist": d})
        for v, w in adj[u]:
            if v in visited:
                continue
            nd = d + w
            if nd < dist[v]:
                if record_steps:
                    rec.add({"type": "relax", "from": u, "to": v, "weight": w,
                             "oldDist": dist[v], "newDist": nd})
                dist[v] = nd
                prev[v] = u
                relaxations += 1
                heapq.heappush(heap, (nd, next(counter), v))
                pushes += 1
            elif record_steps:
                rec.add({"type": "skip", "from": u, "to": v, "weight": w,
                         "candidate": nd, "current": dist[v]})

    return {
        "source": source,
        "distances": dist,
        "previous": prev,
        "visitOrder": order,
        "relaxations": relaxations,
        "heapPushes": pushes,
        "negativeCycle": False,
        "steps": rec.steps,
        "stepsTruncated": rec.truncated,
    }
