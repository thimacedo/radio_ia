"""Transcriber: wrapper para STT (Whisper local).

Funções principais:
- transcribe(file_path) -> List[Segment]

Segment = dict with keys: start (s), end (s), text, confidence
"""

from typing import List, Dict, Optional
from pathlib import Path

try:
    import whisper
except Exception:
    whisper = None


def transcribe(file_path: str, model_name: str = "medium", language: Optional[str] = "pt") -> List[Dict]:
    """Transcreve audio usando Whisper local quando disponível.

    Retorna lista de segmentos: {start, end, text, confidence}
    """
    file_p = Path(file_path)
    if not file_p.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    if whisper is None:
        # Fallback: retorno stub para permitir desenvolvimento sem instalação
        return [
            {"start": 0.0, "end": 3.2, "text": "Olá, este é um teste.", "confidence": 0.95},
        ]

    model = whisper.load_model(model_name)
    result = model.transcribe(str(file_p), language=language, word_timestamps=True, condition_on_previous_text=False)
    segments = []
    for s in result.get("segments", []):
        words = []
        for w in s.get("words", []):
            words.append({
                "start": float(w.get("start", 0.0)),
                "end": float(w.get("end", 0.0)),
                "text": w.get("word", "").strip(),
                "confidence": w.get("probability", None)
            })
            
        segments.append({
            "start": float(s.get("start", 0.0)),
            "end": float(s.get("end", 0.0)),
            "text": s.get("text", "").strip(),
            "confidence": s.get("avg_logprob", None),
            "words": words
        })
    return segments


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(transcribe(sys.argv[1]))
    else:
        print("Uso: python -m voice_agent.transcriber <arquivo>")
