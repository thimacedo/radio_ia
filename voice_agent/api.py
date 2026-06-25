from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from threading import Thread, Lock
import uuid
import time
import os

from .runner import process_file, approve_and_mount
from .notifier import send_ntfy

app = FastAPI(title="Voice Edit Agent API")

jobs: Dict[str, Dict[str, Any]] = {}
jobs_lock = Lock()


class ProcessPayload(BaseModel):
    program: str
    input_path: str
    auto_approve: Optional[bool] = False
    job_id: Optional[str] = None


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
        jobs[job_id]["updated_at"] = time.time()


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


@app.post("/voice/process")
def voice_process(payload: ProcessPayload):
    input_path = os.path.expanduser(payload.input_path)
    if not os.path.isfile(input_path):
        raise HTTPException(status_code=404, detail=f"Arquivo de entrada não encontrado: {input_path}")

    result = process_file(input_path, auto_approve=payload.auto_approve, job_id=payload.job_id)
    job_id = result.get("job_id") or str(uuid.uuid4())
    result["job_id"] = job_id
    _update_job(job_id, {
        "status": result.get("status"),
        "program": payload.program,
        "input_path": input_path,
        "clean_path": result.get("clean_path"),
        "report": result.get("report"),
        "issues": result.get("issues", []),
        "job_id": job_id,
        "created_at": time.time(),
    })

    if result.get("status") == "awaiting_approval":
        send_ntfy(f"radio_tjrn_{payload.program}", f"Aguardando aprovação: {result.get('report')}")

    return result


@app.post("/voice/approve")
def voice_approve(payload: ApprovePayload):
    clean_path = os.path.expanduser(payload.arquivo_clean)
    if not os.path.isfile(clean_path):
        raise HTTPException(status_code=404, detail=f"Arquivo clean não encontrado: {clean_path}")
    job_id = payload.job_id or str(uuid.uuid4())
    _update_job(job_id, {
        "status": "accepted",
        "program": payload.program,
        "arquivo_clean": clean_path,
        "cortes": payload.cortes,
        "created_at": time.time(),
    })
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
    _update_job(job_id, {
        "status": "rejected",
        "program": payload.program,
        "arquivo_clean": payload.arquivo_clean,
        "motivo": payload.motivo,
        "created_at": time.time(),
    })
    send_ntfy(f"radio_tjrn_{payload.program}", f"Áudio rejeitado: {payload.arquivo_clean}")
    return {"job_id": job_id, "status": "rejected"}


@app.get("/voice/jobs")
def voice_list_jobs():
    with jobs_lock:
        # Retorna uma cópia para evitar problemas de concorrência na serialização
        return dict(jobs)

@app.get("/health")
def health():
    return {"status": "ok", "jobs": len(jobs)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
