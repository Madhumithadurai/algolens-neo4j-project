// =====================================================================
// AlgoLens - sample datasets
// Run after 01_schema.cypher. Uses MERGE, so it is safe to run again.
//
// Model
//   (:Dataset)-[:CONTAINS]->(:Node)
//   (:Node)-[:EDGE {weight, directed}]->(:Node)
//   (:Experiment)-[:USES_DATASET]->(:Dataset)     created by the app
// Array datasets keep their keys in Dataset.values
// =====================================================================


// ---------------------------------------------------------------------
// 1. City road network - undirected, non-negative weights (Dijkstra)
//    Expected distances from A: A 0, B 3, C 2, D 8, E 10, F 12, G 15
// ---------------------------------------------------------------------
MERGE (d:Dataset {datasetId: 'sample-city-roads'})
SET d.name = 'City road network',
    d.description = 'Seven junctions joined by two-way roads. Weights are travel minutes.',
    d.type = 'graph', d.directed = false, d.nodeCount = 7, d.edgeCount = 11,
    d.createdAt = datetime();

MATCH (d:Dataset {datasetId: 'sample-city-roads'})
UNWIND [
  {id: 'A', x: 10, y: 50, o: 0}, {id: 'B', x: 30, y: 20, o: 1}, {id: 'C', x: 30, y: 80, o: 2},
  {id: 'D', x: 55, y: 30, o: 3}, {id: 'E', x: 55, y: 75, o: 4}, {id: 'F', x: 80, y: 50, o: 5},
  {id: 'G', x: 95, y: 85, o: 6}
] AS n
MERGE (v:Node {uid: 'sample-city-roads:' + n.id})
SET v.datasetId = 'sample-city-roads', v.nodeId = n.id, v.label = n.id,
    v.x = n.x, v.y = n.y, v.order = n.o
MERGE (d)-[:CONTAINS]->(v);

UNWIND [
  ['A','B',4], ['A','C',2], ['B','C',1], ['B','D',5], ['C','D',8], ['C','E',10],
  ['D','E',2], ['D','F',6], ['E','F',2], ['F','G',3], ['E','G',7]
] AS e
MATCH (a:Node {uid: 'sample-city-roads:' + e[0]})
MATCH (b:Node {uid: 'sample-city-roads:' + e[1]})
MERGE (a)-[r:EDGE]->(b)
SET r.weight = e[2], r.directed = false;


// ---------------------------------------------------------------------
// 2. Negative weights, no negative cycle (Bellman-Ford)
//    Graph from CLRS, Figure 24.4. Expected from S: T 2, X 4, Y 7, Z -2
// ---------------------------------------------------------------------
MERGE (d:Dataset {datasetId: 'sample-negative-weights'})
SET d.name = 'Negative weights (CLRS 24.4)',
    d.description = 'Directed graph with negative edges but no negative cycle.',
    d.type = 'graph', d.directed = true, d.nodeCount = 5, d.edgeCount = 10,
    d.createdAt = datetime();

MATCH (d:Dataset {datasetId: 'sample-negative-weights'})
UNWIND [
  {id: 'S', x: 10, y: 50, o: 0}, {id: 'T', x: 45, y: 15, o: 1}, {id: 'X', x: 90, y: 15, o: 2},
  {id: 'Y', x: 45, y: 85, o: 3}, {id: 'Z', x: 90, y: 85, o: 4}
] AS n
MERGE (v:Node {uid: 'sample-negative-weights:' + n.id})
SET v.datasetId = 'sample-negative-weights', v.nodeId = n.id, v.label = n.id,
    v.x = n.x, v.y = n.y, v.order = n.o
MERGE (d)-[:CONTAINS]->(v);

UNWIND [
  ['S','T',6], ['S','Y',7], ['T','X',5], ['T','Y',8], ['T','Z',-4],
  ['X','T',-2], ['Y','X',-3], ['Y','Z',9], ['Z','S',2], ['Z','X',7]
] AS e
MATCH (a:Node {uid: 'sample-negative-weights:' + e[0]})
MATCH (b:Node {uid: 'sample-negative-weights:' + e[1]})
MERGE (a)-[r:EDGE]->(b)
SET r.weight = e[2], r.directed = true;


