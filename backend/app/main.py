from pathlib import Path
from datetime import datetime, timezone
import json, shutil, re
from typing import Literal
from io import BytesIO

from numpy import info
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .db import Base, engine, get_db, SessionLocal
from .models import Source, KnowledgeChunk, Procedure, TrainingProgress
from .schemas import AskRequest, ProcedureUpdate, ReviewRequest, ProgressRequest
from .config import UPLOAD_DIR, CORS_ORIGINS, WHISPER_MODEL
from .knowledge import knowledge_index
from .ai import grounded_answer, draft_procedure

# Create tables at launch. The Postgres service must be running first.
Base.metadata.create_all(bind=engine)
app = FastAPI(title="SkillBridge AR API", version="0.1.0", description="Hackathon MVP: document RAG, video RAG, approved SOPs and training progress.")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120, separators=["\n\n", "\n", ". ", " ", ""])

@app.on_event("startup")
def load_index():
    with SessionLocal() as db: knowledge_index.rebuild(db)

def source_out(s): return {"id":s.id,"source_type":s.source_type,"filename":s.filename,"created_at":s.created_at.isoformat() if s.created_at else None}
def procedure_out(p):
    return {"id":p.id,"title":p.title,"description":p.description,"tools":json.loads(p.tools_json or "[]"),"warnings":json.loads(p.warnings_json or "[]"),"steps":json.loads(p.steps_json or "[]"),"source_id":p.source_id,"status":p.status,"rejection_note":p.rejection_note,"created_at":p.created_at.isoformat() if p.created_at else None,"updated_at":p.updated_at.isoformat() if p.updated_at else None}
def make_chunks(db, source, entries):
    rows=[]
    for item in entries:
        row=KnowledgeChunk(source_id=source.id,text=item["text"],source_ref=item["source_ref"],start_seconds=item.get("start_seconds"),end_seconds=item.get("end_seconds"),embedding_json="[]")
        db.add(row); rows.append(row)
    db.commit()
    for row in rows: db.refresh(row)
    knowledge_index.add_chunks(db, rows)
    return len(rows)

@app.get("/api/health")
def health(): return {"status":"ok","service":"SkillBridge AR API"}

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile=File(...), db: Session=Depends(get_db)):
    filename = Path(file.filename or "manual.pdf").name
    if not filename.lower().endswith(".pdf"): raise HTTPException(400,"Please upload a PDF manual or SOP.")
    data = await file.read()
    if len(data) > 30*1024*1024: raise HTTPException(413,"MVP upload limit is 30 MB.")
    path=UPLOAD_DIR / f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{filename}"; path.write_bytes(data)
    try: reader=PdfReader(BytesIO(data))
    except Exception as e: path.unlink(missing_ok=True); raise HTTPException(400,f"Unable to read PDF: {e}")
    entries=[]
    for page_no, page in enumerate(reader.pages, start=1):
        text = re.sub(
            r"\s+",
            " ",
            (page.extract_text() or "")
        ).strip()
        if not text: continue
        for idx, chunk in enumerate(splitter.split_text(text)):
            entries.append({"text":chunk,"source_ref":f"{filename} · page {page_no}"})
    if not entries: path.unlink(missing_ok=True); raise HTTPException(400,"No extractable text found. This PDF may be scanned; use an OCR/text-readable PDF for this demo.")
    source=Source(source_type="document",filename=filename,file_path=str(path)); db.add(source); db.commit(); db.refresh(source)
    count=make_chunks(db, source, entries)
    return {"source":source_out(source),"chunks_created":count,"message":"Document processed and indexed."}

@app.post("/api/videos/upload")
async def upload_video(file: UploadFile=File(...), db: Session=Depends(get_db)):
    filename=Path(file.filename or "expert-demo.mp4").name
    if Path(filename).suffix.lower() not in {".mp4",".mov",".m4v",".webm",".mkv",".mp3",".wav",".m4a"}: raise HTTPException(400,"Supported: mp4, mov, m4v, webm, mkv, mp3, wav, m4a.")
    data=await file.read()
    if len(data)>200*1024*1024: raise HTTPException(413,"MVP upload limit is 200 MB.")
    path=UPLOAD_DIR / f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{filename}"; path.write_bytes(data)
    try:
        from faster_whisper import WhisperModel
        model=WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        segments, info=model.transcribe(str(path), beam_size=1, vad_filter=True)
        detected_language = info.language
        language_probability = float(info.language_probability)
        transcription=[]
        for seg in segments:
            text=seg.text.strip()
            if text: transcription.append({"text":text,"source_ref":f"{filename} · {int(seg.start//60):02d}:{int(seg.start%60):02d}","start_seconds":int(seg.start),"end_seconds":int(seg.end)})
        if not transcription: raise RuntimeError("No speech detected in the video/audio file.")
    except Exception as e:
        path.unlink(missing_ok=True)
        raise HTTPException(500,f"Transcription failed: {e}. Check that the file has audible speech and retry with a shorter clip.")
    source=Source(source_type="video",filename=filename,file_path=str(path)); db.add(source); db.commit(); db.refresh(source)
    count=make_chunks(db, source, transcription)
    return {"source":source_out(source),"chunks_created":count,"transcript":transcription,"message":"Audio transcribed and timestamped."}

@app.get("/api/sources")
def list_sources(db: Session=Depends(get_db)):
    return [source_out(s) for s in db.query(Source).order_by(Source.created_at.desc()).all()]

