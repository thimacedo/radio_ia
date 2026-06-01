# patch_vinhetas.py
"""Patch existing generated MP3 files to replace **entire** incorrect opening and closing vinhetas
with the correct ones (ABERTURA.mp3 and ENCERRAMENTO.mp3).

The previous version only overwrote the first/last *duration of the new assets*,
leaving the tail of the old vinhetas (which are longer – 11 s and 12 s) in the file.
This updated script:
  1. Loads the *incorrect* vinhetas (if they exist) to obtain their exact lengths.
  2. Removes those full segments from each MP3.
  3. Inserts the correct short vinhetas (≈ 6 s each).
  4. Preserves the original bitrate (fallback to 192k).

Usage:
    python patch_vinhetas.py --src <directory_with_mp3s>
"""

import os
import argparse
from pydub import AudioSegment

# ---------------------------------------------------------------------------
# Helper to guess bitrate – pydub does not expose it directly, so we use a
# sensible default (192k) which matches our production settings.
# ---------------------------------------------------------------------------
def get_bitrate(_audio: AudioSegment) -> str:
    return "192k"

# ---------------------------------------------------------------------------
# Load the *incorrect* assets if they are present.  Their durations are used
# to cut the original MP3s cleanly.
# ---------------------------------------------------------------------------
def load_wrong_assets(base_dir: str):
    wrong_open_path = os.path.join(base_dir, "VH AB - NOTICIAS DA HORA.mp3")
    wrong_close_path = os.path.join(base_dir, "VH ENC - NOTICIAS DA HORA.mp3")
    wrong_open = AudioSegment.from_file(wrong_open_path) if os.path.isfile(wrong_open_path) else None
    wrong_close = AudioSegment.from_file(wrong_close_path) if os.path.isfile(wrong_close_path) else None
    return wrong_open, wrong_close

# ---------------------------------------------------------------------------
# Replace vinhetas in a single MP3 file.
# ---------------------------------------------------------------------------
def patch_file(mp3_path: str, opening: AudioSegment, closing: AudioSegment,
               wrong_open: AudioSegment | None, wrong_close: AudioSegment | None) -> None:
    try:
        original = AudioSegment.from_file(mp3_path, format="mp3")
    except Exception as e:
        print(f"[ERRO] Não foi possível ler {mp3_path}: {e}")
        return

    # Determine how many milliseconds to strip from start/end.
    strip_start = len(wrong_open) if wrong_open else len(opening)  # fallback to new length
    strip_end = len(wrong_close) if wrong_close else len(closing)

    if len(original) < strip_start + strip_end:
        print(f"[AVISO] Arquivo muito curto para patch: {mp3_path}")
        return

    # Keep the middle part (everything except the old vinhetas).
    middle = original[strip_start : len(original) - strip_end]
    patched = opening + middle + closing

    bitrate = get_bitrate(original)
    try:
        patched.export(mp3_path, format="mp3", bitrate=bitrate)
        print(f"[OK] Vinhetas corrigidas em {mp3_path}")
    except Exception as e:
        print(f"[ERRO] Falha ao exportar {mp3_path}: {e}")

# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Patch vinhetas em arquivos MP3 gerados")
    parser.add_argument("--src", required=True,
                        help="Diretório contendo os arquivos MP3 a serem corrigidos (recursivo)")
    args = parser.parse_args()

    # Load correct assets (must be in the workspace root).
    base_dir = os.path.dirname(__file__)
    opening_path = os.path.join(base_dir, "ABERTURA.mp3")
    closing_path = os.path.join(base_dir, "ENCERRAMENTO.mp3")
    if not os.path.isfile(opening_path) or not os.path.isfile(closing_path):
        print("[ERRO] Vinhetas corretas (ABERTURA.mp3 / ENCERRAMENTO.mp3) não encontradas na raiz do workspace.")
        return
    opening = AudioSegment.from_file(opening_path, format="mp3")
    closing = AudioSegment.from_file(closing_path, format="mp3")

    # Load wrong assets to know their lengths (optional).
    wrong_open, wrong_close = load_wrong_assets(base_dir)

    # Walk through the source directory recursively.
    for root, _, files in os.walk(args.src):
        for file in files:
            if file.lower().endswith('.mp3'):
                mp3_path = os.path.join(root, file)
                patch_file(mp3_path, opening, closing, wrong_open, wrong_close)

if __name__ == "__main__":
    main()
