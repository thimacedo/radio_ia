import os
import re
from pathlib import Path

# Optional: import for .docx parsing (python-docx). Ensure dependency is installed.
try:
    from docx import Document
except ImportError:
    Document = None  # Will handle missing dependency gracefully.

# Paths
BASE_WORKSPACE = r"e:/NJUD/PROGRAMA GIRO NAS COMARCAS"
REPORT_PATH = os.path.join(BASE_WORKSPACE, "relatorios", "relatorio_2025.md")
TTS_TXT_DIR = os.path.join(BASE_WORKSPACE, "tts_txt")
YEAR_DIR = os.path.join(BASE_WORKSPACE, "2025")
# Fonte dos roteiros (Google Drive)
SOURCE_ROOT = r"H:/Meu Drive/RADIO TJRN CONTEÚDO/PROGRAMAS/PROGRAMA GIRO NAS COMARCAS (10min)"

os.makedirs(TTS_TXT_DIR, exist_ok=True)

# Texto padrão quando o roteiro não for encontrado.
PLACEHOLDER = "Roteiro não disponível para geração de áudio."

def extract_docx_text(docx_path: str) -> str:
    """Extrai o texto puro de um arquivo .docx.
    Retorna string vazia se a biblioteca não estiver disponível ou houver falha.
    """
    if Document is None:
        return ""
    try:
        doc = Document(docx_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except Exception:
        return ""

def find_roster_file(prog_num: str) -> str:
    """Busca um arquivo .docx, .gdoc ou texto simples que corresponda ao número do programa.
    O diretório do Google Drive contém subpastas por ano (ex.: 2025) e, dentro delas,
    pastas cujos nomes começam com o número do programa (ex.: "01", "01 - Piloto").
    Retorna o caminho absoluto do primeiro arquivo encontrado ou string vazia.
    """
    year_root = os.path.join(SOURCE_ROOT, "2025")
    for entry in os.listdir(year_root):
        entry_path = os.path.join(year_root, entry)
        if os.path.isdir(entry_path) and entry.startswith(prog_num):
            for f in os.listdir(entry_path):
                if f.lower().endswith(('.docx', '.gdoc', '.txt')):
                    return os.path.join(entry_path, f)
    return ""

# Identifica os programas que ainda não têm áudio (coluna "❌").
missing_programs = []
with open(REPORT_PATH, "r", encoding="utf-8") as f:
    for line in f:
        # Linha da tabela markdown: | 01 |  | ✅ | ❌ |
        match = re.match(r"\|\s*([^|]+?)\s*\|.*\|\s*❌\s*\|", line)
        if match:
            prog_num = match.group(1).strip()
            missing_programs.append(prog_num)

for prog_num in missing_programs:
    source_file = find_roster_file(prog_num)
    if source_file:
        if source_file.lower().endswith('.docx'):
            text_content = extract_docx_text(source_file)
        else:
            try:
                with open(source_file, "r", encoding="utf-8") as sf:
                    text_content = sf.read()
            except Exception:
                text_content = ""
    else:
        text_content = ""

    if not text_content:
        text_content = PLACEHOLDER

    safe_name = prog_num.replace(" ", "_").replace("/", "-")
    txt_path = os.path.join(TTS_TXT_DIR, f"{safe_name}.txt")
    if not os.path.exists(txt_path):
        with open(txt_path, "w", encoding="utf-8") as txt_file:
            txt_file.write(text_content)
        print(f"Criado txt para programa {prog_num}: {txt_path}")