@app.post("/api/ask")
def ask(body: AskRequest, db: Session=Depends(get_db)):
    found=knowledge_index.search(db,body.question,top_k=5,source_type=body.source_type)
    sources=[]
    from .models import Source as SourceModel
    for ch in found:
        src=db.get(SourceModel,ch.source_id)
        sources.append({"chunk_id":ch.id,"source_id":ch.source_id,"filename":src.filename if src else "Unknown source","source_type":src.source_type if src else "unknown","reference":ch.source_ref,"timestamp_start":ch.start_seconds,"timestamp_end":ch.end_seconds,"excerpt":ch.text[:700]})
    result = grounded_answer(
    body.question,
    found,
    sources,
    response_language=body.response_language,
    )
    return result

@app.post("/api/procedures/draft/{source_id}")
def create_draft(
    source_id: int,
    language: Literal["en", "ja"] = "en",
    db: Session = Depends(get_db),
):
    source=db.get(Source,source_id)
    if not source: raise HTTPException(404,"Source not found.")
    chunks=db.query(KnowledgeChunk).filter(KnowledgeChunk.source_id==source_id).order_by(KnowledgeChunk.id.asc()).limit(30).all()
    if not chunks: raise HTTPException(400,"No indexed source text is available.")
    excerpts=[{"text":c.text,"source_ref":c.source_ref,"timestamp":f"{c.start_seconds//60:02d}:{c.start_seconds%60:02d}" if c.start_seconds is not None else None} for c in chunks]
    data = draft_procedure(
    source.filename,
    excerpts,
    output_language=language,
    )
    p=Procedure(title=data.get("title",f"Draft — {source.filename}"),description=data.get("description","AI draft; expert review required."),tools_json=json.dumps(data.get("tools",[])),warnings_json=json.dumps(data.get("warnings",[])),steps_json=json.dumps(data.get("steps",[])),source_id=source.id,status="draft")
    db.add(p); db.commit(); db.refresh(p)
    return procedure_out(p)

@app.get("/api/procedures")
def list_procedures(status:str|None=None, db: Session=Depends(get_db)):
    q=db.query(Procedure)
    if status: q=q.filter(Procedure.status==status)
    return [procedure_out(p) for p in q.order_by(Procedure.updated_at.desc()).all()]

@app.get("/api/procedures/{procedure_id}")
def get_procedure(procedure_id:int, db: Session=Depends(get_db)):
    p=db.get(Procedure,procedure_id)
    if not p: raise HTTPException(404,"Procedure not found.")
    return procedure_out(p)

@app.put("/api/procedures/{procedure_id}")
def update_procedure(procedure_id:int, body:ProcedureUpdate, db: Session=Depends(get_db)):
    p=db.get(Procedure,procedure_id)
    if not p: raise HTTPException(404,"Procedure not found.")
    if p.status=="approved": p.status="draft" # changing an approved SOP forces a new review
    p.title=body.title; p.description=body.description; p.tools_json=json.dumps(body.tools); p.warnings_json=json.dumps(body.warnings); p.steps_json=json.dumps([s.model_dump() for s in body.steps]); p.updated_at=datetime.now(timezone.utc)
    db.commit(); db.refresh(p)
    return procedure_out(p)

@app.post("/api/procedures/{procedure_id}/review")
def review_procedure(procedure_id:int, body:ReviewRequest, db: Session=Depends(get_db)):
    p=db.get(Procedure,procedure_id)
    if not p: raise HTTPException(404,"Procedure not found.")
    action=body.action.lower().strip()
    if action not in {"approve","reject"}: raise HTTPException(400,"action must be approve or reject")
    p.status="approved" if action=="approve" else "rejected"; p.rejection_note=body.note if action=="reject" else ""; p.updated_at=datetime.now(timezone.utc)
    db.commit(); db.refresh(p)
    return procedure_out(p)

@app.get("/api/training/procedures")
def published_procedures(db: Session=Depends(get_db)):
    return [procedure_out(p) for p in db.query(Procedure).filter(Procedure.status=="approved").order_by(Procedure.updated_at.desc()).all()]

@app.post("/api/training/progress")
def save_progress(body:ProgressRequest, db:Session=Depends(get_db)):
    p=db.get(Procedure,body.procedure_id)
    if not p or p.status!="approved": raise HTTPException(404,"Approved procedure not found.")
    row=TrainingProgress(procedure_id=p.id,trainee_name=body.trainee_name,completed_steps=body.completed_steps,total_steps=body.total_steps,quiz_score=body.quiz_score,completed=body.completed)
    db.add(row); db.commit(); db.refresh(row)
    return {"id":row.id,"procedure_id":row.procedure_id,"trainee_name":row.trainee_name,"completed_steps":row.completed_steps,"total_steps":row.total_steps,"quiz_score":row.quiz_score,"completed":row.completed}

@app.get("/api/training/progress")
def get_progress(db:Session=Depends(get_db)):
    rows=db.query(TrainingProgress).order_by(TrainingProgress.created_at.desc()).limit(100).all()
    return [{"id":r.id,"procedure_id":r.procedure_id,"trainee_name":r.trainee_name,"completed_steps":r.completed_steps,"total_steps":r.total_steps,"quiz_score":r.quiz_score,"completed":r.completed,"created_at":r.created_at.isoformat() if r.created_at else None} for r in rows]