// ---------------------------------------------------------------------
// 3. Negative cycle (Bellman-Ford detection test)
//    Cycle A -> B -> C -> A has total weight 1 - 2 - 1 = -2
// ---------------------------------------------------------------------
MERGE (d:Dataset {datasetId: 'sample-negative-cycle'})
SET d.name = 'Negative cycle test',
    d.description = 'A -> B -> C -> A sums to -2. Bellman-Ford must report it.',
    d.type = 'graph', d.directed = true, d.nodeCount = 5, d.edgeCount = 5,
    d.createdAt = datetime();

MATCH (d:Dataset {datasetId: 'sample-negative-cycle'})
UNWIND [
  {id: 'S', x: 5, y: 50, o: 0}, {id: 'A', x: 35, y: 50, o: 1}, {id: 'B', x: 60, y: 15, o: 2},
  {id: 'C', x: 60, y: 85, o: 3}, {id: 'D', x: 95, y: 85, o: 4}
] AS n
MERGE (v:Node {uid: 'sample-negative-cycle:' + n.id})
SET v.datasetId = 'sample-negative-cycle', v.nodeId = n.id, v.label = n.id,
    v.x = n.x, v.y = n.y, v.order = n.o
MERGE (d)-[:CONTAINS]->(v);

UNWIND [
  ['S','A',4], ['A','B',1], ['B','C',-2], ['C','A',-1], ['C','D',3]
] AS e
MATCH (a:Node {uid: 'sample-negative-cycle:' + e[0]})
MATCH (b:Node {uid: 'sample-negative-cycle:' + e[1]})
MERGE (a)-[r:EDGE]->(b)
SET r.weight = e[2], r.directed = true;


// ---------------------------------------------------------------------
// 4. All-pairs example (Floyd-Warshall)
//    Graph from CLRS, Figure 25.4. Expected final matrix (rows 1..5):
//    1: 0  1 -3  2 -4
//    2: 3  0 -4  1 -1
//    3: 7  4  0  5  3
//    4: 2 -1 -5  0 -2
//    5: 8  5  1  6  0
// ---------------------------------------------------------------------
MERGE (d:Dataset {datasetId: 'sample-all-pairs'})
SET d.name = 'All-pairs example (CLRS 25.4)',
    d.description = 'Five vertices with some negative edges, for Floyd-Warshall.',
    d.type = 'graph', d.directed = true, d.nodeCount = 5, d.edgeCount = 9,
    d.createdAt = datetime();

MATCH (d:Dataset {datasetId: 'sample-all-pairs'})
UNWIND [
  {id: '1', x: 50, y: 5, o: 0}, {id: '2', x: 95, y: 40, o: 1}, {id: '3', x: 78, y: 95, o: 2},
  {id: '4', x: 22, y: 95, o: 3}, {id: '5', x: 5, y: 40, o: 4}
] AS n
MERGE (v:Node {uid: 'sample-all-pairs:' + n.id})
SET v.datasetId = 'sample-all-pairs', v.nodeId = n.id, v.label = n.id,
    v.x = n.x, v.y = n.y, v.order = n.o
MERGE (d)-[:CONTAINS]->(v);

UNWIND [
  ['1','2',3], ['1','3',8], ['1','5',-4], ['2','4',1], ['2','5',7],
  ['3','2',4], ['4','1',2], ['4','3',-5], ['5','4',6]
] AS e
MATCH (a:Node {uid: 'sample-all-pairs:' + e[0]})
MATCH (b:Node {uid: 'sample-all-pairs:' + e[1]})
MERGE (a)-[r:EDGE]->(b)
SET r.weight = e[2], r.directed = true;


// ---------------------------------------------------------------------
// 5. Key lists for the searching algorithms
// ---------------------------------------------------------------------
MERGE (d:Dataset {datasetId: 'sample-sorted-keys'})
SET d.name = 'Sorted keys (15)',
    d.description = 'Fifteen sorted integers for binary search.',
    d.type = 'array',
    d.values = [3, 8, 15, 21, 27, 34, 42, 56, 63, 71, 79, 88, 94, 101, 117],
    d.nodeCount = 15, d.createdAt = datetime();

MERGE (d:Dataset {datasetId: 'sample-avl-rotations'})
SET d.name = 'AVL rotation demo (15)',
    d.description = 'Insertion order chosen to trigger LL, RR, LR and RL rotations.',
    d.type = 'array',
    d.values = [50, 40, 30, 60, 70, 20, 25, 80, 75, 10, 5, 35, 33, 90, 85],
    d.nodeCount = 15, d.createdAt = datetime();
