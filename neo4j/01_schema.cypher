// =====================================================================
// AlgoLens - Neo4j schema (constraints and indexes)
// Works with Neo4j 5.x (Community or Enterprise, Desktop, Aura, Docker)
// Safe to run more than once
// =====================================================================

// Every dataset has a unique id
CREATE CONSTRAINT dataset_id_unique IF NOT EXISTS
FOR (d:Dataset) REQUIRE d.datasetId IS UNIQUE;

// Graph vertices are unique per dataset. uid = datasetId + ':' + nodeId
CREATE CONSTRAINT node_uid_unique IF NOT EXISTS
FOR (n:Node) REQUIRE n.uid IS UNIQUE;

// Every experiment run has a unique id
CREATE CONSTRAINT experiment_id_unique IF NOT EXISTS
FOR (e:Experiment) REQUIRE e.experimentId IS UNIQUE;

// Lookups used by the application and the report queries
CREATE INDEX node_dataset_idx IF NOT EXISTS FOR (n:Node) ON (n.datasetId);
CREATE INDEX experiment_algorithm_idx IF NOT EXISTS FOR (e:Experiment) ON (e.algorithm);
CREATE INDEX experiment_created_idx IF NOT EXISTS FOR (e:Experiment) ON (e.createdAt);
