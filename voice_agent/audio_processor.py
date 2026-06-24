"""Processamento técnico de áudio: conversão, redução de ruído, normalização.

Contém stubs que usam ffmpeg/pydub/noisereduce/pyloudnorm quando implementado.
"""

from pathlib import Path
from typing import Dict
import subprocess
import os

try:
    import noisereduce as nr
    import pyloudnorm as pyln
    import soundfile as sf
    import numpy as np
except Exception:
    nr = None
    pyln = None
    sf = None
    np = None


def ensure_wav(input_path: str, output_path: str) -> str:
    """Converte input para WAV 44.1kHz mono via ffmpeg.
    Retorna caminho do arquivo WAV gerado.
    """
    input_p = Path(input_path)
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_p),
        "-ar",
        "44100",
        "-ac",
        "1",
        "-sample_fmt",
        "s16",
        str(out_p),
    ]
    subprocess.run(cmd, check=False)
    return str(out_p)


def process_audio(input_path: str, output_path: str, config: Dict = None) -> str:
    """Pipeline: converte, aplica redução de ruído e normalização de loudness quando possível.

    Se as bibliotecas (`noisereduce`, `pyloudnorm`, `soundfile`, `numpy`) não estiverem
    disponíveis, faz apenas a conversão via ffmpeg.
    Retorna caminho do WAV processado.
    """
    cfg = config or {}
    wav = ensure_wav(input_path, output_path)

    if nr is None or pyln is None or sf is None or np is None:
        # não há libs de processamento; retorna o wav convertido
        return wav

    # Carrega áudio
    data, sr = sf.read(wav)
    if data.ndim > 1:
        data = np.mean(data, axis=1)

    # Ruído: usa um trecho inicial como perfil (primeiros 0.5s)
    noise_clip = data[: int(0.5 * sr)] if len(data) > sr // 2 else None
    try:
        if noise_clip is not None and cfg.get("noise_reduction", True):
            reduced = nr.reduce_noise(y=data, y_noise=noise_clip, prop_decrease=cfg.get("noise_reduction_strength", 0.6))
        else:
            reduced = data
    except Exception:
        reduced = data

    # Normalização de loudness para target LUFS
    try:
        meter = pyln.Meter(sr)
        loudness = meter.integrated_loudness(reduced)
        target = cfg.get("loudness_target_lufs", -16.0)
        loudness_diff = target - loudness
        reduced = pyln.normalize.loudness(reduced, loudness, target)
    except Exception:
        pass

    # Escreve arquivo final
    try:
        sf.write(wav, reduced, sr, subtype="PCM_16")
    except Exception:
        # fallback: manter arquivo gerado pelo ffmpeg
        pass

    return wav


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Uso: python -m voice_agent.audio_processor <in> <out>")
    else:
        print(process_audio(sys.argv[1], sys.argv[2], {}))
