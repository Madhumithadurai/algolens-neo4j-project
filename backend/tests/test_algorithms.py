"""Correctness tests.  Run from the backend folder:

    python -m unittest discover -s tests -v
"""
import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithms import (AVLTree, bellman_ford, binary_search, binary_search_fast,  # noqa: E402
                        dijkstra, floyd_warshall, floyd_warshall_path, reconstruct_path)
from services.generators import generate_graph  # noqa: E402

INF = float("inf")


def E(triples):
    return [{"source": s, "target": t, "weight": w} for s, t, w in triples]


CITY_NODES = list("ABCDEFG")
CITY_EDGES = E([("A", "B", 4), ("A", "C", 2), ("B", "C", 1), ("B", "D", 5), ("C", "D", 8),
                ("C", "E", 10), ("D", "E", 2), ("D", "F", 6), ("E", "F", 2), ("F", "G", 3),
                ("E", "G", 7)])
CITY_EXPECTED = {"A": 0, "B": 3, "C": 2, "D": 8, "E": 10, "F": 12, "G": 15}

CLRS_BF_NODES = list("STXYZ")
CLRS_BF_EDGES = E([("S", "T", 6), ("S", "Y", 7), ("T", "X", 5), ("T", "Y", 8), ("T", "Z", -4),
                   ("X", "T", -2), ("Y", "X", -3), ("Y", "Z", 9), ("Z", "S", 2), ("Z", "X", 7)])

CLRS_FW_NODES = ["1", "2", "3", "4", "5"]
CLRS_FW_EDGES = E([("1", "2", 3), ("1", "3", 8), ("1", "5", -4), ("2", "4", 1), ("2", "5", 7),
                   ("3", "2", 4), ("4", "1", 2), ("4", "3", -5), ("5", "4", 6)])
CLRS_FW_EXPECTED = [[0, 1, -3, 2, -4], [3, 0, -4, 1, -1], [7, 4, 0, 5, 3],
                    [2, -1, -5, 0, -2], [8, 5, 1, 6, 0]]


class BinarySearchTests(unittest.TestCase):
    def test_finds_every_key(self):
        arr = list(range(0, 200, 3))
        for i, v in enumerate(arr):
            self.assertEqual(binary_search(arr, v)["index"], i)
            self.assertEqual(binary_search_fast(arr, v), i)

    def test_missing_keys(self):
        arr = [1, 3, 5, 7]
        for t in (0, 2, 4, 6, 8):
            self.assertFalse(binary_search(arr, t)["found"])
            self.assertEqual(binary_search_fast(arr, t), -1)

    def test_comparisons_are_logarithmic(self):
        arr = list(range(1024))
        for t in (0, 511, 1023, 2000):
            self.assertLessEqual(binary_search(arr, t)["comparisons"], 11)

    def test_empty_list(self):
        self.assertFalse(binary_search([], 5)["found"])


class AVLTests(unittest.TestCase):
    def test_random_inserts_stay_balanced(self):
        rng = random.Random(7)
        keys = rng.sample(range(100000), 3000)
        t = AVLTree()
        for k in keys:
            t.insert(k)
        self.assertTrue(t.is_valid())
        self.assertEqual(t.inorder(), sorted(keys))
        self.assertLessEqual(t.height(), 1.45 * math.log2(len(keys) + 2))
        for k in keys[:500]:
            self.assertTrue(t.contains(k))
            self.assertTrue(t.search(k)["found"])
        self.assertFalse(t.contains(-1))

    def test_sorted_inserts_stay_balanced(self):
        t = AVLTree()
        for k in range(1, 1024):
            t.insert(k)
        self.assertTrue(t.is_valid())
        self.assertEqual(t.height(), 10)

    def test_all_four_rotation_cases(self):
        t = AVLTree(record_steps=True, snapshots=True)
        for k in [50, 40, 30, 60, 70, 20, 25, 80, 75, 10, 5, 35, 33, 90, 85]:
            t.insert(k)
        kinds = {r["kind"] for s in t.steps for r in s["rotations"]}
        self.assertEqual(kinds, {"LL", "RR", "LR", "RL"})
        self.assertTrue(t.is_valid())

    def test_duplicates_ignored(self):
        t = AVLTree()
        for k in [5, 5, 3, 3, 8]:
            t.insert(k)
        self.assertEqual(t.size, 3)


