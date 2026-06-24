"""Detecta issues na transcrição: repetições, hesitações, silêncios.

API principal: detect_issues(segments, config) -> list[Issue]
Issue dict: {type, start, end, text, severity}
"""

from typing import List, Dict
from difflib import SequenceMatcher


def detect_issues(segments: List[Dict], config: Dict = None) -> List[Dict]:
    config = config or {}
    issues = []
    prev_text = None
    for seg in segments:
        text = seg.get("text", "").strip()
        # repetição simples (palavra duplicada)
        tokens = text.split()
        for i in range(len(tokens)-1):
            if tokens[i].lower() == tokens[i+1].lower():
                issues.append({
                    "type": "repeticao_palavra",
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": tokens[i],
                    "severity": "ATENCAO",
                })
                break
        # repetição de frase (similaridade com anterior)
        if prev_text is not None:
            ratio = SequenceMatcher(None, prev_text, text).ratio()
            if ratio > 0.85:
                issues.append({
                    "type": "repeticao_frase",
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": text,
                    "severity": "ATENCAO",
                })
        prev_text = text

    # silêncios e hesitações são calculados na camada de transcrição (ou por gaps)
    return issues


if __name__ == "__main__":
    # breve demo
    segs = [
        {"start":0.0, "end":1.2, "text":"o o contrato"},
        {"start":1.3, "end":2.4, "text":"o contrato"},
    ]
    print(detect_issues(segs))
