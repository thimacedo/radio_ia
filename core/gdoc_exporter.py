"""
gdoc_exporter.py
----------------
Lê um arquivo .gdoc (ponteiro JSON do Google Drive para Desktop),
extrai o ID do documento e exporta o conteúdo como text/plain
usando a Google Drive API com credenciais de conta de serviço.

Uso direto:
    python gdoc_exporter.py caminho/para/arquivo.gdoc

Uso como módulo:
    from gdoc_exporter import export_gdoc_to_txt
    texto = export_gdoc_to_txt(Path("arquivo.gdoc"))
"""

from __future__ import annotations

import json
import logging
import re
import sys
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dependências externas — instale com:
#   & e:/NJUD/.venv/Scripts/python.exe -m pip install --upgrade \
#       google-api-python-client google-auth-httplib2 google-auth-oauthlib
# ---------------------------------------------------------------------------
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
except ImportError as exc:
    raise ImportError(
        "Bibliotecas do Google não encontradas.\n"
        "Execute:\n"
        "  & e:/NJUD/.venv/Scripts/python.exe -m pip install --upgrade "
        "google-api-python-client google-auth-httplib2 google-auth-oauthlib"
    ) from exc

# ---------------------------------------------------------------------------
# Configurações — ajuste se necessário
# ---------------------------------------------------------------------------
import sys
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))
from core.best_practices import carregar_env_var
CREDENTIALS_PATH = project_root / carregar_env_var("CREDENTIALS_PATH", "config/credentials/service_account.json")

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
]


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------

def _build_drive_service(credentials_path: Path):
    """Constrói o cliente autenticado da Google Drive API."""
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"Arquivo de credenciais não encontrado: {credentials_path}\n"
            "Coloque o credentials.json da conta de serviço em e:/NJUD/"
        )
    creds = service_account.Credentials.from_service_account_file(
        str(credentials_path), scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _extract_doc_id(gdoc_path: Path) -> str:
    """
    Lê o arquivo .gdoc e extrai o ID do Google Document.

    O arquivo .gdoc é um JSON com (pelo menos) dois campos:
        {
          "url": "https://docs.google.com/open?id=DOCUMENT_ID",
          "doc_id": "DOCUMENT_ID"
        }
    """
    raw = gdoc_path.read_text(encoding="utf-8", errors="replace")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Não foi possível interpretar {gdoc_path} como JSON: {exc}"
        ) from exc

    # Tenta o campo "doc_id" primeiro (mais direto)
    doc_id = data.get("doc_id") or data.get("docId")
    if doc_id:
        return doc_id.strip()

    # Alternativa: extrai o ID da URL
    url = data.get("url", "")
    # Padrões comuns:
    #   https://docs.google.com/open?id=XXXXX
    #   https://docs.google.com/document/d/XXXXX/edit
    match = re.search(r"[?&/](?:id=|d/)([a-zA-Z0-9_-]{25,})", url)
    if match:
        return match.group(1)

    raise ValueError(
        f"Não foi possível extrair o ID do documento em {gdoc_path}.\n"
        f"Conteúdo do arquivo: {raw[:300]}"
    )


def export_gdoc_to_txt(
    gdoc_path: Path,
    credentials_path: Path = CREDENTIALS_PATH,
    encoding: str = "utf-8",
    use_cache: bool = True,
    cache_ttl_s: int = 3600,
) -> str:
    """
    Exporta o Google Doc apontado pelo arquivo .gdoc como texto puro.

    Parâmetros
    ----------
    gdoc_path : Path
        Caminho para o arquivo .gdoc no disco.
    credentials_path : Path
        Caminho para o JSON de credenciais da conta de serviço.
    encoding : str
        Codificação usada para decodificar a resposta da API (padrão: utf-8).
    use_cache : bool
        Se True, verifica o DocCache antes de baixar (padrão: True).
    cache_ttl_s : int
        TTL do cache em segundos (padrão: 3600 = 1 hora).

    Retorna
    -------
    str
        Conteúdo textual do documento.

    Lança
    -----
    FileNotFoundError  — se o .gdoc ou o credentials.json não existirem.
    ValueError         — se o ID do documento não puder ser extraído.
    googleapiclient.errors.HttpError — se a API retornar erro (ex.: sem permissão).
    """
    gdoc_path = Path(gdoc_path)
    if not gdoc_path.exists():
        raise FileNotFoundError(f"Arquivo .gdoc não encontrado: {gdoc_path}")

    service = _build_drive_service(credentials_path)

    # Tenta extrair o ID do arquivo local
    doc_id = None
    try:
        doc_id = _extract_doc_id(gdoc_path)
    except Exception as exc:
        print(f"  [AVISO] Não foi possível ler o ID do arquivo local '{gdoc_path.name}': {exc}")
        print("  Tentando buscar o arquivo por nome no Google Drive via API...")

    if not doc_id:
        # Busca o ID por nome na API
        name = gdoc_path.name
        if name.lower().endswith(".gdoc"):
            name = name[:-5]

        query = f"name = '{name}' and mimeType = 'application/vnd.google-apps.document' and trashed = false"
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            pageSize=5
        ).execute()

        files = results.get('files', [])
        if files:
            doc_id = files[0]['id']
            print(f"  [OK] Encontrado ID na nuvem: {doc_id} para o arquivo '{name}'")
        else:
            raise ValueError(f"Não foi possível localizar o documento '{name}' no Google Drive via API.")

    # ----------------------------------------------------------------
    # Cache hit: retorna conteúdo salvo sem consumir quota da API
    # ----------------------------------------------------------------
    if use_cache:
        try:
            from core.doc_cache import DocCache
            _cache = DocCache(default_ttl_s=cache_ttl_s)
            cached = _cache.get(doc_id, max_age_s=cache_ttl_s)
            if cached is not None:
                logger.info("[DocCache] HIT para doc_id=%s — usando conteúdo em cache.", doc_id)
                return cached
        except Exception as cache_err:
            logger.warning("[DocCache] Falha ao ler cache (continuando sem cache): %s", cache_err)
            _cache = None
    else:
        _cache = None

    # ----------------------------------------------------------------
    # Cache miss: exporta o documento como texto puro via API
    # ----------------------------------------------------------------
    request = service.files().export_media(
        fileId=doc_id,
        mimeType="text/plain",
    )

    # Usa um arquivo temporário para receber o stream
    with tempfile.TemporaryFile() as tmp:
        downloader = MediaIoBaseDownload(tmp, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        tmp.seek(0)
        content = tmp.read().decode(encoding, errors="replace")

    # Salva no cache para próximas requisições
    if _cache is not None:
        try:
            _cache.set(doc_id, content, ttl_s=cache_ttl_s)
            logger.info("[DocCache] MISS — conteúdo salvo no cache (doc_id=%s).", doc_id)
        except Exception as cache_save_err:
            logger.warning("[DocCache] Falha ao salvar no cache: %s", cache_save_err)

    return content


# ---------------------------------------------------------------------------
# Execução direta (teste rápido)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python gdoc_exporter.py <arquivo.gdoc>")
        sys.exit(1)

    target = Path(sys.argv[1])
    try:
        texto = export_gdoc_to_txt(target)
        print(f"✅ Documento exportado com sucesso ({len(texto)} caracteres).")
        print("-" * 60)
        print(texto[:500])  # Exibe os primeiros 500 caracteres como prévia
    except Exception as e:
        print(f"❌ Erro: {e}", file=sys.stderr)
        sys.exit(1)
