"""Run the Cypher scripts in ../neo4j against the database configured in .env.

    python init_db.py            create schema + load sample datasets
    python init_db.py --reset    delete all AlgoLens data first, then do the above

(You can also paste the .cypher files into Neo4j Browser or run them with cypher-shell.)
"""
import os
import sys

import config

try:
    from neo4j import GraphDatabase
except ImportError:
    sys.exit("The 'neo4j' package is missing. Run: pip install -r requirements.txt")

SCRIPTS = ["01_schema.cypher", "02_sample_datasets.cypher"]


def statements(path):
    with open(path, encoding="utf-8") as fh:
        lines = [ln for ln in fh.read().splitlines() if not ln.strip().startswith("//")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def main():
    scripts = (["99_reset.cypher"] if "--reset" in sys.argv else []) + SCRIPTS
    print(f"Connecting to {config.NEO4J_URI} as {config.NEO4J_USER} ...")
    driver = GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD))
    try:
        driver.verify_connectivity()
    except Exception as exc:  # noqa: BLE001
        sys.exit(f"Could not connect: {exc}\nCheck that Neo4j is running and that the "
                 f"password in backend/.env is correct.")
    with driver.session(database=config.NEO4J_DATABASE) as session:
        for name in scripts:
            path = os.path.join(config.NEO4J_SCRIPTS_DIR, name)
            stmts = statements(path)
            for stmt in stmts:
                session.run(stmt).consume()
            print(f"  ran {name} ({len(stmts)} statements)")
        count = session.run("MATCH (d:Dataset) RETURN count(d) AS c").single()["c"]
    driver.close()
    print(f"Done. {count} datasets are now in Neo4j.")


if __name__ == "__main__":
    main()
