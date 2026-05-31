import os
from pathlib import Path
import re

# -------------------------------------------------
# 1️⃣  Configurações
# -------------------------------------------------
# Pasta onde os roteiros originais estão (Google Drive)
DRIVE_ROOT = Path(r"H:/Meu Drive/RADIO TJRN CONTEÚDO/PROGRAMAS/PROGRAMA GIRO NAS COMARCAS (10min)")

# Pasta de trabalho local (onde ficam os .txt finais)
BASE_WORKSPACE = Path(r"e:/NJUD/PROGRAMA GIRO NAS COMARCAS")
TTS_TXT_DIR   = BASE_WORKSPACE / "tts_txt"

# Relatórios de auditoria (tabelas markdown)
REPORT_2025 = BASE_WORKSPACE / "relatorios" / "relatorio_2025.md"
REPORT_2026 = BASE_WORKSPACE / "relatorios" / "relatorio_2026.md"

# Extensões reconhecidas como roteiros
ROUTINE_EXTS = {".docx", ".gdoc", ".txt"}

# Texto padrão quando o roteiro não for encontrado
PLACEHOLDER = "Roteiro não disponível para geração de áudio."

# -------------------------------------------------
# 2️⃣  Funções auxiliares
# -------------------------------------------------
try:
    from docx import Document
except ImportError:       # caso a dependência não esteja instalada
    Document = None


def extract_docx_text(docx_path: Path) -> str:
    """Retorna o texto puro de um .docx. Em falha devolve ''."""
    if Document is None:
        return ""
    try:
        doc = Document(str(docx_path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception:
        return ""


def find_roster_file(prog_num: str, year: str) -> Path | None:
    """Procura um arquivo .docx/.gdoc/.txt que corresponda ao número do programa
    dentro da pasta do Google Drive para o ano indicado.
    - Normaliza prog_num para dois dígitos.
    - Primeiro tenta encontrar a pasta cujo nome começa com o número.
    - Se falhar, faz busca recursiva por arquivos que contenham o número.
    """
    prog_num = prog_num.strip().zfill(2)          # garante 2 dígitos (01, 02, ...)
    year_root = DRIVE_ROOT / year
    if not year_root.is_dir():
        return None

    # 1️⃣ Tentativa rápida por pasta que começa com o número
    for entry in os.listdir(year_root):
        entry_path = year_root / entry
        if entry_path.is_dir() and entry.startswith(prog_num):
            for f in os.listdir(entry_path):
                if Path(f).suffix.lower() in ROUTINE_EXTS:
                    return entry_path / f

    # 2️⃣ Busca mais flexível: procura arquivos que contenham o número do programa
    for root, _, files in os.walk(year_root):
        for f in files:
            if Path(f).suffix.lower() in ROUTINE_EXTS and prog_num in f:
                return Path(root) / f
    return None


def parse_missing_programs(report_path: Path) -> list[tuple[str, str]]:
    """Lê um relatório markdown e devolve (prog_num, year) para linhas com ❌.
    Normaliza o número para dois dígitos.
    """
    missing = []
    year = report_path.stem.split("_")[-1]   # “relatorio_2025” → “2025”
    with report_path.open("r", encoding="utf-8") as f:
        for line in f:
            if "❌" in line:
                m = re.match(r"\|\s*([^|]+?)\s*\|.*\|\s*❌\s*\|", line)
                if m:
                    prog_num = m.group(1).strip().split()[0]  # captura apenas o número inicial
                    prog_num = prog_num.zfill(2)               # garante duas casas
                    missing.append((prog_num, year))
    return missing

# -------------------------------------------------
# 3️⃣  Execução principal
# -------------------------------------------------
def main():
    TTS_TXT_DIR.mkdir(parents=True, exist_ok=True)

    # 3.1 – coleta os programas que precisam de txt (2025 + 2026)
    missing_programs = []
    for report in (REPORT_2025, REPORT_2026):
        if report.is_file():
            missing_programs.extend(parse_missing_programs(report))

    if not missing_programs:
        print("Nenhum programa sem áudio encontrado nos relatórios.")
        return

    # 3.2 – gera/atualiza os arquivos .txt
    for prog_num, year in missing_programs:
        src_file = find_roster_file(prog_num, year)

        # Extrai o conteúdo do roteiro
        if src_file:
            if src_file.suffix.lower() == ".docx":
                text_content = extract_docx_text(src_file)
            else:
                try:
                    text_content = src_file.read_text(encoding="utf-8")
                except Exception:
                    text_content = ""
        else:
            text_content = ""

        if not text_content.strip():
            text_content = PLACEHOLDER

        safe_name = prog_num.replace(" ", "_").replace("/", "-")
        txt_path = TTS_TXT_DIR / f"{safe_name}.txt"
        txt_path.write_text(text_content, encoding="utf-8")
        print(f"Criado/atualizado txt para programa {prog_num} (ano {year}): {txt_path}")

if __name__ == "__main__":
    main()
