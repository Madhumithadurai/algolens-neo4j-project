"""Reproducible random inputs for searching and graph algorithms."""
import string


def node_names(count):
    if count <= 26:
        return list(string.ascii_uppercase[:count])
    return [f"v{i}" for i in range(count)]


def generate_sorted_array(size, rng):
    """`size` distinct integers from [0, 10*size), sorted."""
    return sorted(rng.sample(range(size * 10), size))


def generate_search_queries(values, count, rng):
    """Half of the queries are present keys, half are absent keys."""
    present = set(values)
    upper = max(len(values) * 10, 10)
    queries = []
    for i in range(count):
        if i % 2 == 0:
            queries.append(rng.choice(values))
        else:
            while True:
                x = rng.randrange(upper)
                if x not in present:
                    queries.append(x)
                    break
    rng.shuffle(queries)
    return queries


def generate_graph(vertices, density, rng, min_weight=1, max_weight=20, negative=False,
                   negative_cycle=False, directed=True, max_edges=200_000):
    """
    Random weighted graph.

    * A random path from the first vertex through all others guarantees that every
      vertex is reachable from the first one (the default source).
    * negative=True: weights are re-weighted with random vertex potentials,
      w' = w + p(u) - p(v). Some edges become negative, yet every cycle keeps its
      original non-negative total, so there is never a negative cycle.
    * negative_cycle=True: plants a 3-vertex cycle with total weight -6.
    """
    if vertices < 1:
        raise ValueError("A graph needs at least one vertex.")
    if (negative or negative_cycle) and not directed:
        raise ValueError("Negative weights need a directed graph: in an undirected graph a "
                         "negative edge u-v is already a negative cycle u→v→u.")
    if min_weight > max_weight:
        raise ValueError("Minimum weight must not exceed maximum weight.")
    if negative_cycle and vertices < 3:
        raise ValueError("A negative cycle needs at least 3 vertices.")

    names = node_names(vertices)
    possible = vertices * (vertices - 1) if directed else vertices * (vertices - 1) // 2
    target = int(round(density * possible))
    target = min(max(target, vertices - 1), possible)
    if target > max_edges:
        raise ValueError(f"{vertices:,} vertices at density {density} would create {target:,} edges, "
                         f"above the limit of {max_edges:,}. Lower the density or the vertex count.")

    def key(a, b):
        return (a, b) if directed else tuple(sorted((a, b)))

    pairs = {}
    order = names[:1] + rng.sample(names[1:], len(names) - 1)
    for a, b in zip(order, order[1:]):
        pairs[key(a, b)] = True

    if target > possible * 0.5:
        if directed:
            candidates = [(a, b) for a in names for b in names if a != b]
        else:
            candidates = [(names[i], names[j]) for i in range(vertices) for j in range(i + 1, vertices)]
        rng.shuffle(candidates)
        for a, b in candidates:
            if len(pairs) >= target:
                break
            pairs.setdefault(key(a, b), True)
    else:
        while len(pairs) < target:
            a, b = rng.sample(names, 2)
            pairs.setdefault(key(a, b), True)

    potentials = {n: rng.randint(0, max_weight) for n in names} if negative else None
    edges = []
    for (s, t) in pairs:
        w = rng.randint(min_weight, max_weight)
        if negative:
            w = w + potentials[s] - potentials[t]
        edges.append({"source": s, "target": t, "weight": w})

    planted = None
    if negative_cycle:
        a, b, c = rng.sample(names, 3)
        cyc = {(a, b): -2, (b, c): -3, (c, a): -1}
        edges = [e for e in edges if (e["source"], e["target"]) not in cyc]
        edges += [{"source": s, "target": t, "weight": w} for (s, t), w in cyc.items()]
        planted = [a, b, c]

    return {"nodes": names, "edges": edges, "directed": directed, "plantedCycle": planted}
