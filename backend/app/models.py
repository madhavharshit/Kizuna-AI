from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def now_utc(): return datetime.now(timezone.utc)

class Source(Base):
    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_type: Mapped[str] = mapped_column(String(20), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(600))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    source_ref: Mapped[str] = mapped_column(String(500), default="")
    start_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding_json: Mapped[str] = mapped_column(Text, default="[]")

class Procedure(Base):
    __tablename__ = "procedures"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    tools_json: Mapped[str] = mapped_column(Text, default="[]")
    warnings_json: Mapped[str] = mapped_column(Text, default="[]")
    steps_json: Mapped[str] = mapped_column(Text, default="[]")
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    rejection_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

class TrainingProgress(Base):
    __tablename__ = "training_progress"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    procedure_id: Mapped[int] = mapped_column(ForeignKey("procedures.id", ondelete="CASCADE"), index=True)
    trainee_name: Mapped[str] = mapped_column(String(120), default="Demo Trainee")
    completed_steps: Mapped[int] = mapped_column(Integer, default=0)
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    quiz_score: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
