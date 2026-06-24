"""Processamento técnico de áudio: conversão, redução de ruído, normalização.

Contém stubs que usam ffmpeg/pydub/noisereduce/pyloudnorm quando implementado.
"""

from pathlib import Path
from typing import Dict
import subprocess


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
    """Stub pipeline: converte e devolve caminho do clean wav.
    Implementar: noisereduce, pyloudnorm, compressão.
    """
    wav = ensure_wav(input_path, output_path)
    # TODO: apply noise reduction and loudness normalization
    return wav


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Uso: python -m voice_agent.audio_processor <in> <out>")
    else:
        print(process_audio(sys.argv[1], sys.argv[2]))
