"""Helpers shared by the graph algorithms."""

INF = float("inf")


class StepRecorder:
    """Collects visualisation steps up to a limit so responses stay small."""

    def __init__(self, enabled=True, limit=3000):
        self.enabled = enabled
        self.limit = limit
        self.steps = []
        self.truncated = False

    def add(self, step):
        if not self.enabled:
            return
        if len(self.steps) < self.limit:
            self.steps.append(step)
        else:
            self.truncated = True

    def force(self, step):
        """Always keep an important step (e.g. the negative-cycle report)."""
        if self.enabled:
            self.steps.append(step)


def build_adjacency(nodes, edges, directed):
    adj = {n: [] for n in nodes}
    for e in edges:
        adj[e["source"]].append((e["target"], e["weight"]))
        if not directed and e["source"] != e["target"]:
            adj[e["target"]].append((e["source"], e["weight"]))
    return adj


def edge_list(edges, directed):
    out = [(e["source"], e["target"], e["weight"]) for e in edges]
    if not directed:
        out += [(t, s, w) for (s, t, w) in out if s != t]
    return out


def reconstruct_path(prev, source, target):
    """Follow predecessor links back from target. Returns [] if unreachable."""
    if target == source:
        return [source]
    if prev.get(target) is None:
        return []
    path = [target]
    cur = target
    guard = len(prev) + 1
    while cur != source:
        cur = prev.get(cur)
        if cur is None or len(path) > guard:   # unreachable or caught in a cycle
            return []
        path.append(cur)
    path.reverse()
    return path
