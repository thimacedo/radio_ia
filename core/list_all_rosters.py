import os
from pathlib import Path

# ----------------------------------------------------------------------
# 1️⃣  Caminho raiz onde os roteiros estão (Google Drive)
# ----------------------------------------------------------------------
DRIVE_ROOT = Path(r"H:/Meu Drive/RADIO TJRN CONTEÚDO/PROGRAMAS/PROGRAMA GIRO NAS COMARCAS (10min)")

# 2️⃣  Anos que queremos inspecionar
YEARS = ["2025", "2026"]

# 3️⃣  Extensões consideradas como roteiros
ROUTINE_EXTS = {".docx", ".gdoc", ".txt"}

def list_rosters():
    """Percorre recursivamente as pastas de cada ano e imprime o caminho
    completo de todos os arquivos de roteiro encontrados."""
    for year in YEARS:
        year_path = DRIVE_ROOT / year
        if not year_path.is_dir():
            print(f"[Aviso] Pasta do ano {year} não encontrada: {year_path}")
            continue
        print(f"\n=== Roteiros em {year_path} ===")
        found = False
        for root, dirs, files in os.walk(year_path):
            for f in files:
                ext = Path(f).suffix.lower()
                if ext in ROUTINE_EXTS:
                    found = True
                    full_path = Path(root) / f
                    print(full_path)
        if not found:
            print("  (nenhum roteiro encontrado)")

if __name__ == "__main__":
    list_rosters()
