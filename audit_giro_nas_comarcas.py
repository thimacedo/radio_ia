"""
audit_giro_nas_comarcas.py
==========================
Audita a pasta do Google Drive (montada localmente em H:) e:
  - Gera relatórios .md com o status de roteiro + áudio por programa.
  - Para cada programa SEM áudio que POSSUI roteiro, exporta o texto
    para um arquivo .txt em TTS_DIR, pronto para o TTS.

Suporte a formatos de roteiro:
  .docx  → python-docx
  .gdoc  → Google Drive API (conta de serviço)   ← corrigido
  .txt   → leitura direta

Dependências extras (além das do projeto original):
  & e:/NJUD/.venv/Scripts/python.exe -m pip install --upgrade ^
      python-docx ^
      google-api-python-client google-auth-httplib2 google-auth-oauthlib
"""

from __future__ import annotations

import datetime
import io
import os
import pathlib
import re
import shutil
import sys

# ---------------------------------------------------------------------------
# Configurações de caminho
# ---------------------------------------------------------------------------
ROOT_DRIVE  = r"H:/Meu Drive/RADIO TJRN CONTEÚDO/PROGRAMAS/PROGRAMA GIRO NAS COMARCAS (10min)"
WORKSPACE   = r"e:/NJUD/PROGRAMA GIRO NAS COMARCAS"
REPORTS_DIR = os.path.join(WORKSPACE, "relatorios")
TTS_DIR     = os.path.join(WORKSPACE, "tts_txt")
CREDENTIALS = r"e:/NJUD/gen-lang-client-0980378916-8cc8eb1488d1.json"

os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(TTS_DIR, exist_ok=True)

PLACEHOLDER = "Roteiro não disponível para geração de áudio."

# ---------------------------------------------------------------------------
# Google Drive API — inicialização lazy (só carrega se houver .gdoc)
# ---------------------------------------------------------------------------
_drive_service = None   # cache do cliente autenticado


def _get_drive_service():
    """Constrói (ou reutiliza) o cliente autenticado da Google Drive API."""
    global _drive_service
    if _drive_service is not None:
        return _drive_service

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError(
            "Bibliotecas do Google não encontradas.\n"
            "Execute:\n"
            "  & e:/NJUD/.venv/Scripts/python.exe -m pip install --upgrade "
            "google-api-python-client google-auth-httplib2 google-auth-oauthlib"
        )

    if not os.path.exists(CREDENTIALS):
        raise FileNotFoundError(
            f"Credenciais não encontradas: {CREDENTIALS}\n"
            "Coloque o credentials.json da conta de serviço em e:/NJUD/"
        )

    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    _drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)
    return _drive_service


def _find_doc_id_by_name(doc_name: str) -> str | None:
    """
    Busca um Google Doc pelo nome exato (sem extensão) via Drive API.
    Retorna o fileId ou None se não encontrado.

    Não toca no arquivo local — necessário porque os .gdoc do Drive for
    Desktop são cloud-only e inacessíveis via leitura de arquivo Win32.
    """
    service = _get_drive_service()
    # Escapa aspas simples no nome (padrão da query language da Drive API)
    safe_name = doc_name.replace("'", "\\'")
    query = (
        f"name = '{safe_name}' "
        f"and mimeType = 'application/vnd.google-apps.document' "
        f"and trashed = false"
    )
    result = service.files().list(
        q=query,
        fields="files(id, name)",
        pageSize=5,
    ).execute()

    files = result.get("files", [])
    if files:
        return files[0]["id"]

    # Fallback: busca parcial (útil se o nome tiver espaços extras ou case diferente)
    safe_partial = doc_name.strip().replace("'", "\\'")
    query_partial = (
        f"name contains '{safe_partial[:40]}' "
        f"and mimeType = 'application/vnd.google-apps.document' "
        f"and trashed = false"
    )
    result2 = service.files().list(
        q=query_partial,
        fields="files(id, name)",
        pageSize=5,
    ).execute()
    files2 = result2.get("files", [])
    if files2:
        return files2[0]["id"]

    return None


