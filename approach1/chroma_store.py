"""
chroma_store.py — Shared ChromaDB collections for a DEW session.

Collections:
  urls      — every URL visited, content cached
  concepts  — broader topics explored (saturation check)
  ideas     — specific findings/facts discovered
"""

import chromadb

_client = chromadb.Client()

urls     = _client.get_or_create_collection("urls")
concepts = _client.get_or_create_collection("concepts")
ideas    = _client.get_or_create_collection("ideas")


def is_saturated(concept: str, threshold: float = 0.85) -> bool:
    """Return True if this concept has already been explored."""
    if concepts.count() == 0:
        return False
    results = concepts.query(query_texts=[concept], n_results=1)
    distances = results["distances"][0]
    if not distances:
        return False
    # chromadb distance: 0=identical, 2=opposite. Convert to similarity.
    similarity = 1 - (distances[0] / 2)
    return similarity >= threshold


def add_concept(concept: str, meta: dict = {}):
    import uuid
    concepts.add(ids=[str(uuid.uuid4())], documents=[concept], metadatas=[meta])


def add_idea(idea: str, meta: dict = {}):
    import uuid
    ideas.add(ids=[str(uuid.uuid4())], documents=[idea], metadatas=[meta])
