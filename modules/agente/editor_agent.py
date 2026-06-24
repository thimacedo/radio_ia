from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
import base64
import datetime

try:
    from core.voice_queue import VoiceQueue
except Exception:
    VoiceQueue = None

app = FastAPI(title="Editor Agent (stub)")

jobs: Dict[str, Dict[str, Any]] = {}


class JobCreate(BaseModel):
    job_id: Optional[str]
    program_id: str
    source: Dict[str, Any]
    parse_mode: Optional[str] = "auto"
    provided_blocks: Optional[List[List[Any]]] = None
    voice_strategy: Optional[Dict[str, Any]] = None
    assembly_profile: Optional[str] = None
    preferred_voice: Optional[str] = None
    priority: Optional[int] = 50
    callback_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PreviewRequest(BaseModel):
    segment_text: str
    voice: Optional[str] = None
    rate: Optional[str] = None


class ResolveConflictRequest(BaseModel):
    context: str
    candidates: List[Dict[str, Any]]


class EditApproveRequest(BaseModel):
    job_id: Optional[str]
    text: str
    instructions: Optional[str] = None
    target_format: Optional[str] = "audio_as_text"


class StatusCallback(BaseModel):
    event: str
    job_id: str
    percent: Optional[int]
    message: Optional[str]
    outputs: Optional[Dict[str, Any]]


@app.post("/jobs/create")
def create_job(payload: JobCreate):
    job_id = payload.job_id or str(uuid.uuid4())
    now = datetime.datetime.utcnow().isoformat()
    jobs[job_id] = {
        "created_at": now,
        "status": "accepted",
        "payload": payload.dict(),
    }
    return {"job_id": job_id, "status": "accepted"}


@app.post("/jobs/{job_id}/preview")
def preview(job_id: str, req: PreviewRequest):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="job not found")
    # Stub: return a tiny base64 placeholder instead of real TTS
    sample = f"preview:{req.segment_text[:64]}"
    b64 = base64.b64encode(sample.encode()).decode()
    return {"job_id": job_id, "preview_base64": b64, "note": "stub preview"}


@app.post("/editor/resolve_conflict")
def resolve_conflict(req: ResolveConflictRequest):
    # Na stub, devolvemos mapping identity por sheet_row (se existir)
    resolution = {}
    for cand in req.candidates:
        row = cand.get("sheet_row") or cand.get("row")
        if row is not None:
            resolution[str(row)] = f"assigned_{row}"
    return {"resolution": resolution}


@app.post("/editor/edit_and_approve")
def edit_and_approve(req: EditApproveRequest):
    # Minimal editor: echo do texto e split em blocos por linhas
    lines = [l.strip() for l in req.text.splitlines() if l.strip()]
    blocks = []
    for ln in lines:
        blocks.append(["LOC", ln])
    suggested_voice = "pt-BR-FranciscaNeural"
    return {
        "job_id": req.job_id,
        "approved_text": req.text,
        "parse_blocks": blocks,
        "suggested_voice": suggested_voice,
    }


@app.get("/voice/next")
def voice_next():
    if VoiceQueue is None:
        return {"voice": "pt-BR-FranciscaNeural", "note": "VoiceQueue not available in stub"}
    try:
        v = VoiceQueue().next_voice()
        return {"voice": v}
    except Exception as e:
        return {"voice": "pt-BR-FranciscaNeural", "error": str(e)}


@app.post("/jobs/{job_id}/status_callback")
def job_status_callback(job_id: str, cb: StatusCallback):
    if job_id not in jobs:
        jobs[job_id] = {"created_at": datetime.datetime.utcnow().isoformat()}
    jobs[job_id]["last_status"] = cb.dict()
    jobs[job_id]["status"] = cb.event
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
