"""
processar_roteiro_completo.py
─────────────────────────────
Versão **sem IA** do processador de roteiros.

Lê os TXT originais do Drive (ou pasta local), aplica regras de parsing
puramente baseadas em regex e produz TXT formatados com Speaker 1 / Speaker 2
prontos para o gerador de áudio (gerar_locucao_multi_speaker.py / agente_njud.py).

Diferença da versão resumida:
  • NÃO corta OFF / NOTA — mantém o roteiro completo.
  • NÃO usa API de IA — tudo é regex + dicionário.
  • Converte números, valores (R$), datas e siglas para extenso automaticamente.
"""

import os
import re
import sys
import argparse
import json

# ─────────────────────────────────────────────
# CONFIGURAÇÃO PADRÃO
# ─────────────────────────────────────────────

DEFAULT_SRC = r"H:\Meu Drive\RADIO TJRN CONTEÚDO\NOT JUDICIARIO (5 MIN)\NJUD 2026\Roteiros TXT Original"
DEFAULT_DEST = r"e:\NJUD\roteiros_processados"
DEFAULT_YEAR = 2026

# ─────────────────────────────────────────────
# CONVERSÃO DE NÚMEROS PARA EXTENSO
# ─────────────────────────────────────────────

_UNIDADES = [
    "", "um", "dois", "três", "quatro", "cinco",
    "seis", "sete", "oito", "nove", "dez",
    "onze", "doze", "treze", "quatorze", "quinze",
    "dezesseis", "dezessete", "dezoito", "dezenove",
]
_DEZENAS = [
    "", "", "vinte", "trinta", "quarenta", "cinquenta",
    "sessenta", "setenta", "oitenta", "noventa",
]
_CENTENAS = [
    "", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos",
    "seiscentos", "setecentos", "oitocentos", "novecentos",
]

def _numero_por_extenso_0_999(n: int) -> str:
    if n == 0:
        return "zero"
    if n == 100:
        return "cem"
    partes = []
    c = n // 100
    d = (n % 100) // 10
    u = n % 10
    if c:
        partes.append(_CENTENAS[c])
    if n % 100 < 20 and n % 100 > 0:
        partes.append(_UNIDADES[n % 100])
    else:
        if d:
            partes.append(_DEZENAS[d])
        if u:
            partes.append(_UNIDADES[u])
    return " e ".join(partes)


def numero_por_extenso(n: int) -> str:
    """Converte inteiros de 0 a 999.999.999 para português por extenso."""
    if n == 0:
        return "zero"
    if n < 0:
        return "menos " + numero_por_extenso(-n)

    partes = []
    # milhões
    milhoes = n // 1_000_000
    resto = n % 1_000_000
    milhares = resto // 1_000
    centenas = resto % 1_000

    if milhoes == 1:
        partes.append("um milhão")
    elif milhoes > 1:
        partes.append(_numero_por_extenso_0_999(milhoes) + " milhões")

    if milhares == 1:
        partes.append("mil")
    elif milhares > 1:
        partes.append(_numero_por_extenso_0_999(milhares) + " mil")

    if centenas > 0:
        partes.append(_numero_por_extenso_0_999(centenas))

    return " e ".join(partes) if len(partes) <= 2 else ", ".join(partes[:-1]) + " e " + partes[-1]


# ─────────────────────────────────────────────
# CONVERSÃO DE VALORES MONETÁRIOS
# ─────────────────────────────────────────────

def _converter_reais(match) -> str:
    """Callback para re.sub — converte 'R$ 58.808,00' → 'cinquenta e oito mil oitocentos e oito reais'."""
    raw = match.group(0)
    # Limpar
    raw = raw.replace("R$", "").strip()
    raw = raw.replace(".", "")  # separador de milhar
    partes = raw.split(",")
    inteiro = int(partes[0]) if partes[0] else 0
    centavos = int(partes[1]) if len(partes) > 1 and partes[1] else 0

    txt = numero_por_extenso(inteiro)
    if inteiro == 1:
        txt += " real"
    elif inteiro > 1:
        txt += " reais"

    if centavos:
        txt += " e " + numero_por_extenso(centavos)
        txt += " centavo" if centavos == 1 else " centavos"
    return txt


