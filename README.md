# AlgoLens

Comparative performance analysis and visualization of searching and graph algorithms
(M.Tech mini project).

| Layer    | Technology                                   |
|----------|----------------------------------------------|
| Frontend | HTML5, CSS3, vanilla JavaScript, SVG          |
| Backend  | Python 3 + Flask (REST/JSON API)              |
| Database | Neo4j 5.x (Cypher scripts in `neo4j/`)        |

Algorithms: Binary Search, AVL Tree Search, Dijkstra, Bellman-Ford, Floyd-Warshall.

---

## 1. Folder structure

```
algolens/
├── README.md
├── start_windows.bat          one-click start on Windows
├── start_linux_mac.sh         one-click start on Linux / macOS
├── backend/
│   ├── app.py                 Flask app: API + serves the frontend
│   ├── config.py              settings and size limits
│   ├── init_db.py             runs the Neo4j scripts for you (optional)
│   ├── requirements.txt
│   ├── .env.example           copy to .env and set your Neo4j password
│   ├── algorithms/            the five algorithms (pure Python)
│   ├── services/              validation, generators, timing, Neo4j access, benchmarks
│   └── tests/                 unit tests (textbook examples from CLRS)
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/                    api, player, charts, search, graph, benchmark, experiments, main
└── neo4j/
    ├── 01_schema.cypher       constraints and indexes
    ├── 02_sample_datasets.cypher  sample graphs and key lists
    ├── 03_report_queries.cypher   queries for the report / viva
    ├── 98_clear_experiments.cypher
    └── 99_reset.cypher
```

---

## 2. Install the prerequisites

1. **Python 3.9 or newer** (3.11 or 3.12 recommended) – https://www.python.org/downloads/
   On Windows tick **“Add python.exe to PATH”** during installation.
   Check: `python --version` (on Linux/macOS: `python3 --version`).
2. **Neo4j 5.x** – any one of these:
   * **Neo4j Desktop** (easiest on Windows/macOS) – https://neo4j.com/download/
   * **Neo4j Community Server** (zip/tar) – needs Java 17 or 21.
   * **Docker**: `docker run -d --name algolens-neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/algolens123 neo4j:5`
3. A modern browser (Chrome, Edge, Firefox).

---

## 3. Set up Neo4j

### 3.1 Create and start a database

**Neo4j Desktop**
1. Open Neo4j Desktop → *New* / *Create instance* (local DBMS).
2. Name: `algolens`, set a password (at least 8 characters, e.g. `algolens123`). Remember it.
3. Click **Start**. Wait until the status is *Running*.

**Community server**: unzip, then run `bin\neo4j console` (Windows) or `bin/neo4j console`
(Linux/macOS). Open http://localhost:7474, log in with `neo4j` / `neo4j` and set a new password.

**Docker**: the command above already sets the password to `algolens123`.

The app connects with the Bolt protocol on **bolt://localhost:7687**.

### 3.2 Run the Cypher scripts (choose ONE way)

**Way A – Neo4j Browser (no tools needed)**
1. Open http://localhost:7474 (or *Open → Neo4j Browser* in Desktop) and log in.
2. Open `neo4j/01_schema.cypher` in a text editor, copy everything, paste into the Browser
   editor and press **Run** (Ctrl+Enter).
3. Do the same with `neo4j/02_sample_datasets.cypher`.
4. Check: `MATCH (d:Dataset) RETURN d.name, d.type` should return 6 rows.

   If the Browser runs only the first statement, enable
   *Settings (gear icon) → Enable multi statement query editor*, then run again.

**Way B – cypher-shell**
```
cypher-shell -a bolt://localhost:7687 -u neo4j -p algolens123 -f neo4j/01_schema.cypher
cypher-shell -a bolt://localhost:7687 -u neo4j -p algolens123 -f neo4j/02_sample_datasets.cypher
```

**Way C – Python helper** (after step 4 below)
```
cd backend
python init_db.py            # schema + sample data
python init_db.py --reset    # wipe AlgoLens data first, then reload
```

---

## 4. Set up and run the backend

### Windows (Command Prompt or PowerShell)
```
cd algolens\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
notepad .env                 # set NEO4J_PASSWORD to your password, save
python app.py
```
If PowerShell refuses to run `activate`, run once:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or use Command Prompt.

### Linux / macOS
```
cd algolens/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env                    # set NEO4J_PASSWORD, save
python app.py
```

You should see:
```
 AlgoLens backend
 Open:   http://127.0.0.1:5000
 Neo4j:  connected (bolt://localhost:7687)
```

Open **http://127.0.0.1:5000** in the browser. The badge at the top right shows
**“Neo4j connected”**. (Do not open `index.html` by double-clicking; it must be served by Flask.)

Shortcut: after creating `.env` once, `start_windows.bat` or `./start_linux_mac.sh` does all of the
above in one step.

---

## 5. Using the application

