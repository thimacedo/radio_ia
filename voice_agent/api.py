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
    arquivo_clean: str # Legacy or cabeca_path
    cortes: Optional[Any] = [] # Can be list or dict
    cabeca_path: Optional[str] = None
    off_path: Optional[str] = None
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


def _background_assemble_multipart(job_id: str, program: str, cabeca_path: str, cabeca_cuts: List[Dict], off_path: str, off_cuts: List[Dict]):
    _update_job(job_id, {"status": "running", "started_at": time.time()})
    try:
        from .runner import approve_and_mount_multipart
        final_path = approve_and_mount_multipart(program, cabeca_path, cabeca_cuts, off_path, off_cuts, job_id=job_id)
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

    res = process_file(input_path, auto_approve=payload.auto_approve, job_id=payload.job_id)
    
    if res.get("status") == "multi_jobs":
        for result in res["jobs"]:
            job_id = result.get("job_id")
            _update_job(job_id, {
                "status": result.get("status"),
                "program": payload.program,
                "bulletin_id": result.get("bulletin_id"),
                "input_path": input_path,
                "clean_path": result.get("clean_path"),
                "cabeca_path": result.get("cabeca_path"),
                "off_path": result.get("off_path"),
                "report": result.get("report"),
                "issues": result.get("issues", []),
                "job_id": job_id,
                "created_at": time.time(),
            })

            if result.get("status") == "awaiting_approval":
                send_ntfy(f"radio_tjrn_{payload.program}", f"Aguardando aprovação: {result.get('report')}")
        return res
    else:
        # Fallback para o comportamento antigo, caso ocorra
        job_id = res.get("job_id") or str(uuid.uuid4())
        res["job_id"] = job_id
        _update_job(job_id, {
            "status": res.get("status"),
            "program": payload.program,
            "input_path": input_path,
            "clean_path": res.get("clean_path"),
            "report": res.get("report"),
            "issues": res.get("issues", []),
            "job_id": job_id,
            "created_at": time.time(),
        })

        if res.get("status") == "awaiting_approval":
            send_ntfy(f"radio_tjrn_{payload.program}", f"Aguardando aprovação: {res.get('report')}")

        return res


@app.post("/voice/approve")
def voice_approve(payload: ApprovePayload):
    cabeca_path = payload.cabeca_path or payload.arquivo_clean
    if cabeca_path:
        cabeca_path = os.path.expanduser(cabeca_path)
    
    off_path = payload.off_path
    if off_path:
        off_path = os.path.expanduser(off_path)
        
    job_id = payload.job_id or str(uuid.uuid4())
    
    cabeca_cuts = []
    off_cuts = []
    if isinstance(payload.cortes, dict):
        cabeca_cuts = payload.cortes.get("cabeca_cuts", [])
        off_cuts = payload.cortes.get("off_cuts", [])
    elif isinstance(payload.cortes, list):
        cabeca_cuts = payload.cortes
        
    _update_job(job_id, {
        "status": "accepted",
        "program": payload.program,
        "arquivo_clean": cabeca_path,
        "cabeca_path": cabeca_path,
        "off_path": off_path,
        "cabeca_cuts": cabeca_cuts,
        "off_cuts": off_cuts,
        "created_at": time.time(),
    })
    
    thread = Thread(target=_background_assemble_multipart, args=(job_id, payload.program, cabeca_path, cabeca_cuts, off_path or "", off_cuts), daemon=True)
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


@app.get("/health")
def health():
    return {"status": "ok", "jobs": len(jobs)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
