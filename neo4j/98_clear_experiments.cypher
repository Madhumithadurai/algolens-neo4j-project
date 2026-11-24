// =====================================================================
// AlgoLens - delete recorded experiment runs only (datasets are kept)
// =====================================================================
MATCH (e:Experiment) DETACH DELETE e;
