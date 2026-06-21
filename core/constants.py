# -*- coding: utf-8 -*-
"""
Constantes centralizadas para o sistema Rádio IA TJRN.
Substitui duplicações em: agente_ia.py, gerar_njud_tts.py, gerar_locucao_giro_premium.py,
boletins_pipeline.py, giro_pipeline.py, sincronizar_boletins_drive.py.

Uso:
    from core.constants import (
        MONTH_MAP_SHORT, MONTH_MAP_FULL, WEEKDAYS_PT,
        folder_name_5s, obter_dia_semana_pt, ANO_PRODUCAO, ANO_SHORT
    )
"""

from __future__ import annotations

import datetime

# ──────────────────────────────────────────────────────────────────────────────
# Data / Calendário
# ──────────────────────────────────────────────────────────────────────────────

MONTH_MAP_SHORT: dict[int, str] = {
    1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR", 5: "MAI", 6: "JUN",
    7: "JUL", 8: "AGO", 9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ",
}

MONTH_MAP_FULL: dict[int, str] = {
    1: "1 - JANEIRO",
    2: "2 - FEVEREIRO",
    3: "3 - MARÇO",
    4: "4 - ABRIL",
    5: "5 - MAIO",
    6: "6 - JUNHO",
    7: "7 - JULHO",
    8: "8 - AGOSTO",
    9: "9 - SETEMBRO",
    10: "10 - OUTUBRO",
    11: "11 - NOVEMBRO",
    12: "12 - DEZEMBRO",
}

WEEKDAYS_PT: dict[int, str] = {
    0: "SEG",  # Segunda
    1: "TER",  # Terça
    2: "QUA",  # Quarta
    3: "QUI",  # Quinta
    4: "SEX",  # Sexta
    5: "SAB",  # Sábado
    6: "DOM",  # Domingo
}

# ──────────────────────────────────────────────────────────────────────────────
# Ano de produção (automático — não hardcoded)
# ──────────────────────────────────────────────────────────────────────────────

ANO_PRODUCAO: int = datetime.datetime.now().year          # ex: 2026
ANO_SHORT: str = str(ANO_PRODUCAO)[-2:]                 # ex: "26"

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def folder_name_5s(mes_num: int, ano_short: str | None = None) -> str:
    """
    Retorna o nome padronizado de pasta no formato 5S.
    Exemplo: folder_name_5s(6) → "06 - JUN - 26"
    """
    if ano_short is None:
        ano_short = ANO_SHORT
    short = MONTH_MAP_SHORT.get(mes_num, "JUN")
    return f"{mes_num:02d} - {short} - {ano_short}"


def obter_dia_semana_pt(ano: int, mes: int, dia: int) -> str:
    """Retorna o dia da semana em português. Ex: 'SEG', 'TER'."""
    try:
        return WEEKDAYS_PT[datetime.datetime(ano, mes, dia).weekday()]
    except Exception:
        return "SEG"


def obter_mes_por_nome(nome: str) -> int | None:
    """
    Dado um nome de mês (ex: 'junho', '6', '6 - JUNHO'), retorna o número.
    Retorna None se não reconhecer.
    """
    nome = nome.strip().upper()

    # Número puro: "6", "06"
    import re as _re
    m_num = _re.match(r"^(\d{1,2})$", nome)
    if m_num:
        val = int(m_num.group(1))
        if 1 <= val <= 12:
            return val

    # "6 - JUNHO" / "JUNHO" / "JUN"
    for num, short in MONTH_MAP_SHORT.items():
        if short in nome:
            return num
    for num, full in MONTH_MAP_FULL.items():
        if full.upper() in nome or nome in full.upper():
            return num

    return None


def extrair_mes_num_de_caminho(caminho: str) -> int:
    """
    Tenta extrair o número do mês de uma string de caminho ou referência.
    Fallback: retorna o mês atual.
    """
    import re as _re
    m = _re.search(r"(\d{4})[-/](\d{2})[-/]", caminho)
    if m:
        return int(m.group(2))
    m2 = _re.search(r"(\d{2})[-/](\d{4})", caminho)
    if m2:
        return int(m2.group(1))
    m3 = _re.search(r"\b(\d{1,2})\b", caminho)
    if m3:
        val = int(m3.group(1))
        if 1 <= val <= 12:
            return val
    return datetime.datetime.now().month
