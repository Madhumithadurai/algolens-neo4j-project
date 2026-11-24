// =====================================================================
// AlgoLens - useful queries for the report and the viva
// Run them one at a time in Neo4j Browser (http://localhost:7474)
// These are NOT run by init_db.py
// =====================================================================

// Q1. Show one graph dataset as a picture (try the other sample ids too)
MATCH (d:Dataset {datasetId: 'sample-city-roads'})-[:CONTAINS]->(n:Node)
OPTIONAL MATCH (n)-[r:EDGE]->(m:Node)
RETURN d, n, r, m;

// Q2. List every dataset
MATCH (d:Dataset)
RETURN d.datasetId AS id, d.name AS name, d.type AS type,
       d.nodeCount AS vertices_or_keys, d.edgeCount AS edges, d.createdAt AS created
ORDER BY type, name;

// Q3. Latest 25 experiment runs
MATCH (e:Experiment)
OPTIONAL MATCH (e)-[:USES_DATASET]->(d:Dataset)
RETURN e.createdAt AS created, e.algorithm AS algorithm, e.mode AS mode,
       e.inputSize AS n, e.graphDensity AS density,
       round(e.executionTimeMs, 6) AS time_ms, round(e.memoryKb, 2) AS memory_kb,
       e.dbLoadMs AS db_load_ms, d.name AS dataset
ORDER BY created DESC
LIMIT 25;

// Q4. Average time and memory per algorithm and input size (benchmark runs)
MATCH (e:Experiment {mode: 'benchmark'})
RETURN e.algorithm AS algorithm, e.inputSize AS n,
       count(*) AS runs,
       round(avg(e.executionTimeMs), 6) AS avg_time_ms,
       round(min(e.executionTimeMs), 6) AS best_time_ms,
       round(avg(e.memoryKb), 2) AS avg_memory_kb
ORDER BY algorithm, n;

// Q5. Binary search vs AVL search at each size (per single search, microseconds)
MATCH (e:Experiment {mode: 'benchmark', category: 'search'})
WITH e.inputSize AS n, e.algorithm AS algorithm, avg(e.executionTimeMs) * 1000 AS us
RETURN n,
       round(sum(CASE WHEN algorithm = 'binary' THEN us ELSE 0 END), 4) AS binary_us,
       round(sum(CASE WHEN algorithm = 'avl' THEN us ELSE 0 END), 4) AS avl_us
ORDER BY n;

// Q6. Graph algorithms side by side at each vertex count (milliseconds)
MATCH (e:Experiment {mode: 'benchmark', category: 'graph'})
WITH e.inputSize AS v, e.algorithm AS algorithm, avg(e.executionTimeMs) AS ms
RETURN v,
       round(sum(CASE WHEN algorithm = 'dijkstra' THEN ms ELSE 0 END), 3) AS dijkstra_ms,
       round(sum(CASE WHEN algorithm = 'bellman-ford' THEN ms ELSE 0 END), 3) AS bellman_ford_ms,
       round(sum(CASE WHEN algorithm = 'floyd-warshall' THEN ms ELSE 0 END), 3) AS floyd_warshall_ms
ORDER BY v;

// Q7. Runs that loaded their input from Neo4j: algorithm time vs database time
MATCH (e:Experiment)-[:USES_DATASET]->(d:Dataset)
WHERE e.dbLoadMs IS NOT NULL
RETURN d.name AS dataset, e.algorithm AS algorithm,
       round(e.executionTimeMs, 4) AS algorithm_ms, round(e.dbLoadMs, 2) AS neo4j_load_ms
ORDER BY e.createdAt DESC;

// Q8. Shortest path computed by Neo4j itself (cross-check for Dijkstra)
//     Works on non-negative graphs. Uses Cypher only, no plugins.
MATCH (a:Node {uid: 'sample-city-roads:A'}), (g:Node {uid: 'sample-city-roads:G'})
MATCH p = (a)-[:EDGE*1..6]-(g)
WITH p, reduce(total = 0, r IN relationships(p) | total + r.weight) AS cost
RETURN [n IN nodes(p) | n.nodeId] AS path, cost
ORDER BY cost ASC
LIMIT 1;
