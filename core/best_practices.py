import asyncio
import time
import functools
import os
import json
import re

# Centralized Calendar/Formatting Constants
MONTH_MAP_SHORT = {
    1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR", 5: "MAI", 6: "JUN",
    7: "JUL", 8: "AGO", 9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ"
}

MONTH_MAP_FULL = {
    1: "1 - JANEIRO", 2: "2 - FEVEREIRO", 3: "3 - MARÇO", 4: "4 - ABRIL",
    5: "5 - MAIO",    6: "6 - JUNHO",     7: "7 - JULHO",  8: "8 - AGOSTO",
    9: "9 - SETEMBRO", 10: "10 - OUTUBRO", 11: "11 - NOVEMBRO", 12: "12 - DEZEMBRO"
}

WEEKDAYS_PT = {0: "SEG", 1: "TER", 2: "QUA", 3: "QUI", 4: "SEX", 5: "SAB", 6: "DOM"}

def retry_async(retries: int = 3, backoff: float = 0.5, exceptions: tuple = (Exception,)):
    """Retry decorator for async functions.
    Parameters
    ----------
    retries: int
        Number of attempts.
    backoff: float
        Base backoff in seconds; exponential backoff applied.
    exceptions: tuple
        Exceptions that trigger a retry.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kw):
            attempt = 0
            while True:
                try:
                    return await func(*args, **kw)
                except exceptions as e:
                    attempt += 1
                    if attempt > retries:
                        raise
                    wait = backoff * (2 ** (attempt - 1))
                    print(f"[WARN] {func.__name__} failed ({e}). Retrying {attempt}/{retries} after {wait}s...")
                    await asyncio.sleep(wait)
        return wrapper
    return decorator

def aplicar_pronuncia(texto: str) -> str:
    """Substitui siglas e palavras no texto por suas representações fonéticas
    definidas em data/pronunciation_rules.json.
    """
    core_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(core_dir)
    caminho_json = os.path.join(project_root, "data", "pronunciation_rules.json").replace("\\", "/")
    
    if not os.path.exists(caminho_json):
        return texto
        
    try:
        with open(caminho_json, "r", encoding="utf-8") as f:
            regras = json.load(f)
    except Exception as e:
        print(f"[WARN] Erro ao ler dicionário de pronúncia: {e}")
        return texto

    # Filtrar chaves especiais e vazias
    dicionario = {}
    for k, v in regras.items():
        if k.startswith("__") or k.startswith("==") or not v:
            continue
        dicionario[k] = v

    # Substituição usando regex de palavra inteira (\b)
    # Ordenar por tamanho decrescente para evitar substituições parciais
    chaves_ordenadas = sorted(dicionario.keys(), key=len, reverse=True)
    
    for sigla in chaves_ordenadas:
        pronuncia = dicionario[sigla]
        padrao = re.compile(rf"\b{re.escape(sigla)}\b")
        texto = padrao.sub(pronuncia, texto)
        
    return texto

def carregar_env_var(chave: str, fallback: str = "") -> str:
    """Lê uma variável de ambiente do arquivo .env com fallback do valor padrão."""
    core_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(core_dir)
    env_path = os.path.join(project_root, ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.split("=", 1)
                        if k.strip() == chave:
                            return v.strip().replace('"', '').replace("'", "")
        except Exception as e:
            print(f"[WARN] Falha ao ler variável {chave} do .env: {e}")
    return fallback
