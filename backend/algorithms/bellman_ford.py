"""Bellman-Ford: O(V * E). Handles negative weights and detects negative cycles."""
from .common import INF, StepRecorder, edge_list


def bellman_ford(nodes, edges, source, directed=True, record_steps=True, max_steps=3000):
    elist = edge_list(edges, directed)
    n = len(nodes)
    dist = dict.fromkeys(nodes, INF)
    prev = dict.fromkeys(nodes)
    dist[source] = 0
    rec = StepRecorder(record_steps, max_steps)

    iterations = 0
    relaxations = 0
    for i in range(1, n):
        iterations = i
        changed = False
        if record_steps:
            rec.add({"type": "iteration", "iteration": i, "maxIterations": n - 1})
        for u, v, w in elist:
            du = dist[u]
            if du != INF and du + w < dist[v]:
                if record_steps:
                    rec.add({"type": "relax", "iteration": i, "from": u, "to": v, "weight": w,
                             "oldDist": dist[v], "newDist": du + w})
                dist[v] = du + w
                prev[v] = u
                changed = True
                relaxations += 1
        if not changed:                  # early exit: nothing can change any more
            if record_steps:
                rec.add({"type": "converged", "iteration": i})
            break

    # One more pass: any further improvement means a reachable negative cycle.
    negative_cycle = False
    cycle = []
    for u, v, w in elist:
        if dist[u] != INF and dist[u] + w < dist[v]:
            negative_cycle = True
            pred = dict(prev)
            pred[v] = u
            x = v
            for _ in range(n):          # walk back n steps to land inside the cycle
                if pred[x] is None:
                    break
                x = pred[x]
            cycle = [x]
            y = pred[x]
            while y is not None and y != x and len(cycle) <= n:
                cycle.append(y)
                y = pred[y]
            cycle.reverse()
            if record_steps:
                rec.force({"type": "negative-cycle", "from": u, "to": v, "weight": w, "cycle": cycle})
            break

    return {
        "source": source,
        "distances": dist,
        "previous": prev,
        "iterations": iterations,
        "relaxations": relaxations,
        "negativeCycle": negative_cycle,
        "cycle": cycle,
        "steps": rec.steps,
        "stepsTruncated": rec.truncated,
    }
