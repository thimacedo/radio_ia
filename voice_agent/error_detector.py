"""Detecta issues na transcrição: repetições, hesitações, silêncios.

API principal: detect_issues(segments, config) -> list[Issue]
Issue dict: {type, start, end, text, severity}
"""

from typing import List, Dict
from difflib import SequenceMatcher

import re

def normalize_text(text):
    return re.sub(r'[^\w\s]', '', text.lower()).strip()

def detect_issues(segments: List[Dict], config: Dict = None) -> List[Dict]:
    config = config or {}
    issues = []
    
    # Extract all words sequentially
    all_words = []
    for seg in segments:
        words = seg.get("words", [])
        for w in words:
            all_words.append(w)
            
    if not all_words:
        return issues
        
    N = 3 # N-gram size for retake detection
    norm_words = [normalize_text(w["text"]) for w in all_words]
    
    # 1. Detect explicit markers
    markers = {"repete", "repetindo", "novamente", "denovo", "errei", "voltar"}
    
    i = 0
    while i < len(norm_words):
        if norm_words[i] in markers:
            # We found a marker. Let's look at the next N words to find the resumption point
            resume_ngram = norm_words[i+1:i+1+N]
            
            if len(resume_ngram) == N and not any(not w for w in resume_ngram):
                # Search backwards from the marker for this N-gram
                found_mistake_start = -1
                for j in range(i - N, -1, -1):
                    if norm_words[j:j+N] == resume_ngram:
                        found_mistake_start = j
                        break
                        
                if found_mistake_start != -1:
                    cut_start = all_words[found_mistake_start]["start"]
                    cut_end = all_words[i]["end"] # up to the end of the marker
                    
                    issues.append({
                        "type": "retake_explicito",
                        "start": cut_start,
                        "end": cut_end,
                        "text": " ".join([w["text"] for w in all_words[found_mistake_start:i+1]]),
                        "severity": "ALTO",
                        "suggested_cut": {
                            "start": cut_start,
                            "end": cut_end
                        }
                    })
                    # Skip past the marker
                    i += 1
                    continue
                    
        i += 1

    # 2. Heuristic N-gram repetition for implicit retakes (with pauses)
    i = 0
    while i <= len(norm_words) - N:
        ngram = norm_words[i:i+N]
        if any(not w for w in ngram):
            i += 1
            continue
            
        window_size = 20
        for j in range(i + 1, min(i + window_size, len(norm_words) - N + 1)):
            ahead_ngram = norm_words[j:j+N]
            if ngram == ahead_ngram:
                # To avoid false positives (like "o presidente da... o presidente da"), 
                # we require a significant pause (> 0.8s) or a single-word repeat
                pause_duration = all_words[j]["start"] - all_words[j-1]["end"]
                
                is_single_word = (j == i + 1 and ngram[0] == ahead_ngram[0])
                
                if is_single_word or pause_duration > 0.8:
                    cut_start = all_words[i]["start"]
                    cut_end = all_words[j]["start"]
                    
                    if is_single_word:
                        issues.append({
                            "type": "repeticao_palavra",
                            "start": cut_start,
                            "end": all_words[j]["end"],
                            "text": all_words[i]["text"],
                            "severity": "ATENCAO",
                            "suggested_cut": {
                                "start": cut_start,
                                "end": cut_end
                            }
                        })
                    else:
                        issues.append({
                            "type": "retake_implicito",
                            "start": cut_start,
                            "end": cut_end,
                            "text": " ".join([w["text"] for w in all_words[i:j]]),
                            "severity": "ALTO",
                            "suggested_cut": {
                                "start": cut_start,
                                "end": cut_end
                            }
                        })
                    
                    i = j + N - 1
                    break
        
        i += 1
        
    return issues


if __name__ == "__main__":
    # breve demo
    segs = [
        {"start":0.0, "end":1.2, "text":"o o contrato"},
        {"start":1.3, "end":2.4, "text":"o contrato"},
    ]
    print(detect_issues(segs))