def _export_gdoc(gdoc_path: str) -> str:
    """
    Exporta o Google Doc correspondente ao arquivo .gdoc como texto puro.

    Estratégia: usa o NOME do arquivo (sem extensão) para localizar o
    documento via Drive API — nunca abre o arquivo local, que é um
    cloud stub inacessível via Win32 no Google Drive for Desktop.

    Retorna o conteúdo (str) ou PLACEHOLDER em caso de falha.
    """
    try:
        from googleapiclient.http import MediaIoBaseDownload
    except ImportError:
        print("  ⚠️  google-api-python-client não instalado; usando placeholder.")
        return PLACEHOLDER

    # Nome do arquivo sem extensão → nome do Google Doc no Drive
    doc_name = pathlib.Path(gdoc_path).stem  # ex: "PROG GNC 87"

    try:
        service = _get_drive_service()
        doc_id  = _find_doc_id_by_name(doc_name)

        if not doc_id:
            print(f"  ⚠️  Documento não encontrado na Drive API: '{doc_name}'")
            return PLACEHOLDER

        request = service.files().export_media(fileId=doc_id, mimeType="text/plain")
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        content = buf.getvalue().decode("utf-8", errors="replace").strip()
        return content if content else PLACEHOLDER

    except Exception as exc:
        print(f"  ❌ Erro ao exportar '{os.path.basename(gdoc_path)}': {exc}")
        return PLACEHOLDER


# ---------------------------------------------------------------------------
# Leitura de roteiro (qualquer formato)
# ---------------------------------------------------------------------------

def read_roteiro(source_path: str) -> str:
    """
    Lê o texto do roteiro independente do formato (.txt / .docx / .gdoc).
    Retorna uma string com o conteúdo ou PLACEHOLDER.
    """
    ext = pathlib.Path(source_path).suffix.lower()

    if ext == ".txt":
        return pathlib.Path(source_path).read_text(encoding="utf-8", errors="replace")

    if ext == ".docx":
        try:
            from docx import Document
            doc = Document(source_path)
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as exc:
            print(f"  ⚠️  Erro ao ler .docx: {exc}")
            return PLACEHOLDER

    if ext == ".gdoc":
        print(f"  🌐 Exportando via Drive API: {os.path.basename(source_path)}")
        return _export_gdoc(source_path)

    print(f"  ⚠️  Formato não suportado: {ext}")
    return PLACEHOLDER


def save_txt(content: str, dest_dir: str, stem: str) -> str:
    """Grava o conteúdo em <dest_dir>/<stem>.txt e devolve o caminho."""
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, f"{stem}.txt")
    pathlib.Path(dest).write_text(content, encoding="utf-8")
    return dest


# ---------------------------------------------------------------------------
# Helpers MP3 / Roteiro (originais, sem alteração)
# ---------------------------------------------------------------------------

def is_mp3_file(fname: str) -> bool:
    return fname.lower().endswith(".mp3") and (
        fname.startswith("GNC") or fname.startswith("GC")
    )


def extract_info_2025(mp3_name: str):
    parts = mp3_name[:-4].split("-")
    if len(parts) >= 3:
        num = parts[1]
        try:
            date = datetime.datetime.strptime(parts[2], "%Y%m%d").date()
        except ValueError:
            date = parts[2]
        return num, str(date)
    return None, None


def extract_info_2026(mp3_name: str) -> str:
    base = mp3_name[:-4]
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return str(datetime.datetime.strptime(base.split("-")[-1], fmt).date())
        except Exception:
            pass
    nums = re.findall(r"\d+", base)
    if len(nums) >= 2:
        return f"2026{nums[1].zfill(2)}{nums[0].zfill(2)}"
    return "unknown"


def find_roteiro(folder_path: str) -> str | None:
    """
    Localiza o arquivo de roteiro na pasta do programa.

    Prioridade:
      1. Arquivo cujo nome contém "roteiro" (qualquer extensão suportada)
      2. Arquivo cujo nome contém "gnc", "giro" ou "prog" (o roteiro em si)
      3. Arquivo cujo nome contém "pauta" (alternativa)

    Extensões aceitas (ordem de preferência): .docx, .gdoc, .txt
    Arquivos com "links" no nome são ignorados.
    """
    candidates: list[tuple[int, str]] = []   # (prioridade, caminho)

    for fname in os.listdir(folder_path):
        flo = fname.lower()
        ext = pathlib.Path(flo).suffix

        if ext not in (".docx", ".gdoc", ".txt"):
            continue
        if "links" in flo:   # ignora arquivos de referências/links
            continue

        path = os.path.join(folder_path, fname)

        if "roteiro" in flo:
            candidates.append((0, path))
        elif any(k in flo for k in ("gnc", "giro", "prog")):
            candidates.append((1, path))
        elif "pauta" in flo:
            candidates.append((2, path))

    if not candidates:
        return None

    # Dentro da mesma prioridade, prefere .docx > .gdoc > .txt
    ext_order = {".docx": 0, ".gdoc": 1, ".txt": 2}
    candidates.sort(key=lambda t: (t[0], ext_order.get(pathlib.Path(t[1]).suffix.lower(), 9)))
    return candidates[0][1]


# ---------------------------------------------------------------------------
# Processamento por ano
# ---------------------------------------------------------------------------

