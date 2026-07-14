"""Assembler: aplica cortes aprovados, mistura assets e exporta o arquivo final.

API principal:
- assemble(program_config, clean_wav_path, cuts, output_path) -> output_path
"""

from typing import List, Dict, Optional
from pathlib import Path

try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None

from .asset_manager import load_assets, load_program_config


def _apply_cuts(audio: AudioSegment, cuts: List[Dict]) -> AudioSegment:
    if not cuts:
        return audio
    segments = []
    cursor = 0
    for cut in sorted(cuts, key=lambda x: x.get("start_ms", 0)):
        start = int(cut.get("start_ms", 0))
        end = int(cut.get("end_ms", 0))
        if start > cursor:
            segments.append(audio[cursor:start])
        cursor = max(cursor, end)
    if cursor < len(audio):
        segments.append(audio[cursor:])
    return sum(segments) if segments else AudioSegment.silent(duration=0)


def _load_audio(path: Optional[str]) -> Optional[AudioSegment]:
    if path and Path(path).exists():
        try:
            return AudioSegment.from_file(path)
        except Exception:
            return None
    return None


def assemble(program: str, clean_wav_path: str, cuts: List[Dict], output_path: str) -> str:
    """Monte arquivo final a partir do clean wav e regras do programa.

    cuts: lista de {start_ms, end_ms}
    program: nome do programa para carregar config/asset references
    """
    config = load_program_config(program)
    assets = load_assets(program)
    montagem = config.get("montagem", {})
    estrutura = montagem.get("estrutura", [
        {"tipo": "voz", "bg": None, "fade_in": 0.5, "fade_out": 0.5}
    ])

    base_audio = AudioSegment.from_wav(clean_wav_path)
    voz_audio = _apply_cuts(base_audio, cuts)

    if AudioSegment is None:
        raise ImportError("pydub is required to run assembler. Install it with pip install pydub.")

    result = AudioSegment.silent(duration=0)
    bg_audio = None
    if isinstance(estrutura, list):
        for item in estrutura:
            tipo = item.get("tipo")
            if tipo == "vinheta":
                arquivo_key = item.get("arquivo")
                vinheta_path = assets.get(arquivo_key) if arquivo_key else None
                vinheta = _load_audio(vinheta_path)
                if vinheta:
                    if item.get("fade_in"):
                        vinheta = vinheta.fade_in(int(item.get("fade_in") * 1000))
                    if item.get("fade_out"):
                        vinheta = vinheta.fade_out(int(item.get("fade_out") * 1000))
                    result += vinheta
            elif tipo == "voz":
                if item.get("bg"):
                    bg_path = assets.get(item.get("bg"))
                    bg_audio = _load_audio(bg_path)
                voice_segment = voz_audio
                if bg_audio:
                    volume_bg = item.get("bg_volume", -18)
                    bg_loop = bg_audio
                    if len(bg_loop) < len(voice_segment):
                        repeats = (len(voice_segment) // len(bg_loop)) + 1
                        bg_loop = bg_loop * repeats
                    bg_loop = bg_loop[: len(voice_segment)] + volume_bg
                    voice_segment = voice_segment.overlay(bg_loop)
                if item.get("fade_in"):
                    voice_segment = voice_segment.fade_in(int(item.get("fade_in") * 1000))
                if item.get("fade_out"):
                    voice_segment = voice_segment.fade_out(int(item.get("fade_out") * 1000))
                result += voice_segment
            else:
                continue
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    result.export(str(out_p), format="mp3", bitrate="320k")
    return str(out_p)
def assemble_multipart(program: str, cabeca_path: str, cabeca_cuts: List[Dict], off_path: Optional[str], off_cuts: List[Dict], output_path: str) -> str:
    """Monta arquivo final a partir das frações CABEÇA e OFF."""
    if AudioSegment is None:
        raise ImportError("pydub is required to run assembler. Install it with pip install pydub.")
        
    config = load_program_config(program)
    assets = load_assets(program)

    try:
        cabeca_base = AudioSegment.from_wav(cabeca_path)
    except Exception:
        cabeca_base = AudioSegment.silent(duration=0)
        
    cabeca_audio = _apply_cuts(cabeca_base, cabeca_cuts)
    
    off_audio = AudioSegment.silent(duration=0)
    if off_path and Path(off_path).exists():
        try:
            off_base = AudioSegment.from_wav(off_path)
            off_audio = _apply_cuts(off_base, off_cuts)
        except Exception:
            pass

    has_cabeca = len(cabeca_audio) > 0
    has_off = len(off_audio) > 0

    # 1. Montar a versão RÁDIO (completa com vinhetas e trilha)
    radio_result = AudioSegment.silent(duration=0)
    
    abertura_path = assets.get("vinheta_abertura")
    abertura = _load_audio(abertura_path)
    if abertura:
        radio_result += abertura
        
    if has_cabeca:
        radio_result += cabeca_audio
        
    transicao_path = assets.get("vinheta_transicao")
    transicao = _load_audio(transicao_path)
    
    # Vinheta de transição só entre Cabeça e OFF
    if has_cabeca and has_off and transicao:
        radio_result += transicao
        
    if has_off:
        bg_path = assets.get("bg_musica")
        bg_audio = _load_audio(bg_path)
        
        voice_segment = off_audio
        if bg_audio:
            volume_bg = -18
            bg_loop = bg_audio
            if len(bg_loop) < len(voice_segment):
                repeats = (len(voice_segment) // len(bg_loop)) + 1
                bg_loop = bg_loop * repeats
            bg_loop = bg_loop[: len(voice_segment)] + volume_bg
            voice_segment = voice_segment.overlay(bg_loop)
            
        radio_result += voice_segment

    encerramento_path = assets.get("vinheta_encerramento")
    encerramento = _load_audio(encerramento_path)
    if encerramento:
        radio_result += encerramento

    # 2. Montar a versão MAILING (Cabeça + Transição + OFF, sem vinheta abertura/encerramento, sem trilha BG)
    mailing_result = AudioSegment.silent(duration=0)
    if has_cabeca and has_off:
        mailing_result += cabeca_audio
        if transicao:
            mailing_result += transicao
        mailing_result += off_audio
    elif has_cabeca:
        mailing_result += cabeca_audio
    elif has_off:
        mailing_result += off_audio

    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    
    # Exporta a versão Rádio padrão no caminho original
    radio_result.export(str(out_p), format="mp3", bitrate="320k")
    
    # Se o programa for boletins, gera também os arquivos de forma explícita com sufixos
    if program == "boletins":
        radio_path = out_p.parent / f"{out_p.stem}_radio.mp3"
        mailing_path = out_p.parent / f"{out_p.stem}_mailing.mp3"
        
        radio_result.export(str(radio_path), format="mp3", bitrate="320k")
        mailing_result.export(str(mailing_path), format="mp3", bitrate="320k")
        
        print(f"[assembler] Gerou versões de Boletim: Rádio -> {radio_path}, Mailing -> {mailing_path}")
        
    return str(out_p)

if __name__ == "__main__":
    print("Assembler stub")