# ─────────────────────────────────────────────
# MESES
# ─────────────────────────────────────────────

MESES_EXTENSO = {
    "01": "janeiro", "02": "fevereiro", "03": "março", "04": "abril",
    "05": "maio", "06": "junho", "07": "julho", "08": "agosto",
    "09": "setembro", "10": "outubro", "11": "novembro", "12": "dezembro",
    "1": "janeiro", "2": "fevereiro", "3": "março", "4": "abril",
    "5": "maio", "6": "junho", "7": "julho", "8": "agosto",
    "9": "setembro", "10": "outubro", "11": "novembro", "12": "dezembro",
}

MESES_NOME_PARA_NUM = {
    "janeiro": "01", "fevereiro": "02", "março": "03", "marco": "03",
    "abril": "04", "maio": "05", "junho": "06", "julho": "07",
    "agosto": "08", "setembro": "09", "outubro": "10", "novembro": "11",
    "dezembro": "12",
}


def _converter_data_inline(match) -> str:
    """Converte datas como 04/05, 16/04/2026 para extenso."""
    raw = match.group(0).strip()
    partes = re.split(r"[/\-]", raw)
    dia = int(partes[0])
    mes_raw = partes[1].lower() if len(partes) > 1 else ""
    mes_nome = MESES_EXTENSO.get(mes_raw, MESES_NOME_PARA_NUM.get(mes_raw, mes_raw))
    if not mes_nome:
        return raw
    ano = ""
    if len(partes) == 3:
        ano_num = int(partes[2])
        ano = " de " + numero_por_extenso(ano_num)
    return f"{numero_por_extenso(dia)} de {mes_nome}{ano}"


# ─────────────────────────────────────────────
# CONVERSÃO DE NÚMEROS SOLTOS NO TEXTO
# ─────────────────────────────────────────────

def _converter_numero_solto(match) -> str:
    """Converte números isolados (ex: '0 km' → 'zero quilômetro')."""
    return numero_por_extenso(int(match.group(0)))


def _converter_percentual(match) -> str:
    raw = match.group(1).replace(".", "").replace(",", " vírgula ")
    # Se era inteiro puro, converter
    try:
        n = int(match.group(1).replace(".", ""))
        return numero_por_extenso(n) + " por cento"
    except ValueError:
        return raw + " por cento"


# ─────────────────────────────────────────────
# CONVERSÃO DE NÚMEROS ORDINAIS
# ─────────────────────────────────────────────

_ORDINAIS_MASC = {
    1: "primeiro", 2: "segundo", 3: "terceiro", 4: "quarto", 5: "quinto",
    6: "sexto", 7: "sétimo", 8: "oitavo", 9: "nono",
    10: "décimo", 20: "vigésimo", 30: "trigésimo", 40: "quadragésimo",
    50: "quinquagésimo", 60: "sexagésimo", 70: "septuagésimo",
    80: "octogésimo", 90: "nonagésimo",
    100: "centésimo", 200: "duzentésimo", 300: "trezentésimo",
    400: "quadringentésimo", 500: "quingentésimo", 600: "sexcentésimo",
    700: "septingentésimo", 800: "octingentésimo", 900: "nongentésimo"
}

_ORDINAIS_FEM = {
    1: "primeira", 2: "segunda", 3: "terceira", 4: "quarta", 5: "quinta",
    6: "sexta", 7: "sétima", 8: "oitava", 9: "nona",
    10: "décima", 20: "vigésima", 30: "trigésima", 40: "quadragésima",
    50: "quinquagésima", 60: "sexagésima", 70: "septuagésima",
    80: "octogésima", 90: "nonagésima",
    100: "centésima", 200: "duzentésima", 300: "trezentésima",
    400: "quadringentésima", 500: "quingentésima", 600: "sexcentésima",
    700: "septingentésima", 800: "octingentésima", 900: "nongentésima"
}