def process_year(year: int) -> None:
    year_path = os.path.join(ROOT_DRIVE, str(year))
    report_lines: list[str] = []
    missing_2026: list[str] = []

    entries = sorted(os.listdir(year_path))
    total   = sum(1 for e in entries if os.path.isdir(os.path.join(year_path, e)))
    done    = 0

    for entry in entries:
        prog_dir = os.path.join(year_path, entry)
        if not os.path.isdir(prog_dir):
            continue

        done += 1
        mp3_files    = [f for f in os.listdir(prog_dir) if is_mp3_file(f)]
        roteiro_path = find_roteiro(prog_dir)
        roteiro_ok   = bool(roteiro_path)
        audio_ok     = bool(mp3_files)

        # ── 2025 ──────────────────────────────────────────────────────────
        if year == 2025:
            prog_num = entry
            date     = ""

            if audio_ok:
                _, date_extracted = extract_info_2025(mp3_files[0])
                if date_extracted:
                    date = date_extracted
                for mp3 in mp3_files:
                    src  = os.path.join(prog_dir, mp3)
                    dest = os.path.join(WORKSPACE, str(year), prog_num, mp3)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.copy2(src, dest)

            else:
                # Sem áudio → gera TXT para o TTS
                if roteiro_path:
                    print(f"[{done}/{total}] Prog {prog_num} — sem áudio, convertendo roteiro…")
                    content = read_roteiro(roteiro_path)
                    stem    = f"GNC-{prog_num.zfill(2)}-2025"
                    dest    = save_txt(content, TTS_DIR, stem)
                    status  = "✅ TXT gerado" if content != PLACEHOLDER else "⚠️  placeholder"
                    print(f"           {status}: {os.path.basename(dest)}")
                else:
                    print(f"[{done}/{total}] Prog {prog_num} — sem áudio e sem roteiro.")

            report_lines.append(
                f"| {prog_num} | {date} | {'✅' if roteiro_ok else '❌'} | {'✅' if audio_ok else '❌'} |"
            )

        # ── 2026 ──────────────────────────────────────────────────────────
        else:
            prog_num = entry

            if audio_ok:
                for mp3 in mp3_files:
                    src       = os.path.join(prog_dir, mp3)
                    date_part = extract_info_2026(mp3) or "unknown"
                    new_name  = f"GNC-{date_part}.mp3"
                    dest      = os.path.join(WORKSPACE, str(year), prog_num, new_name)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.copy2(src, dest)

            else:
                missing_2026.append(prog_num)
                if roteiro_path:
                    print(f"[{done}/{total}] 2026/{prog_num} — sem áudio, convertendo roteiro…")
                    content = read_roteiro(roteiro_path)
                    stem    = f"GNC-2026-{prog_num}"
                    dest    = save_txt(content, TTS_DIR, stem)
                    status  = "✅ TXT gerado" if content != PLACEHOLDER else "⚠️  placeholder"
                    print(f"           {status}: {os.path.basename(dest)}")
                else:
                    print(f"[{done}/{total}] 2026/{prog_num} — sem áudio e sem roteiro.")

    # ── Relatórios ────────────────────────────────────────────────────────
    if year == 2025:
        report_path = os.path.join(REPORTS_DIR, "relatorio_2025.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Relatório Giro nas Comarcas – 2025\n\n")
            f.write("| Programa | Data | Roteiro OK | Audio OK |\n|---|---|---|---|\n")
            f.writelines(line + "\n" for line in report_lines)
        print(f"\n📄 Relatório 2025 gravado: {report_path}")

    else:
        prod_path = os.path.join(REPORTS_DIR, "relatorio_2026.md")
        with open(prod_path, "w", encoding="utf-8") as f:
            f.write("# Relatório Produção Giro nas Comarcas – 2026\n\n")
            f.write("## Programas com áudio gerado\n")
            f.write("(arquivos .mp3 copiados para a estrutura de workspace)\n\n")
            f.write("## Programas faltando áudio\n")
            for prog in missing_2026:
                f.write(f"- {prog}\n")
        print(f"\n📄 Relatório 2026 gravado: {prod_path}")


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("  Auditoria — Giro nas Comarcas")
    print("=" * 60)
    os.makedirs(WORKSPACE, exist_ok=True)

    for year in (2025, 2026):
        year_path = os.path.join(ROOT_DRIVE, str(year))
        if not os.path.isdir(year_path):
            print(f"⚠️  Pasta {year} não encontrada: {year_path}")
            continue
        print(f"\n── Processando {year} ──────────────────────────────────")
        process_year(year)

    print("\n✅ Concluído.")
    print(f"   Relatórios : {REPORTS_DIR}")
    print(f"   TXTs (TTS) : {TTS_DIR}")


if __name__ == "__main__":
    main()
