import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", str(BASE_DIR / "storage"))).resolve()
UPLOAD_DIR = STORAGE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://skillbridge:skillbridge_dev_only@localhost:5432/skillbridge",
)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
CORS_ORIGINS = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8081").split(",") if x.strip()]
