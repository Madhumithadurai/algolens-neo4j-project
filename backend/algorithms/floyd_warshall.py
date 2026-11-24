"""Floyd-Warshall all-pairs shortest paths: O(V^3) time, O(V^2) memory."""
from .common import INF, StepRecorder, edge_list


def floyd_warshall(nodes, edges, source=None, directed=True, record_steps=True, max_steps=3000):
    n = len(nodes)
    idx = {name: i for i, name in enumerate(nodes)}
    dist = [[INF] * n for _ in range(n)]
    nxt = [[None] * n for _ in range(n)]
    for i in range(n):
        dist[i][i] = 0
        nxt[i][i] = i
    for s, t, w in edge_list(edges, directed):
        i, j = idx[s], idx[t]
        if w < dist[i][j]:               # keep the cheapest of parallel edges
            dist[i][j] = w
            nxt[i][j] = j

    initial = [row[:] for row in dist] if record_steps else None
    rec = StepRecorder(record_steps, max_steps)
    updates = 0

    for k in range(n):
        dk = dist[k]
        if record_steps:
            rec.add({"type": "k", "k": nodes[k], "kIndex": k})
        for i in range(n):
            dik = dist[i][k]
            if dik == INF:
                continue
            di = dist[i]
            ni = nxt[i]
            nik = ni[k]
            for j in range(n):
                nd = dik + dk[j]
                if nd < di[j]:
                    if record_steps:
                        rec.add({"type": "update", "i": nodes[i], "j": nodes[j], "k": nodes[k],
                                 "iIndex": i, "jIndex": j, "old": di[j], "new": nd})
                    di[j] = nd
                    ni[j] = nik
                    updates += 1

    neg_nodes = [nodes[i] for i in range(n) if dist[i][i] < 0]
    result = {
        "nodes": list(nodes),
        "matrix": dist,
        "negativeCycle": bool(neg_nodes),
        "negativeCycleNodes": neg_nodes,
        "updates": updates,
        "steps": rec.steps,
        "stepsTruncated": rec.truncated,
    }
    if source is not None:
        si = idx[source]
        result["source"] = source
        result["distances"] = {nodes[j]: dist[si][j] for j in range(n)}
    if record_steps:
        result["initialMatrix"] = initial
        result["next"] = nxt
    return result


def floyd_warshall_path(result, source, target):
    """Rebuild the path source → target from the 'next' matrix. [] if none."""
    nodes = result["nodes"]
    nxt = result.get("next")
    if nxt is None:
        return []
    idx = {name: i for i, name in enumerate(nodes)}
    i, j = idx[source], idx[target]
    if nxt[i][j] is None:
        return []
    path = [source]
    cur = i
    while cur != j:
        cur = nxt[cur][j]
        if cur is None or len(path) > len(nodes):
            return []                     # broken by a negative cycle
        path.append(nodes[cur])
    return path
