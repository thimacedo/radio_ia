import sqlite3
import time
import os
import pathlib

DB_PATH = pathlib.Path(__file__).parent.parent / "data" / "execucoes.db"

def inicializar_db():
    """Inicializa o banco de dados SQLite e cria as tabelas de observabilidade."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execucoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_inicio REAL NOT NULL,
                ts_fim REAL,
                pipeline TEXT NOT NULL,
                status TEXT NOT NULL,
                duracao_audio_s REAL DEFAULT 0.0,
                erro_msg TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()

def registrar_inicio(pipeline: str) -> int:
    """Registra o início de uma execução de pipeline e retorna seu ID."""
    inicializar_db()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cursor = conn.cursor()
        ts_inicio = time.time()
        cursor.execute(
            "INSERT INTO execucoes (ts_inicio, pipeline, status) VALUES (?, ?, ?)",
            (ts_inicio, pipeline, "executando")
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def registrar_fim(exec_id: int, status: str, duracao_audio_s: float = 0.0, erro_msg: str = None):
    """Registra o encerramento de um pipeline (sucesso ou falha)."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cursor = conn.cursor()
        ts_fim = time.time()
        cursor.execute(
            """
            UPDATE execucoes 
            SET ts_fim = ?, status = ?, duracao_audio_s = ?, erro_msg = ?
            WHERE id = ?
            """,
            (ts_fim, status, duracao_audio_s, erro_msg, exec_id)
        )
        conn.commit()
    finally:
        conn.close()
