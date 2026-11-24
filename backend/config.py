"""Central configuration. Values can be overridden in backend/.env"""
import os

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is optional
    load_dotenv = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if load_dotenv:
    load_dotenv(os.path.join(BASE_DIR, ".env"))


def _bool(name, default):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


# ---- Neo4j -----------------------------------------------------------------
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# ---- Flask -----------------------------------------------------------------
FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = _bool("FLASK_DEBUG", False)

FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))
NEO4J_SCRIPTS_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "neo4j"))

# ---- Limits for interactive (single) runs ------------------------------------
WEB_LIMITS = {
    "array_max": 200_000,      # keys for binary / AVL search
    "dijkstra": 2_000,         # vertices
    "bellman-ford": 500,       # vertices
    "floyd-warshall": 150,     # vertices (O(V^3) time, O(V^2) memory)
    "max_edges": 100_000,
}

# ---- Limits for benchmark runs -----------------------------------------------
BENCH_LIMITS = {
    "search": 200_000,
    "dijkstra": 5_000,
    "bellman-ford": 800,
    "floyd-warshall": 250,
}
MAX_BENCH_EDGES = 200_000
MAX_BENCH_SIZES = 12

# ---- Visualisation payload limits --------------------------------------------
MAX_STEPS = 3_000                 # recorded steps returned to the browser
VIZ_MATRIX_LIMIT = 60             # Floyd-Warshall step playback up to this many vertices
AVL_SNAPSHOT_LIMIT = 128          # tree snapshot after every insertion up to this size
AVL_TREE_RETURN_LIMIT = 255       # final tree returned for drawing up to this size
BINARY_ARRAY_RETURN_LIMIT = 256   # sorted array returned for drawing up to this size