| Tab | What to do |
|-----|-----------|
| **Searching** | Pick Binary or AVL search, type keys or press *Generate*, enter a key, press *Run search*. Use ⏮ ‹ ▶ › ⏭ to replay the interval halving or the AVL insertions/rotations and search path. |
| **Shortest paths** | Type edges as `A B 4` per line (tick *Directed* if needed), or *Generate*, or *Load* a sample from Neo4j. Choose source and target, press *Run algorithm*, then step through relaxations or matrix updates. |
| **Benchmark** | Choose searching or shortest-path, tick algorithms, enter sizes (e.g. `100, 1000, 5000, 10000, 50000`), press *Run benchmark*. Charts, a table, growth observations and a CSV download are produced. |
| **Experiment history** | Every recorded run read back from Neo4j, filterable, downloadable as CSV. |
| **Method** | How time and memory are measured, and the expected complexities. |

Suggested demo for the viva:
1. Searching → *Load* “AVL rotation demo (15)” → AVL → step through all four rotation types.
2. Shortest paths → *Load* “City road network” → Dijkstra, source A, path to G (cost 15).
3. *Load* “Negative weights (CLRS 24.4)” → Bellman-Ford (S→Z = −2). Then “Negative cycle test”.
4. *Load* “All-pairs example (CLRS 25.4)” → Floyd-Warshall, watch the matrix fill.
5. Benchmark both categories and show the charts; open Neo4j Browser and run the queries in
   `neo4j/03_report_queries.cypher`.

---

## 6. Run the unit tests
```
cd backend
python -m unittest discover -s tests -v
```
21 tests check every algorithm against textbook answers and cross-check all three graph
algorithms on random graphs.

---

## 7. Measurement method (for the report)

* **Time**: `time.perf_counter_ns()`, garbage collector paused, repeated runs, **median** reported
  (also mean, stdev, min, max). Step recording is off while timing.
* **Single search**: too fast to time alone, so 1,000 identical searches are timed and divided.
* **Memory**: separate run under `tracemalloc`, peak Python allocation during the call.
  AVL memory includes building the tree.
* **Neo4j time** is measured separately (“Neo4j load”) and never mixed into algorithm time.
* **Reproducibility**: benchmarks use a seed; the same seed gives the same inputs. The
  environment (Python version, OS, CPU) is shown with every benchmark and stored with every run.

## 8. Neo4j data model

```
(:Dataset {datasetId, name, description, type:'graph'|'array', directed, nodeCount, edgeCount, values, createdAt})
(:Dataset)-[:CONTAINS]->(:Node {uid, datasetId, nodeId, label, x, y, order})
(:Node)-[:EDGE {weight, directed}]->(:Node)
(:Experiment {experimentId, algorithm, category, mode, inputSize, edgeCount, graphDensity,
              executionTimeMs, memoryKb, buildTimeMs, dbLoadMs, repeats, seed,
              pythonVersion, machine, status, createdAt})
(:Experiment)-[:USES_DATASET]->(:Dataset)
```
`executionTimeMs` is always the time of one algorithm execution (one search, or one
shortest-path computation).

## 9. API endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET  | `/api/health` | Backend and Neo4j status |
| POST | `/api/search/binary` | Binary search with steps and metrics |
| POST | `/api/search/avl` | Build AVL tree, search, rotations and metrics |
| POST | `/api/graph/dijkstra` | Dijkstra from a source |
| POST | `/api/graph/bellman-ford` | Bellman-Ford with negative-cycle detection |
| POST | `/api/graph/floyd-warshall` | All-pairs distance matrix |
| POST | `/api/benchmark` | Run a benchmark over several sizes |
| POST | `/api/generate/array`, `/api/generate/graph` | Random inputs |
| GET  | `/api/datasets`, `/api/datasets/<id>` | List / load datasets |
| POST | `/api/datasets` | Save a graph or key list |
| GET  | `/api/experiments?algorithm=` | Recorded runs |

Example:
```
curl -X POST http://127.0.0.1:5000/api/graph/dijkstra -H "Content-Type: application/json" \
  -d '{"edges":[{"source":"A","target":"B","weight":4}],"source":"A","directed":true}'
```

## 10. Troubleshooting

| Problem | Fix |
|---------|-----|
| Badge says *Neo4j offline* | Start the database; check `NEO4J_PASSWORD` and `NEO4J_URI` in `backend/.env`; restart `python app.py`. The app still works, runs just are not stored. |
| `Unauthorized` / authentication failure | Wrong password in `.env`. |
| `Address already in use` / port 5000 busy | Set `FLASK_PORT=5050` in `.env` (on macOS, AirPlay often uses 5000). |
| `python` not found (Windows) | Reinstall Python with *Add to PATH*, or use `py` instead of `python`. |
| `No module named flask` | Activate the virtual environment, then `pip install -r requirements.txt`. |
| Saved-dataset menus are empty | Run `02_sample_datasets.cypher` (or `python init_db.py`) and wait up to 15 s for the badge to turn green. |
| Benchmark is slow | Floyd-Warshall is O(V³) in pure Python; keep V ≤ 150 for quick runs. Limits are in `config.py`. |
| Database name error | Community edition uses the database `neo4j`; keep `NEO4J_DATABASE=neo4j`. |
