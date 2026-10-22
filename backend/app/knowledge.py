"""Simple persisted embedding index. Embeddings are created locally, indexed with FAISS."""
from functools import lru_cache
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from .config import EMBEDDING_MODEL
from .models import KnowledgeChunk, Source

@lru_cache(maxsize=1)
def get_embedder():
    return SentenceTransformer(EMBEDDING_MODEL)

class KnowledgeIndex:
    def __init__(self):
        self.index = None
        self.chunk_ids: list[int] = []

    def rebuild(self, db: Session):
        rows = db.query(KnowledgeChunk).filter(KnowledgeChunk.embedding_json != "[]").all()
        valid = []
        ids = []
        for row in rows:
            try:
                vector = json.loads(row.embedding_json)
                if vector: valid.append(vector); ids.append(row.id)
            except Exception: pass
        if not valid:
            self.index, self.chunk_ids = None, []
            return
        matrix = np.asarray(valid, dtype="float32")
        faiss.normalize_L2(matrix)
        self.index = faiss.IndexFlatIP(matrix.shape[1])
        self.index.add(matrix)
        self.chunk_ids = ids

    def add_chunks(self, db: Session, rows: list[KnowledgeChunk]):
        if not rows: return
        texts = [row.text for row in rows]
        vectors = get_embedder().encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        for row, vector in zip(rows, vectors):
            row.embedding_json = json.dumps(vector.astype(float).tolist())
        db.commit()
        self.rebuild(db)

    def search(self, db: Session, query: str, top_k: int = 5, source_type: str | None = None):
        # Keep results grounded: vector search finds candidate chunks; filter source type when needed.
        if source_type:
            candidates = db.query(KnowledgeChunk).join(
                Source, KnowledgeChunk.source_id == Source.id
            ).filter(Source.source_type == source_type).all()
            rows = candidates
            if not rows: return []
            matrix = np.asarray([json.loads(r.embedding_json) for r in rows], dtype="float32")
            qv = get_embedder().encode([query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
            scores = matrix @ qv[0]
            return [rows[i] for i in np.argsort(scores)[::-1][:top_k]]
        if self.index is None or not self.chunk_ids:
            self.rebuild(db)
        if self.index is None: return []
        qv = get_embedder().encode([query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
        scores, positions = self.index.search(qv, min(top_k, len(self.chunk_ids)))
        ids = [self.chunk_ids[p] for p in positions[0] if p >= 0]
        if not ids: return []
        found = db.query(KnowledgeChunk).filter(KnowledgeChunk.id.in_(ids)).all()
        by_id = {r.id:r for r in found}
        return [by_id[i] for i in ids if i in by_id]

knowledge_index = KnowledgeIndex()
