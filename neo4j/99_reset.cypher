// =====================================================================
// AlgoLens - delete ALL AlgoLens data (datasets, vertices, experiments)
// Constraints and indexes are kept. Run 02_sample_datasets.cypher again afterwards.
// =====================================================================
MATCH (n) WHERE n:Dataset OR n:Node OR n:Experiment
DETACH DELETE n;
