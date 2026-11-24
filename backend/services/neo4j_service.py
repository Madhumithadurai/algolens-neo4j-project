"""All Neo4j access goes through this class.

The application keeps working when Neo4j is offline: runs are simply not
recorded, and dataset features report that the database is unavailable.
"""
import logging
import time
import uuid

logging.getLogger("neo4j").setLevel(logging.ERROR)

try:
    from neo4j import GraphDatabase
except ImportError:  # pragma: no cover
    GraphDatabase = None


class Neo4jService:
    RETRY_SECONDS = 10

    def __init__(self, uri, user, password, database):
        self.uri, self.user, self.password, self.database = uri, user, password, database
        self._driver = None
        self._available = False
        self._checked_at = 0.0
        self.last_error = None

    # ---- connection ------------------------------------------------------------
    def _get_driver(self):
        if GraphDatabase is None:
            raise RuntimeError("The 'neo4j' package is not installed. Run: pip install -r requirements.txt")
        if self._driver is None:
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password),
                                                connection_timeout=3.0)
        return self._driver

    def is_available(self, force=False):
        now = time.monotonic()
        if not force and now - self._checked_at < self.RETRY_SECONDS:
            return self._available
        self._checked_at = now
        try:
            self._get_driver().verify_connectivity()
            self._available = True
            self.last_error = None
        except Exception as exc:  # noqa: BLE001 - any failure means "offline"
            self._available = False
            self.last_error = str(exc) or exc.__class__.__name__
            self.close()
        return self._available

    def close(self):
        if self._driver is not None:
            try:
                self._driver.close()
            except Exception:  # noqa: BLE001
                pass
            self._driver = None

    def _query(self, cypher, **params):
        with self._get_driver().session(database=self.database) as session:
            return [record.data() for record in session.run(cypher, params)]

    # ---- datasets ----------------------------------------------------------------
    def save_graph_dataset(self, name, description, nodes, edges, directed, coordinates=None):
        ds_id = "ds-" + uuid.uuid4().hex[:10]
        coordinates = coordinates or {}
        node_rows = []
        for order, n in enumerate(nodes):
            c = coordinates.get(n) or {}
            node_rows.append({"nodeId": n, "label": n, "order": order,
                              "x": c.get("x"), "y": c.get("y")})
        with self._get_driver().session(database=self.database) as session:
            session.execute_write(self._tx_create_graph, ds_id, name, description,
                                  node_rows, edges, directed)
        return ds_id

    @staticmethod
    def _tx_create_graph(tx, ds_id, name, description, nodes, edges, directed):
        tx.run("""
            CREATE (d:Dataset {datasetId: $dsId, name: $name, description: $description,
                               type: 'graph', directed: $directed,
                               nodeCount: $nodeCount, edgeCount: $edgeCount,
                               createdAt: datetime()})
        """, dsId=ds_id, name=name, description=description, directed=directed,
               nodeCount=len(nodes), edgeCount=len(edges))
        tx.run("""
            MATCH (d:Dataset {datasetId: $dsId})
            UNWIND $nodes AS n
            CREATE (d)-[:CONTAINS]->(:Node {uid: $dsId + ':' + n.nodeId, datasetId: $dsId,
                                            nodeId: n.nodeId, label: n.label, order: n.order,
                                            x: n.x, y: n.y})
        """, dsId=ds_id, nodes=nodes)
        tx.run("""
            UNWIND $edges AS e
            MATCH (a:Node {uid: $dsId + ':' + e.source})
            MATCH (b:Node {uid: $dsId + ':' + e.target})
            CREATE (a)-[:EDGE {weight: e.weight, directed: $directed}]->(b)
        """, dsId=ds_id, edges=edges, directed=directed)

    def save_array_dataset(self, name, description, values):
        ds_id = "ds-" + uuid.uuid4().hex[:10]
        self._query("""
            CREATE (d:Dataset {datasetId: $dsId, name: $name, description: $description,
                               type: 'array', values: $values, nodeCount: size($values),
                               createdAt: datetime()})
        """, dsId=ds_id, name=name, description=description, values=values)
        return ds_id

    def list_datasets(self):
        return self._query("""
            MATCH (d:Dataset)
            RETURN d.datasetId AS datasetId, d.name AS name,
                   coalesce(d.description, '') AS description,
                   coalesce(d.type, 'graph') AS type, d.directed AS directed,
                   d.nodeCount AS nodeCount, d.edgeCount AS edgeCount,
                   toString(d.createdAt) AS createdAt
            ORDER BY type, name
        """)

    def load_dataset(self, ds_id):
        rows = self._query("""
            MATCH (d:Dataset {datasetId: $dsId})
            RETURN d.datasetId AS datasetId, d.name AS name,
                   coalesce(d.description, '') AS description,
                   coalesce(d.type, 'graph') AS type, coalesce(d.directed, true) AS directed,
                   d.values AS keyList, toString(d.createdAt) AS createdAt
        """, dsId=ds_id)
        if not rows:
            return None
        ds = rows[0]
        keys = ds.pop("keyList", None)
        if ds["type"] == "array":
            ds["values"] = keys or []
            return ds
        ds["nodes"] = self._query("""
            MATCH (:Dataset {datasetId: $dsId})-[:CONTAINS]->(n:Node)
            RETURN n.nodeId AS id, n.label AS label, n.x AS x, n.y AS y
            ORDER BY coalesce(n.order, 0), n.nodeId
        """, dsId=ds_id)
        ds["edges"] = self._query("""
            MATCH (:Dataset {datasetId: $dsId})-[:CONTAINS]->(a:Node)-[r:EDGE]->(b:Node)
            RETURN a.nodeId AS source, b.nodeId AS target, r.weight AS weight
            ORDER BY coalesce(a.order, 0), coalesce(b.order, 0)
        """, dsId=ds_id)
        return ds

    # ---- experiments -----------------------------------------------------------------
    def save_experiment(self, props, dataset_id=None):
        rows = self._query("""
            CREATE (e:Experiment)
            SET e = $props, e.createdAt = datetime()
            WITH e
            OPTIONAL MATCH (d:Dataset {datasetId: $dsId})
            FOREACH (x IN CASE WHEN d IS NULL THEN [] ELSE [1] END |
                CREATE (e)-[:USES_DATASET]->(d))
            RETURN e.experimentId AS id
        """, props=props, dsId=dataset_id)
        return rows[0]["id"] if rows else None

    def list_experiments(self, algorithm=None, limit=300):
        rows = self._query("""
            MATCH (e:Experiment)
            WHERE $algorithm IS NULL OR e.algorithm = $algorithm
            OPTIONAL MATCH (e)-[:USES_DATASET]->(d:Dataset)
            WITH e, d ORDER BY e.createdAt DESC LIMIT $limit
            RETURN e {.*, createdAt: toString(e.createdAt)} AS experiment, d.name AS datasetName
        """, algorithm=algorithm, limit=limit)
        out = []
        for r in rows:
            exp = r["experiment"]
            exp["datasetName"] = r["datasetName"]
            out.append(exp)
        return out