class DijkstraTests(unittest.TestCase):
    def test_city_roads(self):
        r = dijkstra(CITY_NODES, CITY_EDGES, "A", directed=False)
        self.assertEqual(r["distances"], CITY_EXPECTED)
        self.assertEqual(reconstruct_path(r["previous"], "A", "G"), ["A", "C", "B", "D", "E", "F", "G"])

    def test_rejects_negative_weights(self):
        with self.assertRaises(ValueError):
            dijkstra(CLRS_BF_NODES, CLRS_BF_EDGES, "S")

    def test_unreachable_vertex(self):
        r = dijkstra(["A", "B", "C"], E([("A", "B", 1)]), "A")
        self.assertEqual(r["distances"]["C"], INF)
        self.assertEqual(reconstruct_path(r["previous"], "A", "C"), [])


class BellmanFordTests(unittest.TestCase):
    def test_clrs_negative_weights(self):
        r = bellman_ford(CLRS_BF_NODES, CLRS_BF_EDGES, "S")
        self.assertFalse(r["negativeCycle"])
        self.assertEqual(r["distances"], {"S": 0, "T": 2, "X": 4, "Y": 7, "Z": -2})

    def test_detects_negative_cycle(self):
        edges = E([("S", "A", 4), ("A", "B", 1), ("B", "C", -2), ("C", "A", -1), ("C", "D", 3)])
        r = bellman_ford(list("SABCD"), edges, "S")
        self.assertTrue(r["negativeCycle"])
        self.assertEqual(set(r["cycle"]), {"A", "B", "C"})

    def test_unreachable_negative_cycle_is_ignored(self):
        edges = E([("S", "A", 1), ("B", "C", -5), ("C", "B", 1)])
        r = bellman_ford(list("SABC"), edges, "S")
        self.assertFalse(r["negativeCycle"])

    def test_matches_dijkstra_on_city(self):
        r = bellman_ford(CITY_NODES, CITY_EDGES, "A", directed=False)
        self.assertEqual(r["distances"], CITY_EXPECTED)


class FloydWarshallTests(unittest.TestCase):
    def test_clrs_matrix(self):
        r = floyd_warshall(CLRS_FW_NODES, CLRS_FW_EDGES, source="1")
        self.assertEqual(r["matrix"], CLRS_FW_EXPECTED)
        self.assertFalse(r["negativeCycle"])
        path = floyd_warshall_path(r, "1", "3")
        self.assertEqual(path, ["1", "5", "4", "3"])

    def test_detects_negative_cycle(self):
        edges = E([("A", "B", 1), ("B", "C", -2), ("C", "A", -1)])
        r = floyd_warshall(list("ABC"), edges)
        self.assertTrue(r["negativeCycle"])


class CrossCheckTests(unittest.TestCase):
    def test_all_three_agree_on_random_graphs(self):
        rng = random.Random(2026)
        for trial in range(40):
            v = rng.randint(2, 25)
            g = generate_graph(v, rng.uniform(0.05, 0.9), rng, directed=rng.random() < 0.7)
            src = g["nodes"][0]
            d1 = dijkstra(g["nodes"], g["edges"], src, g["directed"], False)["distances"]
            d2 = bellman_ford(g["nodes"], g["edges"], src, g["directed"], False)["distances"]
            d3 = floyd_warshall(g["nodes"], g["edges"], src, g["directed"], False)["distances"]
            self.assertEqual(d1, d2, f"trial {trial}")
            self.assertEqual(d1, d3, f"trial {trial}")


class GeneratorTests(unittest.TestCase):
    def test_negative_graph_has_no_negative_cycle(self):
        rng = random.Random(1)
        for _ in range(20):
            g = generate_graph(20, 0.3, rng, negative=True)
            self.assertTrue(any(e["weight"] < 0 for e in g["edges"]))
            r = bellman_ford(g["nodes"], g["edges"], g["nodes"][0], True, False)
            self.assertFalse(r["negativeCycle"])

    def test_planted_cycle_is_found(self):
        g = generate_graph(12, 0.2, random.Random(3), negative_cycle=True)
        r = bellman_ford(g["nodes"], g["edges"], g["nodes"][0], True, False)
        self.assertTrue(r["negativeCycle"])

    def test_every_vertex_reachable_from_source(self):
        g = generate_graph(60, 0.01, random.Random(5))
        r = dijkstra(g["nodes"], g["edges"], g["nodes"][0], True, False)
        self.assertTrue(all(d != INF for d in r["distances"].values()))


if __name__ == "__main__":
    unittest.main()
