"""Orquestrador do Voice Edit Agent.

Fluxo: process_file(path) chama módulos:
  audio_processor.process_audio -> transcriber.transcribe -> error_detector.detect_issues
  report_generator.generate_report -> notifier.send_ntfy -> assembler.assemble

Este runner é um orquestrador síncrono simples para POC.
"""

from pathlib import Path
import json
import uuid
import datetime
from typing import List, Dict, Optional

from . import audio_processor, transcriber, error_detector, report_generator, notifier, assembler, splitter

def infer_program_from_path(p: Path) -> str:
    # espera inputs/{programa}/file
    parts = p.parts
    if "inputs" in parts:
        idx = parts.index("inputs")
        if len(parts) > idx + 1:
            return parts[idx + 1]
    return "default"


def process_file(input_path: str, auto_approve: bool = True, job_id: str = None) -> Dict:
    p = Path(input_path)
    if not p.exists():
        raise FileNotFoundError(input_path)

    program = infer_program_from_path(p)
    job_id = job_id or str(uuid.uuid4())
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")

    processed_dir = Path("processed") / program
    processed_dir.mkdir(parents=True, exist_ok=True)
    clean_name = f"{p.stem}_clean.wav"
    clean_path = str(processed_dir / clean_name)

    print(f"[runner] convertendo e limpando áudio: {p} -> {clean_path}")
    try:
        from .program_config import get_voice_edit_config
        config = get_voice_edit_config(program)
    except Exception:
        config = {}
    audio_processor.process_audio(str(p), clean_path, config)

    print("[runner] transcrevendo...")
    segments = transcriber.transcribe(clean_path)

    print("[runner] executando fatiador (auto-splitter)...")
    boletins_dir = str(processed_dir / "boletins")
    fractions = splitter.split_audio(clean_path, segments, boletins_dir, original_input_path=str(p))

    results = []

    if not fractions:
        # Fallback para processamento único (sem claquetes)
        fractions = [{
            "id": "UNICO",
            "cabeca_path": clean_path,
            "off_path": None,
            "cabeca_words": [],
            "off_words": []
        }]
        
        # Populate words for single file fallback
        all_words = []
        for s in segments:
            all_words.extend(s.get("words", []))
        fractions[0]["cabeca_words"] = all_words

    for fraction in fractions:
        b_id = fraction["id"]
        b_job_id = f"{job_id}_{b_id}" if job_id else str(uuid.uuid4())
        
        print(f"[runner] processando fração {b_id}...")
        
        # Detect issues on CABEÇA
        cabeca_segments = [{"words": fraction["cabeca_words"]}]
        cabeca_issues = error_detector.detect_issues(cabeca_segments, config=None)
        for issue in cabeca_issues:
            issue["part"] = "cabeca"
        
        # Detect issues on OFF
        off_segments = [{"words": fraction["off_words"]}] if fraction["off_words"] else []
        off_issues = error_detector.detect_issues(off_segments, config=None)
        for issue in off_issues:
            issue["part"] = "off"
        
        all_issues = cabeca_issues + off_issues

        # Extrai os cortes sugeridos
        cabeca_cuts = []
        for issue in cabeca_issues:
            if "suggested_cut" in issue:
                cabeca_cuts.append({
                    "start_ms": int(issue["suggested_cut"]["start"] * 1000),
                    "end_ms": int(issue["suggested_cut"]["end"] * 1000)
                })
                
        off_cuts = []
        for issue in off_issues:
            if "suggested_cut" in issue:
                off_cuts.append({
                    "start_ms": int(issue["suggested_cut"]["start"] * 1000),
                    "end_ms": int(issue["suggested_cut"]["end"] * 1000)
                })

        report_dir = Path("reports") / program
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = str(report_dir / f"{ts}_{p.stem}_{b_id}_report.html")
        print(f"[runner] gerando relatório: {report_path}")
        report_generator.generate_report_multipart(
            f"{program}_{b_id}", 
            fraction["cabeca_path"], 
            fraction["off_path"], 
            all_issues, 
            cabeca_cuts,
            off_cuts,
            report_path
        )

        topic = f"radio_tjrn_{program}"
        notifier.send_ntfy(topic, f"Relatório pronto: {report_path}")

        if not auto_approve and all_issues:
            print(f"[runner] {b_id} aguarda aprovação manual")
            results.append({
                "status": "awaiting_approval",
                "job_id": b_job_id,
                "bulletin_id": b_id,
                "program": program,
                "input_path": str(p),
                "clean_path": fraction["cabeca_path"], # Main editable path
                "cabeca_path": fraction["cabeca_path"],
                "off_path": fraction["off_path"],
                "report": report_path,
                "issues": all_issues,
            })
            continue

        outputs_dir = Path("outputs") / program
        outputs_dir.mkdir(parents=True, exist_ok=True)
        final_name = f"{ts}_{program}_{b_id}_final.mp3"
        final_path = str(outputs_dir / final_name)

        print(f"[runner] montando final {b_id}: {final_path}")
        
        # New signature for multi-part assembly
        assembler.assemble_multipart(program, fraction["cabeca_path"], cabeca_cuts, fraction["off_path"], off_cuts, final_path)

        notifier.send_ntfy(topic, f"Programa finalizado: {final_path}")

        results.append({
            "status": "completed",
            "job_id": b_job_id,
            "bulletin_id": b_id,
            "program": program,
            "input_path": str(p),
            "clean_path": fraction["cabeca_path"],
            "cabeca_path": fraction["cabeca_path"],
            "off_path": fraction["off_path"],
            "final_path": final_path,
            "report": report_path,
        })

    return {"status": "multi_jobs", "jobs": results}


def approve_and_mount(program: str, clean_path: str, cuts: List[Dict], job_id: str = None) -> str:
    """Executa montagem final a partir do arquivo limpo único."""
    outputs_dir = Path("outputs") / program
    outputs_dir.mkdir(parents=True, exist_ok=True)
    final_name = f"{Path(clean_path).stem}_approved_final.mp3"
    final_path = str(outputs_dir / final_name)
    assembler.assemble(program, clean_path, cuts, final_path)
    return final_path


def approve_and_mount_multipart(program: str, cabeca_path: str, cabeca_cuts: List[Dict], off_path: Optional[str], off_cuts: List[Dict], job_id: str = None) -> str:
    """Executa montagem final a partir das frações aprovadas."""
    outputs_dir = Path("outputs") / program
    outputs_dir.mkdir(parents=True, exist_ok=True)
    final_name = f"{Path(cabeca_path).stem}_approved_final.mp3"
    final_path = str(outputs_dir / final_name)
    assembler.assemble_multipart(program, cabeca_path, cabeca_cuts, off_path, off_cuts, final_path)
    return final_path


def main_cli():
    import sys
    if len(sys.argv) < 2:
        print("Uso: python -m voice_agent.runner <arquivo_de_audio>")
        return
    path = sys.argv[1]
    res = process_file(path)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main_cli()