def ordinal_por_extenso(n: int, feminino: bool = False) -> str:
    """Converte inteiros de 1 a 999 para ordinais por extenso em português."""
    if n <= 0 or n > 999:
        return str(n) + ("ª" if feminino else "º")
    
    dicionario = _ORDINAIS_FEM if feminino else _ORDINAIS_MASC
    
    if n in dicionario:
        return dicionario[n]
        
    partes = []
    c = (n // 100) * 100
    d = ((n % 100) // 10) * 10
    u = n % 10
    
    if c:
        partes.append(dicionario[c])
    if d:
        partes.append(dicionario[d])
    if u:
        partes.append(dicionario[u])
        
    return " ".join(partes)

def _converter_ordinal(match) -> str:
    num = int(match.group(1))
    simbolo = match.group(2)
    feminino = (simbolo == "ª")
    return ordinal_por_extenso(num, feminino)


# ─────────────────────────────────────────────
# SIGLAS
# ─────────────────────────────────────────────

def _soletra_sigla(match) -> str:
    """Converte siglas de 2-5 letras maiúsculas para soletração (ex: TJRN → t j r n)."""
    sigla = match.group(0)
    # Não soletra palavras comuns que são grafadas em maiúsculas
    # Somente soletra siglas conhecidas ou de exatamente 2-4 letras maiúsculas
    # que NÃO sejam palavras comuns em português
    SIGLAS_CONHECIDAS = {
        "TJRN", "STF", "STJ", "TSE", "TJ", "OAB", "IPVA", "IPTU",
        "CPF", "CNPJ", "RG", "MP", "INSS", "FGTS", "SUS", "CNJ",
        "DPVAT", "TRF", "TRE", "TST", "TRT", "PF", "PC", "PM",
    }
    if sigla in SIGLAS_CONHECIDAS:
        return " ".join(c.lower() for c in sigla)
    # Não soletra — devolve como está
    return sigla


# ─────────────────────────────────────────────
# MARCADORES TÉCNICOS A REMOVER
# ─────────────────────────────────────────────

MARCADORES_IGNORAR = re.compile(
    r"^\s*("
    r"SOBE\s+TRILHA['\s]*|"
    r"QDA\s*|"
    r"TEMPO\s+M[AÁ]X.*|"
    r"NOT[IÍ]CIAS\s+DO\s+JUDICI[AÁ]RIO\s*|"
    r"PROGRAMA\s+N[ºO°]\s*\d+.*|"
    r"ENCERRAMENTO\s*|"
    r"ENC\s*"
    r")\s*$",
    re.IGNORECASE
)

MARCADOR_CABECALHO_PROGRAMA = re.compile(
    r"PROGRAMA\s+N[ºO°]\s*(\d+)\s*\(?\s*(\d{1,2})\s*[/\-]\s*(\d{1,2})\s*\)?",
    re.IGNORECASE
)


# ─────────────────────────────────────────────
# PARSER PRINCIPAL
# ─────────────────────────────────────────────

def limpar_texto_locutor(texto: str) -> str:
    """Aplica todas as conversões de locução ao texto de uma fala."""
    # 0. Normalizar caixa alta pura → capitalização normal
    #    Se a linha inteira (ou quase) está em MAIÚSCULAS, converter para sentença
    palavras = texto.split()
    maiusculas = sum(1 for p in palavras if p.isupper() and len(p) > 1)
    if len(palavras) > 2 and maiusculas / len(palavras) > 0.5:
        texto = texto.capitalize()
        # Recapitalizar após pontuação
        texto = re.sub(r'([.!?]\s+)(\w)', lambda m: m.group(1) + m.group(2).upper(), texto)

    # 1. Remover barras duplas → ponto (pausa longa)
    texto = re.sub(r"\s*//\s*", ". ", texto)
    # 2. Remover barra simples → vírgula (micro-pausa)
    texto = re.sub(r"\s*/\s*", ", ", texto)
    # 3. Converter URLs para forma falada
    texto = re.sub(r"(?:https?://)?(?:www\.)?tjrn\.jus\.br", "t j r n ponto jus ponto b r", texto, flags=re.IGNORECASE)
    texto = re.sub(r"(?:https?://)?(?:www\.)?(\w+)\.com\.br", r"\1 ponto com ponto b r", texto, flags=re.IGNORECASE)
    texto = re.sub(r"(?:https?://)?(?:www\.)?(\w+)\.com", r"\1 ponto com", texto, flags=re.IGNORECASE)
    # 4. Converter menções de redes sociais (@handle)
    texto = re.sub(r"@tjrnoficial", "arroba t j r n oficial", texto, flags=re.IGNORECASE)
    texto = re.sub(r"@tjrnnoticias", "arroba t j r n notícias", texto, flags=re.IGNORECASE)
    texto = re.sub(r"@tjrn", "arroba t j r n", texto, flags=re.IGNORECASE)
    texto = re.sub(r"@(\w+)", r"arroba \1", texto)
    # 5. Converter valores monetários: R$ 58.808,00
    texto = re.sub(r"R\$\s*[\d.,]+", _converter_reais, texto)
    # 6. Converter percentuais: 20%
    texto = re.sub(r"([\d.,]+)\s*%", _converter_percentual, texto)
    # 7. Converter datas inline: 04/05, 16/04/2026
    texto = re.sub(r"\b\d{1,2}[/\-]\d{1,2}(?:[/\-]\d{2,4})?\b", _converter_data_inline, texto)
    # 7.5. Converter ordinais: 11º, 11°, 2ª
    texto = re.sub(r"\b(\d{1,3})\s*([º°ª])", _converter_ordinal, texto)
    # 8. Converter números isolados (até 6 dígitos) que não façam parte de palavras
    texto = re.sub(r"(?<!\w)\d{1,6}(?!\w)", _converter_numero_solto, texto)
    # 9. Soletra siglas maiúsculas conhecidas (2-5 letras)
    texto = re.sub(r"\b[A-ZÁÉÍÓÚÀÂÊÔÃÕÇ]{2,5}\b", _soletra_sigla, texto)
    # 10. Limpar espaços duplicados
    texto = re.sub(r"\s{2,}", " ", texto).strip()
    # 11. Limpar pontuação duplicada e trailing
    texto = re.sub(r"[.,]{2,}", ".", texto)
    texto = re.sub(r"\.\s*,", ".", texto)
    texto = re.sub(r"\.\s*\.", ".", texto)
    texto = re.sub(r"^\s*[.,]\s*", "", texto)  # remove pontuação no início
    return texto


def extrair_info_programa(linhas: list) -> dict:
    """Extrai número do episódio e data a partir do cabeçalho."""
    info = {"ep": None, "dia": None, "mes": None}
    for linha in linhas[:15]:
        m = MARCADOR_CABECALHO_PROGRAMA.search(linha)
        if m:
            info["ep"] = int(m.group(1))
            info["dia"] = m.group(2).zfill(2)
            info["mes"] = m.group(3).zfill(2)
            return info
        m2 = re.search(r"NJUD\s*(\d{3,4})\s+(\d{1,2})[/\-](\d{1,2})", linha, re.IGNORECASE)
        if m2:
            info["ep"] = int(m2.group(1))
            info["dia"] = m2.group(2).zfill(2)
            info["mes"] = m2.group(3).zfill(2)
            return info
    return info


def remover_apresentacao_nominal(texto: str) -> str:
    """Remove apresentações do tipo 'Eu sou Leonardo Almeida' ou 'Com vocês, Fulano'."""
    texto = re.sub(
        r"(?:EU\s+SOU|MEU\s+NOME\s+[EÉ]|AQUI\s+[EÉ]|COM\s+VOC[EÊ]S?[,]?)\s+[A-ZÁÉÍÓÚÀÂÊÔÃÕÇ][a-záéíóúàâêôãõç]+(?:\s+[A-ZÁÉÍÓÚÀÂÊÔÃÕÇ][a-záéíóúàâêôãõç]+)*",
        "",
        texto,
        flags=re.IGNORECASE
    )
    return texto.strip()


def processar_roteiro_completo(conteudo: str, year: int = DEFAULT_YEAR) -> tuple:
    """
    Processa um roteiro bruto completo.

    Detecta as seções estruturais do jornal:
        ABERTURA  →  ESCALADA (chamadas)  →  SOBE TRILHA/QDA  →  NOTAS  →  ENCERRAMENTO

    Intercala cada chamada com sua nota correspondente:
        Speaker 1: chamada 1
        Speaker 2: nota 1
        Speaker 1: chamada 2
        Speaker 2: nota 2
        ...
    """
    linhas = conteudo.split("\n")
    info = extrair_info_programa(linhas)
    ep = info["ep"]
    data_str = f"{info['dia']}-{info['mes']}-{year}" if info["dia"] and info["mes"] else None

    # ── Primeira passagem: dividir em seções por SOBE TRILHA / QDA ──
    SEPARADOR = re.compile(r"^\s*(SOBE\s+TRILHA['\s]*|QDA)\s*$", re.IGNORECASE)
    CABECALHO = re.compile(
        r"^\s*(Tempo\s+m[aá]x|not[ií]cias\s+do\s+judici[aá]rio|PROGRAMA\s+N[ºO°])\s*", re.IGNORECASE
    )

    secoes = []        # lista de listas — cada sub-lista é um bloco entre separadores
    bloco_atual = []

    for linha in linhas:
        linha_strip = linha.strip()
        if not linha_strip:
            continue
        # Ignorar cabeçalhos do programa
        if MARCADOR_CABECALHO_PROGRAMA.search(linha_strip):
            continue
        if CABECALHO.match(linha_strip):
            continue

        # Separadores SOBE TRILHA / QDA delimitam seções
        if SEPARADOR.match(linha_strip):
            if bloco_atual:
                secoes.append(bloco_atual)
                bloco_atual = []
            continue

        # Extrair texto da linha (com ou sem LOC/Speaker)
        m_loc = re.match(r"^(LOC\s*(\d)?)\s*:\s*(.*)$", linha_strip, re.IGNORECASE)
        m_sp = re.match(r"^(Speaker\s*[12])\s*:\s*(?:\[.*?\])?\s*(.*)$", linha_strip, re.IGNORECASE)

        if m_loc:
            texto = m_loc.group(3).strip()
        elif m_sp:
            texto = m_sp.group(2).strip()
        else:
            texto = linha_strip

        if texto:
            texto = remover_apresentacao_nominal(texto)
            texto = limpar_texto_locutor(texto)
            if texto and len(texto) > 3:
                bloco_atual.append(texto)

    # Não esquecer o último bloco
    if bloco_atual:
        secoes.append(bloco_atual)

    # ── Identificar abertura, escalada, notas, encerramento ──
    # Estrutura típica:
    #   seção 0 = pode ser vazia ou conter a abertura
    #   seção 1 = escalada (chamadas / manchetes curtas)
    #   seção 2 = notas (textos completos das notícias) + encerramento no final
    #
    # Quando há apenas 2 seções: seção 0 = abertura + escalada, seção 1 = notas + encerramento
    # Quando há 3+ seções: seção 0 = abertura, seção 1 = escalada, seção 2+ = notas + encerramento

    abertura = []
    chamadas = []
    notas = []
    encerramento = []

    # Heurística para detectar o encerramento: última fala que menciona "termina aqui"
    # ou "até a próxima"
    def is_encerramento(txt):
        return bool(re.search(r"termina\s+aqui|at[eé]\s+a\s+pr[oó]xima|encerra", txt, re.IGNORECASE))

    if len(secoes) >= 3:
        # Seção 0 = abertura
        abertura = secoes[0]
        # Seção 1 = escalada (chamadas)
        chamadas = secoes[1]
        # Seções 2+ = notas + possível encerramento
        todas_notas = []
        for s in secoes[2:]:
            todas_notas.extend(s)
        # Separar encerramento da última nota
        for i in range(len(todas_notas) - 1, -1, -1):
            if is_encerramento(todas_notas[i]):
                encerramento = [todas_notas[i]]
                notas = todas_notas[:i]
                break
        else:
            notas = todas_notas

    elif len(secoes) == 2:
        # Seção 0 = abertura + escalada (precisamos separar)
        # A abertura geralmente é a primeira fala (saudação)
        bloco0 = secoes[0]
        if len(bloco0) > 1:
            abertura = [bloco0[0]]
            chamadas = bloco0[1:]
        else:
            abertura = bloco0
        # Seção 1 = notas + encerramento
        bloco1 = secoes[1]
        for i in range(len(bloco1) - 1, -1, -1):
            if is_encerramento(bloco1[i]):
                encerramento = [bloco1[i]]
                notas = bloco1[:i]
                break
        else:
            notas = bloco1

    elif len(secoes) == 1:
        # Tudo numa seção só — fallback simples
        bloco = secoes[0]
        if len(bloco) > 2:
            abertura = [bloco[0]]
            if is_encerramento(bloco[-1]):
                encerramento = [bloco[-1]]
                meio = bloco[1:-1]
            else:
                meio = bloco[1:]
            # Dividir ao meio: primeira metade = chamadas, segunda = notas
            metade = len(meio) // 2
            chamadas = meio[:metade]
            notas = meio[metade:]
        else:
            abertura = bloco

    # ── Montar saída com marcadores de seção para sound design ──
    #
    # Estrutura final do programa:
    #   [SECTION:ABERTURA]        → Speaker 1 (com vinheta de abertura antes)
    #   [SECTION:ESCALADA]        → Speaker 1 e 2 revezando (com BG a 30%)
    #   [SECTION:MATERIA]         → Speaker 1 lê manchete, Speaker 2 lê nota
    #                               (com VHT passagem entre cada matéria)
    #   [SECTION:ENCERRAMENTO]    → Speaker 1 (com BG a 30%, vinheta de encerramento depois)

    linhas_saida = []

    # Header
    header = "Read in a professional news anchor style suitable for Brazilian radio. The tone should be authoritative, clear, and dynamic.\n"
    if ep:
        header += f"\nNJUD {ep}"
        if data_str:
            partes = data_str.split("-")
            header += f" {partes[0]}-{partes[1]}"
    header += "\n"
    linhas_saida.append(header)

    # ABERTURA → Speaker 1
    linhas_saida.append("[SECTION:ABERTURA]")
    for txt in abertura:
        linhas_saida.append(f"Speaker 1: [professional] {txt}")

    # ESCALADA → revezamento entre Speaker 1 e Speaker 2
    if chamadas:
        linhas_saida.append("")
        linhas_saida.append("[SECTION:ESCALADA]")
        for i, txt in enumerate(chamadas):
            speaker = "Speaker 1" if i % 2 == 0 else "Speaker 2"
            linhas_saida.append(f"{speaker}: [professional] {txt}")

    # MATÉRIAS → para cada par (chamada, nota):
    #   Speaker 1 lê a manchete completa
    #   Speaker 2 lê a nota/corpo da notícia
    #   [VHT_PASSAGEM] entre cada matéria
    n_chamadas = len(chamadas)
    n_notas = len(notas)
    n_materias = max(n_chamadas, n_notas)

    if n_materias > 0:
        for i in range(n_materias):
            linhas_saida.append("")
            linhas_saida.append("[SECTION:MATERIA]")
            if i < n_chamadas:
                linhas_saida.append(f"Speaker 1: [professional] {chamadas[i]}")
            if i < n_notas:
                linhas_saida.append(f"Speaker 2: [professional] {notas[i]}")
            # Marcador de passagem entre matérias (não depois da última)
            if i < n_materias - 1:
                linhas_saida.append("[VHT_PASSAGEM]")

    # ENCERRAMENTO → Speaker 1
    if encerramento:
        linhas_saida.append("")
        linhas_saida.append("[SECTION:ENCERRAMENTO]")
        for txt in encerramento:
            linhas_saida.append(f"Speaker 1: [professional] {txt}")

    texto_final = "\n".join(linhas_saida) + "\n"
    return texto_final, ep, data_str


# ─────────────────────────────────────────────
# MAIN — PROCESSAMENTO EM LOTE
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Processador de roteiros completos (sem IA) — converte TXT brutos para formato Speaker 1/2."
    )
    parser.add_argument("--src", default=DEFAULT_SRC, help="Pasta raiz dos roteiros originais")
    parser.add_argument("--dest", default=DEFAULT_DEST, help="Pasta destino dos roteiros processados")
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR, help="Ano para inclusão nas datas")
    parser.add_argument("--single", help="Processa um único arquivo TXT (caminho completo)")
    args = parser.parse_args()

    print("=== Processador de Roteiros Completos (sem IA) ===\n")

    # Modo arquivo único
    if args.single:
        if not os.path.exists(args.single):
            print(f"[ERRO] Arquivo não encontrado: {args.single}")
            sys.exit(1)
        with open(args.single, "r", encoding="utf-8") as f:
            conteudo = f.read()
        texto, ep, data = processar_roteiro_completo(conteudo, args.year)
        print(texto)
        print(f"\n--- Episódio: {ep} | Data: {data} ---")
        return

    # Modo lote
    src_base = args.src
    dest_base = args.dest

    if not os.path.exists(src_base):
        print(f"[ERRO] Pasta de origem não encontrada: {src_base}")
        print("Use --src para apontar o caminho correto dos roteiros originais.")
        sys.exit(1)

    # Listar subpastas (meses)
    subpastas = sorted([
        d for d in os.listdir(src_base)
        if os.path.isdir(os.path.join(src_base, d))
    ])

    if not subpastas:
        # Talvez os TXT estejam diretamente na raiz
        subpastas = [""]

    total = 0
    novos = 0

    for sub in subpastas:
        src_dir = os.path.join(src_base, sub) if sub else src_base
        dest_dir = os.path.join(dest_base, sub) if sub else dest_base

        arquivos = sorted([f for f in os.listdir(src_dir) if f.lower().endswith(".txt")])
        if not arquivos:
            continue

        print(f"--- {sub or 'Raiz'}: {len(arquivos)} arquivo(s) ---")

        for arq in arquivos:
            total += 1
            caminho_src = os.path.join(src_dir, arq)

            with open(caminho_src, "r", encoding="utf-8") as f:
                conteudo = f.read()

            texto, ep, data = processar_roteiro_completo(conteudo, args.year)

            # Nome do arquivo de saída
            if ep:
                nome_dest = f"NJUD_{ep}.txt"
            else:
                nome_dest = arq

            os.makedirs(dest_dir, exist_ok=True)
            caminho_dest = os.path.join(dest_dir, nome_dest)

            # Pular se já existe
            if os.path.exists(caminho_dest):
                continue

            with open(caminho_dest, "w", encoding="utf-8") as f:
                f.write(texto)

            ep_label = f"NJUD {ep}" if ep else arq
            print(f"  [OK] {ep_label} → {nome_dest}")
            novos += 1

    print(f"\n=== CONCLUÍDO: {novos} novos de {total} roteiros processados ===")
    print(f"Destino: {dest_base}")


if __name__ == "__main__":
    main()
