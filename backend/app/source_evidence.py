"""Database-scoped evidence retrieval for source-to-SOP drafting."""
from .models import KnowledgeChunk


def load_source_excerpts(db, source_id: int, limit: int = 30) -> list[dict]:
    chunks = (db.query(KnowledgeChunk)
              .filter(KnowledgeChunk.source_id == source_id)
              .order_by(KnowledgeChunk.id.asc())
              .limit(limit)
              .all())
    return [{
        "text": chunk.text,
        "source_ref": chunk.source_ref,
        "timestamp": f"{chunk.start_seconds // 60:02d}:{chunk.start_seconds % 60:02d}" if chunk.start_seconds is not None else None,
        "source_id": chunk.source_id,
    } for chunk in chunks]
