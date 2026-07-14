import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from difflib import SequenceMatcher

try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None

def normalize_word(word: str) -> str:
    # Lowercase and remove punctuation
    return re.sub(r'[^\w\s]', '', word.lower()).strip()

def detect_claquetes(segments: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    Identifies 'claquete' markers (e.g., 'b1', 'boletim 2') in the transcription
    and returns a list of cut points indicating where each bulletin starts.
    Returns: claquetes list, and all words sequentially.
    """
    all_words = []
    for s in segments:
        all_words.extend(s.get("words", []))
        
    claquetes = []
    i = 0
    while i < len(all_words):
        w = normalize_word(all_words[i].get("text", ""))
        
        # Match 'b1', 'd2', 'e3', 'p4', etc. due to phonetic confusion by Whisper
        if re.match(r"^[bcdeoptv]\d+$", w):
            claquetes.append({
                "id": w.upper().replace(w[0].upper(), 'B', 1), # Force it to be 'B'
                "start": all_words[i]["start"],
                "end": all_words[i]["end"],
                "word_idx_start": i,
                "word_idx_end": i
            })
            i += 1
            continue
            
        # Match 'boletim 1', 'boletim dois' etc.
        if w in ("boletim", "boletins") and i + 1 < len(all_words):
            next_w = normalize_word(all_words[i+1].get("text", ""))
            # Check if next word is a number or spelled number
            if re.match(r"^(\d+|um|dois|tres|três|quatro|cinco|seis|sete|oito|nove|dez)$", next_w):
                # Map spoken numbers to digits for ID standardization
                num_map = {"um": "1", "dois": "2", "tres": "3", "três": "3", "quatro": "4", "cinco": "5"}
                num = num_map.get(next_w, next_w)
                claquetes.append({
                    "id": f"B{num}".upper(),
                    "start": all_words[i]["start"],
                    "end": all_words[i+1]["end"],
                    "word_idx_start": i,
                    "word_idx_end": i+1
                })
                i += 2
                continue
                
        # Match 'b' followed by a number
        # DO NOT add 'de', 'e' here because it matches 'de 15', 'e 30' etc.
        if w in ("b", "be", "bê") and i + 1 < len(all_words):
            next_w = normalize_word(all_words[i+1].get("text", ""))
            if re.match(r"^(\d+|um|dois|tres|três|quatro|cinco|seis|sete|oito|nove|dez)$", next_w):
                num_map = {"um": "1", "dois": "2", "tres": "3", "três": "3", "quatro": "4", "cinco": "5"}
                num = num_map.get(next_w, next_w)
                claquetes.append({
                    "id": f"B{num}".upper(),
                    "start": all_words[i]["start"],
                    "end": all_words[i+1]["end"],
                    "word_idx_start": i,
                    "word_idx_end": i+1
                })
                i += 2
                continue

        i += 1
        
    return claquetes, all_words

def find_script_file(input_dir: Path, bulletin_id: str) -> Optional[Path]:
    """Busca o arquivo de script correspondente à claquete (ex: B1) na mesma pasta."""
    # Busca arquivos que contêm "_B1_" ou similar no nome
    patterns = [
        f"*{bulletin_id}*.txt",
        f"*{bulletin_id.lower()}*.txt"
    ]
    for pattern in patterns:
        for p in input_dir.glob(pattern):
            if p.is_file():
                return p
    return None

def parse_script_text(script_path: Path) -> Tuple[str, str]:
    """Lê e extrai os blocos CABEÇA e OFF de um script, sem modificar o arquivo."""
    try:
        content = script_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return "", ""
        
    lines = content.splitlines()
    cabeca_lines = []
    off_lines = []
    
    current_section = None # 'cabeca' or 'off'
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            continue
        if re.match(r"^CABEÇA:?$", line_strip, re.IGNORECASE):
            current_section = "cabeca"
            continue
        elif re.match(r"^OFF:?$", line_strip, re.IGNORECASE):
            current_section = "off"
            continue
            
        if current_section == "cabeca":
            cabeca_lines.append(line_strip)
        elif current_section == "off":
            off_lines.append(line_strip)
            
    return " ".join(cabeca_lines), " ".join(off_lines)

def find_split_by_script(bulletin_words: List[Dict], script_cabeca_text: str) -> Optional[int]:
    """Localiza o índice do último termo da CABEÇA no áudio por alinhamento difflib."""
    if not bulletin_words or not script_cabeca_text.strip():
        return None
        
    script_words = [normalize_word(w) for w in script_cabeca_text.split() if normalize_word(w)]
    if not script_words:
        return None
        
    trans_words = [normalize_word(w.get("text", "")) for w in bulletin_words]
    
    matcher = SequenceMatcher(None, script_words, trans_words)
    matching_blocks = matcher.get_matching_blocks()
    
    best_end = -1
    max_match_len = 0
    for block in matching_blocks:
        if block.size > 0:
            inferred_end = block.b + block.size - 1
            remaining_script_len = len(script_words) - (block.a + block.size)
            inferred_end += remaining_script_len
            
            # Limita a busca nos primeiros 85% do áudio do boletim
            if inferred_end < len(trans_words) * 0.85:
                if block.size > max_match_len:
                    max_match_len = block.size
                    best_end = inferred_end
                    
    if best_end != -1 and best_end < len(bulletin_words):
        return best_end
        
    return None

def find_cabeca_off_split(words: List[Dict]) -> Optional[Dict]:
    """
    Finds the split point between CABEÇA and OFF within a single bulletin's words.
    Returns info about the split point.
    """
    if not words:
        return None
        
    # 1. Look for explicit 'off' marker
    for i, w_obj in enumerate(words):
        w = normalize_word(w_obj.get("text", ""))
        if w == "off":
            return {
                "start": w_obj["start"],
                "end": w_obj["end"],
                "type": "marker",
                "word_idx": i
            }
            
    # 2. Look for the longest pause if no marker found
    # Assume CABEÇA isn't the very end, so we search in the first 70% of the audio
    max_pause = 0
    pause_point = None
    
    # We need at least 2 words to find a pause
    for i in range(len(words) - 1):
        # don't split in the last 30% of words (to avoid splitting near ASSINATURA)
        if i > len(words) * 0.7:
            break
            
        current_end = words[i]["end"]
        next_start = words[i+1]["start"]
        pause_duration = next_start - current_end
        
        if pause_duration > max_pause:
            max_pause = pause_duration
            pause_point = {
                "start": current_end + (pause_duration / 2), # midpoint of pause
                "end": current_end + (pause_duration / 2),
                "type": "pause",
                "word_idx": i
            }
            
    # Require at least 0.5s pause to be considered a structural split
    if max_pause > 0.5 and pause_point:
        return pause_point
        
    return None

def shift_timestamps(words: List[Dict], offset: float) -> List[Dict]:
    """Adjusts the timestamps of words so they are relative to 0.0 again."""
    shifted = []
    for w in words:
        w_copy = w.copy()
        w_copy["start"] = max(0.0, w["start"] - offset)
        w_copy["end"] = max(0.0, w["end"] - offset)
        shifted.append(w_copy)
    return shifted

def split_audio(clean_wav_path: str, segments: List[Dict], output_dir: str, original_input_path: Optional[str] = None) -> List[Dict]:
    """
    Splits the main audio into individual bulletins, and each bulletin into CABEÇA and OFF.
    Returns a list of bulletins with their respective files.
    """
    if AudioSegment is None:
        raise ImportError("pydub required for splitter")
        
    claquetes, all_words = detect_claquetes(segments)
    
    if not claquetes:
        # No markers found
        return []

    try:
        audio = AudioSegment.from_file(clean_wav_path)
    except Exception as e:
        print(f"[splitter] Erro ao abrir áudio: {e}")
        return []
        
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    results = []
    
    for i, claq in enumerate(claquetes):
        b_id = claq["id"]
        start_time_sec = claq["end"]
        start_time_ms = int(start_time_sec * 1000) 
        
        # End time is the start of the next claquete, or end of file
        end_time_sec = claquetes[i+1]["start"] if i + 1 < len(claquetes) else len(audio)/1000.0
        end_time_ms = int(end_time_sec * 1000)
        
        # Word boundaries for this bulletin
        word_start_idx = claq["word_idx_end"] + 1
        word_end_idx = claquetes[i+1]["word_idx_start"] if i + 1 < len(claquetes) else len(all_words)
        bulletin_words = all_words[word_start_idx:word_end_idx]
        
        # Extract audio chunk
        bulletin_audio = audio[start_time_ms:end_time_ms]
        
        # Tenta fatiar usando o alinhamento com o script original do texto (leitura apenas)
        split_point = None
        if original_input_path:
            input_dir = Path(original_input_path).parent
            script_path = find_script_file(input_dir, b_id)
            if script_path:
                cabeca_txt, off_txt = parse_script_text(script_path)
                if cabeca_txt:
                    split_idx = find_split_by_script(bulletin_words, cabeca_txt)
                    if split_idx is not None:
                        split_point = {
                            "start": bulletin_words[split_idx]["end"],
                            "end": bulletin_words[split_idx + 1]["start"] if split_idx + 1 < len(bulletin_words) else bulletin_words[split_idx]["end"],
                            "type": "script",
                            "word_idx": split_idx
                        }
                        print(f"[splitter] Fatiamento Cabeça/OFF de {b_id} alinhado com sucesso via script: {script_path.name}")
        
        # Fallback para fatiamento acústico/silêncio se o script não for encontrado ou falhar
        if not split_point:
            split_point = find_cabeca_off_split(bulletin_words)
        
        if split_point:
            # Shift the split point relative to the start of this bulletin
            split_start_relative = split_point["start"] - start_time_sec
            split_end_relative = split_point["end"] - start_time_sec
            
            split_time_ms = int(split_start_relative * 1000)
            cabeca_audio = bulletin_audio[:split_time_ms]
            
            if split_point["type"] == "marker":
                off_start_ms = int(split_end_relative * 1000)
                off_audio = bulletin_audio[off_start_ms:]
                
                idx = split_point["word_idx"]
                # Shift words back to 0.0 for the internal error_detector logic
                cabeca_words = shift_timestamps(bulletin_words[:idx], start_time_sec)
                off_words = shift_timestamps(bulletin_words[idx+1:], split_point["end"])
            else:
                off_audio = bulletin_audio[split_time_ms:]
                
                idx = split_point["word_idx"]
                cabeca_words = shift_timestamps(bulletin_words[:idx+1], start_time_sec)
                off_words = shift_timestamps(bulletin_words[idx+1:], split_point["start"])
        else:
            cabeca_audio = bulletin_audio
            off_audio = None
            cabeca_words = shift_timestamps(bulletin_words, start_time_sec)
            off_words = []
            
        # Export files
        cabeca_path = str(Path(output_dir) / f"{b_id}_cabeca.wav")
        cabeca_audio.export(cabeca_path, format="wav")
        
        off_path = None
        if off_audio and len(off_audio) > 0:
            off_path = str(Path(output_dir) / f"{b_id}_off.wav")
            off_audio.export(off_path, format="wav")
            
        results.append({
            "id": b_id,
            "cabeca_path": cabeca_path,
            "off_path": off_path,
            "cabeca_words": cabeca_words,
            "off_words": off_words,
            "original_start": start_time_sec
        })
        
    return results
