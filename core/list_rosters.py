import os
from pathlib import Path

# Diretórios de anos
BASE = Path(r"e:/NJUD/PROGRAMA GIRO NAS COMARCAS")
YEARS = ["2025", "2026"]

# Extensões que consideramos como roteiros
ROUTINE_EXTS = {".docx", ".gdoc", ".txt"}

def list_rosters():
    for year in YEARS:
        year_path = BASE / year
        if not year_path.is_dir():
            print(f"Ano {year} não encontrado em {year_path}")
            continue
        print(f"\n=== Roteiros em {year_path} ===")
        for root, dirs, files in os.walk(year_path):
            for f in files:
                ext = Path(f).suffix.lower()
                if ext in ROUTINE_EXTS:
                    full_path = Path(root) / f
                    print(full_path)

if __name__ == "__main__":
    list_rosters()
