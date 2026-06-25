"""
core/doc_cache.py
-----------------
Cache local de documentos do Google Drive baseado em SQLite.
Evita downloads repetidos do mesmo roteiro dentro da janela TTL configurada.

Uso:
    from core.doc_cache import DocCache
    cache = DocCache()
    conteudo = cache.get(doc_id)          # None se não cacheado ou expirado
    cache.set(doc_id, conteudo_do_doc)    # Salva no cache
    cache.invalidate(doc_id)              # Remove entrada específica
    cache.purge_expired()                 # Remove todas entradas expiradas
"""
import hashlib
import sqlite3
import time
import pathlib
from typing import Optional

DB_PATH = pathlib.Path(__file__).parent.parent / "data" / "doc_cache.db"


class DocCache:
    """
    Cache SQLite de conteúdo de documentos do Google Drive.

    Args:
        db_path: Caminho para o arquivo SQLite (padrão: data/doc_cache.db).
        default_ttl_s: Tempo de vida da entrada em segundos (padrão: 3600 = 1 hora).
    """

    def __init__(self, db_path: pathlib.Path = DB_PATH, default_ttl_s: int = 3600):
        self.db_path = pathlib.Path(db_path)
        self.default_ttl_s = default_ttl_s
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.db_path)) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS doc_cache (
                    doc_id      TEXT PRIMARY KEY,
                    conteudo    TEXT NOT NULL,
                    md5         TEXT NOT NULL,
                    ts_criado   REAL NOT NULL,
                    ts_expira   REAL NOT NULL
                )
            """)
            con.commit()

    # ------------------------------------------------------------------
    # API Pública
    # ------------------------------------------------------------------

    def get(self, doc_id: str, max_age_s: Optional[int] = None) -> Optional[str]:
        """
        Retorna o conteúdo em cache se válido, ou None se ausente/expirado.

        Args:
            doc_id: Identificador único do documento (Google Docs ID ou URL).
            max_age_s: TTL personalizado para esta consulta. Usa default_ttl_s se None.
        """
        ttl = max_age_s if max_age_s is not None else self.default_ttl_s
        agora = time.time()
        limite = agora - ttl

        with sqlite3.connect(str(self.db_path)) as con:
            row = con.execute(
                "SELECT conteudo, ts_criado FROM doc_cache WHERE doc_id = ?",
                (doc_id,)
            ).fetchone()

        if row is None:
            return None

        conteudo, ts_criado = row
        if ts_criado < limite:
            # Entrada expirada — remove silenciosamente
            self.invalidate(doc_id)
            return None

        return conteudo

    def set(self, doc_id: str, conteudo: str, ttl_s: Optional[int] = None) -> None:
        """
        Armazena ou atualiza o conteúdo de um documento no cache.

        Args:
            doc_id: Identificador único do documento.
            conteudo: Texto completo do documento.
            ttl_s: Tempo de vida personalizado em segundos. Usa default_ttl_s se None.
        """
        ttl = ttl_s if ttl_s is not None else self.default_ttl_s
        agora = time.time()
        md5 = hashlib.md5(conteudo.encode("utf-8")).hexdigest()

        with sqlite3.connect(str(self.db_path)) as con:
            con.execute(
                """
                INSERT INTO doc_cache (doc_id, conteudo, md5, ts_criado, ts_expira)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    conteudo  = excluded.conteudo,
                    md5       = excluded.md5,
                    ts_criado = excluded.ts_criado,
                    ts_expira = excluded.ts_expira
                """,
                (doc_id, conteudo, md5, agora, agora + ttl)
            )
            con.commit()

    def has_changed(self, doc_id: str, novo_conteudo: str) -> bool:
        """
        Verifica se o conteúdo de um documento mudou em relação ao último cache.
        Útil para evitar reprocessamento desnecessário.
        """
        md5_novo = hashlib.md5(novo_conteudo.encode("utf-8")).hexdigest()
        with sqlite3.connect(str(self.db_path)) as con:
            row = con.execute(
                "SELECT md5 FROM doc_cache WHERE doc_id = ?", (doc_id,)
            ).fetchone()
        if row is None:
            return True  # não existe → considera changed
        return row[0] != md5_novo

    def invalidate(self, doc_id: str) -> None:
        """Remove uma entrada específica do cache."""
        with sqlite3.connect(str(self.db_path)) as con:
            con.execute("DELETE FROM doc_cache WHERE doc_id = ?", (doc_id,))
            con.commit()

    def purge_expired(self) -> int:
        """Remove todas as entradas expiradas. Retorna o número de linhas removidas."""
        agora = time.time()
        with sqlite3.connect(str(self.db_path)) as con:
            cur = con.execute(
                "DELETE FROM doc_cache WHERE ts_expira < ?", (agora,)
            )
            con.commit()
            return cur.rowcount

    def stats(self) -> dict:
        """Retorna estatísticas do cache para monitoramento."""
        agora = time.time()
        with sqlite3.connect(str(self.db_path)) as con:
            total = con.execute("SELECT COUNT(*) FROM doc_cache").fetchone()[0]
            ativos = con.execute(
                "SELECT COUNT(*) FROM doc_cache WHERE ts_expira >= ?", (agora,)
            ).fetchone()[0]
        return {"total": total, "ativos": ativos, "expirados": total - ativos}
