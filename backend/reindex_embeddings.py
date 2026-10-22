from pathlib import Path
from dotenv import load_dotenv
import json

# Load the backend settings before loading the embedding model.
load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

from app.db import SessionLocal
from app.models import KnowledgeChunk
from app.knowledge import get_embedder, knowledge_index


def main():
    with SessionLocal() as db:
        rows = (
            db.query(KnowledgeChunk)
            .order_by(KnowledgeChunk.id)
            .all()
        )

        if not rows:
            print("No knowledge chunks found. Upload a PDF or video first.")
            return

        print(f"Rebuilding embeddings for {len(rows)} chunks...")
        model = get_embedder()

        batch_size = 16

        for start in range(0, len(rows), batch_size):
            batch = rows[start:start + batch_size]

            vectors = model.encode(
                [row.text for row in batch],
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )

            for row, vector in zip(batch, vectors):
                row.embedding_json = json.dumps(
                    vector.astype(float).tolist()
                )

            db.commit()
            print(
                f"Processed {min(start + batch_size, len(rows))}"
                f" / {len(rows)} chunks"
            )

        # Rebuild the in-memory FAISS index from the new vectors.
        knowledge_index.rebuild(db)

        print("Done. All existing chunks now use the multilingual model.")


if __name__ == "__main__":
    main()