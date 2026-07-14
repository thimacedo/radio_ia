# -*- coding: utf-8 -*-
"""
core/doc_cache.py
-----------------
Cache SQLite para conteúdo de Google Docs baixados.

O agente baixa o mesmo roteiro do Drive toda vez que roda. Este cache
armazena o conteúdo com TTL de 1 hora (3600s), eliminando chamadas
redundantes à API do Google.

Uso:
    from core.doc_cache import DocCache

    cache = DocCache()

    # Tentar ler do cache (válido por 1h)
    texto = cache.get("doc_id_abc123")
    if texto is None:
        texto = baixar_do_drive("doc_id_abc123")  # sua função real
        cache.set("doc_id_abc123", texto)          # salva no cache

    # Forçar re-download (invalida o cache)
    cache.invalidate("doc_id_abc123")

    # Limpar entradas expiradas (pode ser chamado periodicamente)
    cache.cleanup()
"""

from __future__ import annotations

import sqlite3
import time
import pathlib
import logging
from typing import Optional

# Logger silencioso para não poluir o output
_logger = logging.getLogger("doc_cache")
_logger.setLevel(logging.WARNING)


class DocCache:
    """
    Cache SQLite para textos de Google Docs.

    Parâmetros
    ----------
    db_path : str | pathlib.Path
        Caminho do arquivo SQLite. Padrão: data/doc_cache.db
    ttl_seconds : int
        Tempo de vida de cada entrada em segundos. Padrão: 3600 (1 hora).
    """

    def __init__(
        self,
        db_path: str | pathlib.Path = "data/doc_cache.db",
        ttl_seconds: int = 3600,
    ):
        self.db_path = pathlib.Path(db_path)
        self.ttl = ttl_seconds

        # Garante que o diretório data/ existe
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._con: Optional[sqlite3.Connection] = None
        self._init_db()

    # ─── Private ──────────────────────────────────────────────────────────────

    def _get_con(self) -> sqlite3.Connection:
        if self._con is None:
            self._con = sqlite3.connect(
                str(self.db_path),
                timeout=10.0,
                isolation_level="IMMEDIATE",
            )
            self._con.execute("PRAGMA journal_mode=WAL")
        return self._con

    def _init_db(self):
        """Cria a tabela de cache se não existir."""
        con = self._get_con()
        con.execute("""
            CREATE TABLE IF NOT EXISTS doc_cache (
                doc_id    TEXT PRIMARY KEY,
                conteudo  TEXT,
                ts        REAL
            )
        """)
        con.execute("""
            CREATE INDEX IF NOT EXISTS idx_ts ON doc_cache(ts)
        """)
        con.commit()

    # ─── Public API ───────────────────────────────────────────────────────────

    def get(self, doc_id: str, max_age_s: int | None = None) -> Optional[str]:
        """
        Retorna o conteúdo em cache se existir e não estiver expirado.

        Parâmetros
        ----------
        doc_id : str
            ID do documento do Google.
        max_age_s : int | None
            Idade máxima aceita em segundos. Usa o TTL do construtor se None.

        Retorna
        -------
        str | None
            O conteúdo cacheado, ou None se não encontrado/expirado.
        """
        if max_age_s is None:
            max_age_s = self.ttl

        con = self._get_con()
        row = con.execute(
            "SELECT conteudo, ts FROM doc_cache WHERE doc_id = ?",
            (doc_id,),
        ).fetchone()

        if row is None:
            _logger.debug(f"[DocCache] MISS  {doc_id}")
            return None

        conteudo, ts = row
        idade = time.time() - ts
        if idade > max_age_s:
            _logger.debug(f"[DocCache] EXPIRED {doc_id} ({idade:.0f}s)")
            return None

        _logger.debug(f"[DocCache] HIT   {doc_id} (idade {idade:.0f}s)")
        return conteudo

    def set(self, doc_id: str, conteudo: str):
        """
        Armazena (ou atualiza) o conteúdo de um documento no cache.

        Parâmetros
        ----------
        doc_id : str
            ID do documento.
        conteudo : str
            Texto completo do documento.
        """
        con = self._get_con()
        con.execute(
            "INSERT OR REPLACE INTO doc_cache (doc_id, conteudo, ts) VALUES (?, ?, ?)",
            (doc_id, conteudo, time.time()),
        )
        con.commit()
        _logger.debug(f"[DocCache] SET   {doc_id} ({len(conteudo)} chars)")

    def invalidate(self, doc_id: str):
        """
        Remove uma entrada específica do cache.

        Útil quando você sabe que o documento foi editado no Drive
        e precisa forçar um re-download.
        """
        con = self._get_con()
        con.execute("DELETE FROM doc_cache WHERE doc_id = ?", (doc_id,))
        con.commit()
        _logger.debug(f"[DocCache] INVALIDATE {doc_id}")

    def cleanup(self, max_age_s: int | None = None) -> int:
        """
        Remove entradas expiradas do cache.

        Parâmetros
        ----------
        max_age_s : int | None
            Remove apenas entradas mais velhas que este valor.
            Usa o TTL do construtor se None.

        Retorna
        -------
        int
            Número de entradas removidas.
        """
        if max_age_s is None:
            max_age_s = self.ttl

        cutoff = time.time() - max_age_s
        con = self._get_con()
        cur = con.execute(
            "DELETE FROM doc_cache WHERE ts < ?",
            (cutoff,),
        )
        con.commit()
        removed = cur.rowcount
        if removed:
            _logger.info(f"[DocCache] Cleanup: {removed} entrada(s) removida(s).")
        return removed

    def stats(self) -> dict:
        """
        Retorna estatísticas do cache.

        Retorna
        -------
        dict
            keys: total_entries, expired_entries, oldest_ts, newest_ts
        """
        con = self._get_con()
        now = time.time()
        cutoff = now - self.ttl

        total = con.execute("SELECT COUNT(*) FROM doc_cache").fetchone()[0]
        expired = con.execute(
            "SELECT COUNT(*) FROM doc_cache WHERE ts < ?", (cutoff,)
        ).fetchone()[0]

        oldest = con.execute(
            "SELECT MIN(ts) FROM doc_cache"
        ).fetchone()[0]
        newest = con.execute(
            "SELECT MAX(ts) FROM doc_cache"
        ).fetchone()[0]

        return {
            "total_entries": total,
            "expired_entries": expired,
            "active_entries": total - expired,
            "oldest_ts": oldest,
            "newest_ts": newest,
            "db_path": str(self.db_path),
        }

    def close(self):
        """Fecha a conexão com o banco."""
        if self._con:
            self._con.close()
            self._con = None


# ─── Instância global com TTL padrão ─────────────────────────────────────────

#: Cache global compartilhado por todas as chamadas neste processo.
_global_cache: Optional[DocCache] = None


def get_cache(
    db_path: str | pathlib.Path = "data/doc_cache.db",
    ttl_seconds: int = 3600,
) -> DocCache:
    """Retorna (e cria se necessário) a instância global de cache."""
    global _global_cache
    if _global_cache is None:
        _global_cache = DocCache(db_path=db_path, ttl_seconds=ttl_seconds)
    return _global_cache
