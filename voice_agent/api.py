from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from threading import Thread, Lock
import uuid
import time
import os

from .runner import approve_and_mount
from .notifier import send_ntfy

app = FastAPI(title="Voice Edit Agent API")

jobs: Dict[str, Dict[str, Any]] = {}
jobs_lock = Lock()


class ApprovePayload(BaseModel):
    program: str
    arquivo_clean: str
    cortes: Optional[List[Dict[str, Any]]] = []
    job_id: Optional[str] = None


class RejectPayload(BaseModel):
    program: str
    arquivo_clean: str
    motivo: Optional[str] = None
    job_id: Optional[str] = None


def _update_job(job_id: str, data: Dict[str, Any]):
    with jobs_lock:
        if job_id not in jobs:
            jobs[job_id] = {}
        jobs[job_id].update(data)


def _background_assemble(job_id: str, program: str, clean_path: str, cortes: List[Dict[str, Any]]):
    _update_job(job_id, {"status": "running", "started_at": time.time()})
    try:
        final_path = approve_and_mount(program, clean_path, cortes, job_id=job_id)
        _update_job(job_id, {
            "status": "completed",
            "final_path": final_path,
            "completed_at": time.time()
        })
        send_ntfy(f"radio_tjrn_{program}", f"Montagem concluída: {final_path}")
    except Exception as e:
        _update_job(job_id, {"status": "failed", "error": str(e), "completed_at": time.time()})
        send_ntfy(f"radio_tjrn_{program}", f"Falha na montagem: {e}")


@app.post("/voice/approve")
def voice_approve(payload: ApprovePayload):
    clean_path = os.path.expanduser(payload.arquivo_clean)
    if not os.path.isfile(clean_path):
        raise HTTPException(status_code=404, detail=f"Arquivo clean não encontrado: {clean_path}")
    job_id = payload.job_id or str(uuid.uuid4())
    with jobs_lock:
        jobs[job_id] = {
            "status": "accepted",
            "program": payload.program,
            "arquivo_clean": clean_path,
            "cortes": payload.cortes,
            "created_at": time.time(),
        }
    thread = Thread(target=_background_assemble, args=(job_id, payload.program, clean_path, payload.cortes or []), daemon=True)
    thread.start()
    return {"job_id": job_id, "status": "accepted"}


@app.get("/voice/status/{job_id}")
def voice_status(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return job


@app.post("/voice/reject")
def voice_reject(payload: RejectPayload):
    job_id = payload.job_id or str(uuid.uuid4())
    with jobs_lock:
        jobs[job_id] = {
            "status": "rejected",
            "program": payload.program,
            "arquivo_clean": payload.arquivo_clean,
            "motivo": payload.motivo,
            "created_at": time.time(),
        }
    return {"job_id": job_id, "status": "rejected"}


@app.get("/health")
def health():
    return {"status": "ok", "jobs": len(jobs)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
