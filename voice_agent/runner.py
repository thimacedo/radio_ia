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
from typing import List, Dict

from . import audio_processor, transcriber, error_detector, report_generator, notifier, assembler


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
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")

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

    print("[runner] detectando issues...")
    issues = error_detector.detect_issues(segments, config=None)

    report_dir = Path("reports") / program
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = str(report_dir / f"{ts}_{p.stem}_report.html")
    print(f"[runner] gerando relatório: {report_path}")
    report_generator.generate_report(program, clean_path, segments, issues, report_path)

    topic = f"radio_tjrn_{program}"
    notifier.send_ntfy(topic, f"Relatório pronto: {report_path}")

    if not auto_approve and issues:
        print("[runner] aguarda aprovação manual — saindo")
        return {
            "status": "awaiting_approval",
            "job_id": job_id,
            "program": program,
            "input_path": str(p),
            "clean_path": clean_path,
            "report": report_path,
            "issues": issues,
        }

    # Auto-approve: realiza cortes sugeridos (por enquanto, nenhum corte automático)
    cuts: List[Dict] = []

    outputs_dir = Path("outputs") / program
    outputs_dir.mkdir(parents=True, exist_ok=True)
    final_name = f"{ts}_{program}_final.mp3"
    final_path = str(outputs_dir / final_name)

    print(f"[runner] montando final: {final_path}")
    assembler.assemble(program, clean_path, cuts, final_path)

    notifier.send_ntfy(topic, f"Programa finalizado: {final_path}")

    return {
        "status": "completed",
        "job_id": job_id,
        "program": program,
        "input_path": str(p),
        "clean_path": clean_path,
        "final_path": final_path,
        "report": report_path,
    }


def approve_and_mount(program: str, clean_path: str, cuts: List[Dict], job_id: str = None) -> str:
    """Executa montagem final a partir do arquivo clean aprovado."""
    outputs_dir = Path("outputs") / program
    outputs_dir.mkdir(parents=True, exist_ok=True)
    final_name = f"{Path(clean_path).stem}_approved_final.mp3"
    final_path = str(outputs_dir / final_name)
    assembler.assemble(program, clean_path, cuts, final_path)
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
