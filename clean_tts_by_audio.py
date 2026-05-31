"""
clean_tts_by_audio.py
=====================
Remove da pasta tts_txt todos os arquivos .txt cujo programa
correspondente JÁ POSSUI um .mp3 editado na pasta do Google Drive.

Lógica:
  - Varre H:/.../2025 e 2026 buscando pastas com pelo menos 1 .mp3
    (qualquer nome — edição já feita = mp3 presente).
  - Normaliza o número da pasta (int) e o ano.
  - Tenta casar com os arquivos .txt pelo número extraído do nome:
      GNC-{num}-{year}.txt  →  (year, num_int)
      GNC-{year}-{folder}.txt  →  (year, folder_str)
  - Apaga os matches; mantém os sem mp3 (precisam de TTS).
"""
import os
import re
import sys
import pathlib

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
MEU_DRIVE = "H:\\Meu Drive"
TTS_DIR   = pathlib.Path(r"E:\NJUD\PROGRAMA GIRO NAS COMARCAS\tts_txt")
ANOS      = (2025, 2026)
# ---------------------------------------------------------------------------

# 1. Detecta o nome real da pasta RADIO TJRN CONTEÚDO (evita hardcode de acento)
tjrn_folder = next(f for f in os.listdir(MEU_DRIVE) if "TJRN" in f.upper())
ROOT_PROG   = os.path.join(MEU_DRIVE, tjrn_folder,
                           "PROGRAMAS", "PROGRAMA GIRO NAS COMARCAS (10min)")


def has_mp3(folder: str) -> bool:
    """Retorna True se a pasta contiver QUALQUER arquivo .mp3."""
    try:
        return any(f.lower().endswith(".mp3") for f in os.listdir(folder))
    except PermissionError:
        return False


# 2. Constrói set de (ano, num_int) que já têm áudio
#    Para 2026 o folder pode ser 'FEV', 'MAR', etc. — guardamos string também.
progs_com_audio: set[tuple[int, object]] = set()

for ano in ANOS:
    ano_dir = os.path.join(ROOT_PROG, str(ano))
    if not os.path.isdir(ano_dir):
        print(f"[aviso] Pasta {ano} não encontrada: {ano_dir}")
        continue
    for entry in os.listdir(ano_dir):
        prog_dir = os.path.join(ano_dir, entry)
        if not os.path.isdir(prog_dir):
            continue
        if has_mp3(prog_dir):
            # Tenta normalizar como inteiro (ex: "01" → 1, "00 - Piloto" → 0)
            num_match = re.match(r"^(\d+)", entry)
            if num_match:
                progs_com_audio.add((ano, int(num_match.group(1))))
            else:
                # Ex: "FEV", "MAR" → guarda string normalizada
                progs_com_audio.add((ano, entry.upper()))

print(f"\nProgramas com áudio no Drive: {len(progs_com_audio)}")
for item in sorted(progs_com_audio, key=lambda x: (x[0], str(x[1]))):
    print(f"  {item[0]} / {item[1]}")


# 3. Função que extrai (ano, num_or_str) do nome do arquivo .txt
#    Padrões suportados:
#      GNC-011-2025.txt  →  (2025, 11)
#      GNC-11-2025.txt   →  (2025, 11)
#      GNC-2026-FEV.txt  →  (2026, 'FEV')
PATTERNS = [
    # GNC-{num}-{ano}
    re.compile(r"GNC-0*(\d+)-(\d{4})\.txt$", re.IGNORECASE),
    # GNC-{ano}-{folder}
    re.compile(r"GNC-(\d{4})-([A-Z0-9]+)\.txt$", re.IGNORECASE),
]

def parse_txt_key(fname: str):
    m = PATTERNS[0].match(fname)
    if m:
        return (int(m.group(2)), int(m.group(1)))   # (ano, num)
    m = PATTERNS[1].match(fname)
    if m:
        return (int(m.group(1)), m.group(2).upper()) # (ano, folder_str)
    return None


# 4. Varredura e deleção
to_delete = []
to_keep   = []
unmatched = []

for f in sorted(TTS_DIR.glob("*.txt")):
    key = parse_txt_key(f.name)
    if key is None:
        unmatched.append(f.name)
        continue
    if key in progs_com_audio:
        to_delete.append((f, key))
    else:
        to_keep.append((f.name, key))

print(f"\n{'='*55}")
print(f"TXTs que SERAO APAGADOS (programa ja tem mp3): {len(to_delete)}")
for f, key in to_delete:
    print(f"  DEL  {f.name}  ({key[0]}/{key[1]})")

print(f"\nTXTs que SERAO MANTIDOS (precisam de TTS): {len(to_keep)}")
for name, key in to_keep:
    print(f"  OK   {name}  ({key[0]}/{key[1]})")

if unmatched:
    print(f"\nNao reconhecidos (mantidos por segurança): {len(unmatched)}")
    for n in unmatched:
        print(f"  ?    {n}")

print(f"\n{'='*55}")
resp = input(f"Confirma apagar {len(to_delete)} arquivo(s)? [s/N] ").strip().lower()
if resp == "s":
    for f, _ in to_delete:
        f.unlink()
    print(f"✅ {len(to_delete)} arquivo(s) apagado(s).")
    print(f"✅ {len(to_keep)} arquivo(s) mantido(s) para TTS.")
else:
    print("Operação cancelada.")
