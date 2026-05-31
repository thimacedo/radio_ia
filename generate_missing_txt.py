"""
generate_missing_txt.py  —  versão com suporte a .gdoc
=======================================================
Este arquivo é uma versão de REFERÊNCIA que mostra como integrar
o gdoc_exporter ao fluxo existente.

Partes marcadas com  ← NOVO  são as únicas adições necessárias.
O restante representa a estrutura típica do script original.
"""

from __future__ import annotations

import re
from pathlib import Path

# ← NOVO: importa o exportador de .gdoc
from gdoc_exporter import export_gdoc_to_txt   # deve estar no mesmo diretório

# ---------------------------------------------------------------------------
# Configurações (ajuste conforme seu ambiente)
# ---------------------------------------------------------------------------
DRIVE_ROOT = Path(r"e:/NJUD/PROGRAMA GIRO NAS COMARCAS")
OUTPUT_ROOT = Path("e:/NJUD/txt")          # pasta onde os .txt são gravados
PLACEHOLDER = "Roteiro não disponível para geração de áudio."

YEARS = ["2025", "2026"]


# ---------------------------------------------------------------------------
# Funções auxiliares existentes (mantidas sem alteração)
# ---------------------------------------------------------------------------

def _numero_from_name(name: str) -> str | None:
    """Extrai o número do programa a partir do nome do arquivo.
    Suporta 1 a 3 dígitos e devolve sempre com três dígitos (ex: '1' -> '001').
    """
    match = re.search(r"\d{1,3}", name)
    return match.group(0).zfill(3) if match else None


def _find_script_file(numero: str) -> Path | None:
    """
    Procura o arquivo de roteiro nas pastas de anos configurados.

    Busca recursivamente em todos os subdiretórios (ex.: 2025/01, 2025/02, …)
    para localizar arquivos cujo nome contenha o número do programa.
    Retorna somente arquivos suportados (.txt, .docx, .gdoc).
    """
    for year in YEARS:
        folder = DRIVE_ROOT / year
        if not folder.is_dir():
            continue
        # rglob percorre diretórios e subdiretórios
        for f in folder.rglob('*'):
            if f.is_dir():
                continue  # ignora pastas
            if _numero_from_name(f.name) == numero:
                if f.suffix.lower() in {".txt", ".docx", ".gdoc"}:
                    return f
    return None


# ---------------------------------------------------------------------------
# ← NOVO: função que lê o conteúdo independente do tipo de arquivo
# ---------------------------------------------------------------------------

def _read_script_content(src_file: Path) -> str:
    """
    Lê o conteúdo textual do roteiro a partir de qualquer formato suportado.

    Suporte:
        .txt   → leitura direta
        .docx  → python-docx  (comportamento original, mantido)
        .gdoc  → Google Drive API via gdoc_exporter  ← NOVO
        outros → retorna PLACEHOLDER
    """
    suffix = src_file.suffix.lower()

    # — .txt simples —
    if suffix == ".txt":
        return src_file.read_text(encoding="utf-8", errors="replace")

    # — Word (.docx) — comportamento original mantido —
    if suffix == ".docx":
        try:
            from docx import Document          # python-docx
            doc = Document(str(src_file))
            paragraphs = [p.text for p in doc.paragraphs]
            return "\n".join(paragraphs)
        except Exception as exc:
            print(f"  ⚠️  Erro ao ler .docx '{src_file.name}': {exc}")
            return PLACEHOLDER

    # — Google Doc (.gdoc) — NOVO —
    if suffix == ".gdoc":
        try:
            print(f"  🌐 Exportando Google Doc: {src_file.name} …")
            content = export_gdoc_to_txt(src_file)
            if content.strip():
                return content
            print(f"  ⚠️  Documento exportado, mas vazio: {src_file.name}")
            return PLACEHOLDER
        except FileNotFoundError as exc:
            print(f"  ❌ Credenciais não encontradas: {exc}")
            return PLACEHOLDER
        except Exception as exc:
            print(f"  ❌ Falha ao exportar '{src_file.name}': {exc}")
            return PLACEHOLDER

    # — formato desconhecido —
    print(f"  [WARN] Formato não suportado: {src_file.suffix} ({src_file.name})")
    return PLACEHOLDER


# ---------------------------------------------------------------------------
# Lógica principal (adaptada do script original)

# ==== FUNÇÃO AUXILIAR: extrair programas sem áudio do relatório ====

def _extract_missing_programs(report_path: Path) -> list[str]:
    """Lê o markdown de relatório e devolve uma lista de números (strings)
    cujo campo "Audio OK" está marcado como ❌.
    """
    missing = []
    for line in report_path.read_text(encoding="utf-8").splitlines():
        # Linha de tabela tem o formato: | <prog> | <date> | <roteiro> | <audio> |
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.strip("| ").split("|")]
        if len(parts) < 4:
            continue
        prog, _, _, audio = parts[:4]
        if "❌" in audio:
            prog_num = prog.split()[0]
            missing.append(prog_num.zfill(3))
    return missing

# Carrega listas de programas ausentes dos relatórios existentes
missing_2025: list[str] = []
report_2025 = Path(r"e:/NJUD/PROGRAMA GIRO NAS COMARCAS/relatorios/relatorio_2025.md")
if report_2025.exists():
    missing_2025 = _extract_missing_programs(report_2025)

missing_2026: list[str] = []
report_2026 = Path(r"e:/NJUD/PROGRAMA GIRO NAS COMARCAS/relatorios/relatorio_2026.md")
if report_2026.exists():
    missing_2026 = _extract_missing_programs(report_2026)

# Lista final de programas sem áudio (mescla ambas as listas)
programas_sem_audio = missing_2025 + missing_2026
# ---------------------------------------------------------------------------

def generate_missing_txt(numeros_sem_audio: list[str]) -> None:
    """
    Para cada número de programa sem áudio, localiza o roteiro e
    grava o arquivo .txt correspondente em OUTPUT_ROOT.
    """
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    total = len(numeros_sem_audio)

    for idx, numero in enumerate(numeros_sem_audio, 1):
        out_path = OUTPUT_ROOT / f"programa_{numero}.txt"
        print(f"[{idx}/{total}] Programa {numero} ...")

        src_file = _find_script_file(numero)

        if src_file is None:
            print(f"  [WARN] Roteiro não encontrado para o programa {numero}.")
            out_path.write_text(PLACEHOLDER, encoding="utf-8")
            continue

        print(f"  [INFO] Arquivo fonte: {src_file.name}  ({src_file.suffix})")
        content = _read_script_content(src_file)   # ← usa a nova função
        out_path.write_text(content, encoding="utf-8")

        if content == PLACEHOLDER:
            print(f"  [WARN] Gravado com placeholder.")
        else:
            print(f"  [OK] Gravado: {out_path.name}  ({len(content)} caracteres)")


# ---------------------------------------------------------------------------
# Ponto de entrada (exemplo — adapte ao seu código de leitura do relatório)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Executa a geração usando a lista de programas ausentes extraída dos relatórios
    generate_missing_txt(programas_sem_audio)
