"""core.py — shared brain: chromadb concepts, file helpers, dynamic tool loader."""

import importlib.util
import inspect
import uuid
from pathlib import Path
import chromadb

# ── workspace files ────────────────────────────────────────────────────────────
WORKSPACE = Path(__file__).parent / "workspace"
WORKSPACE.mkdir(exist_ok=True)

GOAL_FILE   = WORKSPACE / "GOAL.md"
PLAN_FILE   = WORKSPACE / "PLAN.md"
REPORT_FILE = WORKSPACE / "REPORT.md"

# ── chromadb concepts ──────────────────────────────────────────────────────────
_chroma = chromadb.Client()
concepts = _chroma.get_or_create_collection("concepts")

def concept_add(text: str) -> str:
    """Add a new piece of knowledge/finding to the concepts store."""
    concepts.add(ids=[str(uuid.uuid4())], documents=[text])
    return "added"

def concept_search(query: str) -> str:
    """Search concepts store for relevant knowledge. Returns top 4 results."""
    count = concepts.count()
    if count == 0:
        return "concepts store is empty"
    results = concepts.query(query_texts=[query], n_results=min(4, count))
    docs = results.get("documents", [[]])[0]
    if not docs:
        return "nothing relevant found"
    return "\n\n---\n\n".join(docs)

# ── file helpers ───────────────────────────────────────────────────────────────
def read_goal() -> str:
    """Read GOAL.md"""
    return GOAL_FILE.read_text() if GOAL_FILE.exists() else ""

def read_plan() -> str:
    """Read PLAN.md"""
    return PLAN_FILE.read_text() if PLAN_FILE.exists() else ""

def write_plan(content: str) -> str:
    """Write/overwrite PLAN.md"""
    PLAN_FILE.write_text(content)
    return "plan written"

def update_goal_background(background: str) -> str:
    """Append background section to GOAL.md (soul agent fills this)."""
    current = GOAL_FILE.read_text() if GOAL_FILE.exists() else ""
    if "## Background" not in current:
        GOAL_FILE.write_text(current.strip() + f"\n\n## Background\n{background}\n")
    return "background added to GOAL.md"

def report_append(text: str) -> str:
    """Append text to REPORT.md (the living output document)."""
    with open(REPORT_FILE, "a") as f:
        f.write(text + "\n")
    return "appended to report"

def report_read() -> str:
    """Read current REPORT.md"""
    return REPORT_FILE.read_text() if REPORT_FILE.exists() else ""

# ── dynamic tool loader ────────────────────────────────────────────────────────
TOOLS_DIR = Path(__file__).parent / "tools"
_loaded: dict[str, list] = {}

def load_tools(prefix: str) -> str:
    """Load all tools from tools/<prefix>_*.py or tools/<prefix>.py. Returns list of tool names loaded."""
    if prefix in _loaded:
        return f"already loaded: {[f.__name__ for f in _loaded[prefix]]}"

    fns = []
    for path in sorted(TOOLS_DIR.glob("*.py")):
        if path.stem.startswith(prefix) or path.stem == prefix:
            spec = importlib.util.spec_from_file_location(path.stem, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for name, obj in inspect.getmembers(mod, inspect.isfunction):
                if not name.startswith("_"):
                    fns.append(obj)

    _loaded[prefix] = fns
    names = [f.__name__ for f in fns]
    return f"loaded {len(fns)} tools: {names}"

def get_loaded_tools() -> list:
    """Return all currently loaded tool functions (flat list)."""
    all_fns = []
    for fns in _loaded.values():
        all_fns.extend(fns)
    return all_fns
