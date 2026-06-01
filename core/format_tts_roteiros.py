"""
format_tts_roteiros.py
======================
Converte os roteiros do formato antigo para o padrão TTS:

ENTRADA (formato antigo):
  ROTEIRO GIRO NAS COMARCAS
  PROGRAMA 32 |  EXIBIÇÃO: 09/04/2024
  Vh abertura GIRO
  LOC / LOC:
  OLÁ// ...
  Vh passagem nota
  Nota 1
  LOC:
  OFF:
  <texto da matéria>
  encerramento GIRO

SAÍDA (formato padrão):
  ROTEIRO GIRO NAS COMARCAS //não entra na locução
  PROGRAMA 32|  EXIBIÇÃO: 09/04/2024 //não entra na locução

  [Vh abertura GIRO]

  [LOC:]
  OLÁ// HOJE É <DIA> / E ESSE É O GIRO PELAS COMARCAS DO RIO GRANDE DO NORTE//

  [Vh passagem]

  [LOC:]
  <texto da matéria 1>

  [Vh passagem]

  [LOC:]
  <texto da matéria 2>

  [vht encerramento]
"""
import pathlib
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TTS_DIR = pathlib.Path(r"E:\NJUD\PROGRAMA GIRO NAS COMARCAS\tts_txt")

# ---------------------------------------------------------------------------
# Mapeamento dia da semana em português
# ---------------------------------------------------------------------------
DIAS = {
    0: "SEGUNDA-FEIRA", 1: "TERÇA-FEIRA", 2: "QUARTA-FEIRA",
    3: "QUINTA-FEIRA",  4: "SEXTA-FEIRA", 5: "SÁBADO", 6: "DOMINGO",
}

def get_dia_semana(data_str: str) -> str:
    """Tenta extrair o dia da semana de uma string DD/MM/AAAA."""
    import datetime
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            dt = datetime.datetime.strptime(data_str.strip(), fmt)
            return DIAS[dt.weekday()]
        except ValueError:
            pass
    return "TERÇA-FEIRA"   # fallback padrão do programa

# ---------------------------------------------------------------------------
# Detecção de tipo
# ---------------------------------------------------------------------------
def is_already_formatted(text: str) -> bool:
    return "[LOC:]" in text or "[Vh " in text or "[vht" in text.lower()

def is_pauta_bruta(text: str) -> bool:
    return "* " in text and ("FONTE" in text or "PAUTA" in text)

# ---------------------------------------------------------------------------
# Extrai cabeçalho: número e data
# ---------------------------------------------------------------------------
PROG_RE  = re.compile(r"PROGRAMA\s+(\S+)\s*[\|]?\s*EXIBI[CÇ][AÃ]O[:\s]+([^\n\\]+)", re.IGNORECASE)
PROG_RE2 = re.compile(r"PROGRAMA\s+(\S+)", re.IGNORECASE)

def extract_header(text: str):
    """Retorna (prog_num_str, data_str) ou ('?', '')."""
    m = PROG_RE.search(text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    m = PROG_RE2.search(text)
    if m:
        return m.group(1).strip(), ""
    return "?", ""

# ---------------------------------------------------------------------------
# Extrai blocos de matéria do formato antigo
# ---------------------------------------------------------------------------
# Separadores que indicam fim de um bloco e início de outro
VH_PASS_RE = re.compile(
    r"(?:Vh\s+passagem(?:\s+nota)?|vh\s+passagem(?:\s+nota)?|VH\s+PASSAGEM(?:\s+NOTA)?)",
    re.IGNORECASE,
)
LOC_RE = re.compile(r"^(?:LOC:|LOC\b)", re.IGNORECASE | re.MULTILINE)
OFF_RE = re.compile(r"^OFF:\s*", re.IGNORECASE | re.MULTILINE)
NOTA_RE = re.compile(r"^Nota\s+\d+\s*$", re.IGNORECASE | re.MULTILINE)

# Linhas de metadados que não devem ir para a locução
SKIP_LINES_RE = re.compile(
    r"^("
    r"ROTEIRO GIRO|PROGRAMA\s+\d|EXIBI|"
    r"Vh\s+abertura|Vh\s+passagem|Vh\s+encerramento|"
    r"encerramento\s+GIRO|encerramento$|"
    r"LOC:|LOC$|OFF:|Nota\s+\d|"
    r"RETRANCA|FONTE[S]?\s|PAUTA:|REDA[CÇ]|REVIS|CONTATO|EDI[CÇ][AÃ]O:|"
    r"Sugest[aã]o\s+de\s+pergunta|"
    r"https?://|"
    r"\s*$"
    r")",
    re.IGNORECASE,
)

def extract_materia_blocks(text: str) -> list[str]:
    """
    Divide o texto em blocos de matéria (texto de locução puro).
    Estratégia:
      1. Remove cabeçalho até primeira ocorrência de 'Vh abertura'
      2. Divide pelos separadores 'Vh passagem nota' / 'Nota N'
      3. Em cada segmento, pega o texto após LOC: / OFF:
      4. Filtra linhas de metadado
    """
    # Remove tudo antes do primeiro LOC da abertura (saudação)
    # Queremos pegar apenas os blocos de matéria, não a saudação de abertura
    lines = text.splitlines()

    # Identifica índice da primeira saudação (OLÁ //)
    abertura_idx = next(
        (i for i, l in enumerate(lines) if re.match(r"OL[AÁ]//", l.strip(), re.IGNORECASE)), None
    )

    # Identifica índice do encerramento
    encerramento_idx = next(
        (i for i, l in enumerate(lines)
         if re.search(r"encerramento", l, re.IGNORECASE) and
            not re.search(r"LOC|OFF|Nota|RETR", l, re.IGNORECASE)),
        len(lines)
    )

    body_lines = lines[(abertura_idx + 1) if abertura_idx is not None else 0 : encerramento_idx]
    body = "\n".join(body_lines)

    # Divide por separadores de passagem ou numeração de nota
    segments = re.split(
        r"\n\s*(?:Vh\s+passagem(?:\s+nota)?|Nota\s+\d+)\s*\n",
        body,
        flags=re.IGNORECASE,
    )

    blocks = []
    for seg in segments:
        # Dentro de cada segmento, pega o texto após LOC: e/ou OFF:
        after_loc = re.split(r"(?:^|\n)\s*(?:LOC:|LOC\b|OFF:)\s*\n?", seg, flags=re.IGNORECASE)
        # Pega o maior fragmento de texto corrido
        candidate = max(after_loc, key=lambda s: len(s.strip()))
        # Filtra linhas de metadado e URLs
        clean_lines = []
        for line in candidate.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if SKIP_LINES_RE.match(stripped):
                continue
            if stripped.startswith("*") and len(stripped) < 120:
                # bullet curto = metadado/fonte, não locução
                continue
            clean_lines.append(stripped)
        block_text = "\n".join(clean_lines).strip()
        if block_text and len(block_text) > 30:
            blocks.append(block_text)

    return blocks

# ---------------------------------------------------------------------------
# Monta o roteiro no formato padrão
# ---------------------------------------------------------------------------
def build_roteiro(prog_num: str, data_str: str, blocks: list[str]) -> str:
    dia = get_dia_semana(data_str) if data_str else "TERÇA-FEIRA"
    data_label = data_str if data_str else "DD/MM/AAAA"

    abertura_loc = (
        f"OLÁ// HOJE É {dia} / "
        f"E ESSE É O GIRO PELAS COMARCAS DO RIO GRANDE DO NORTE//"
    )

    lines = [
        f"ROTEIRO GIRO NAS COMARCAS //não entra na locução",
        f"PROGRAMA {prog_num}|  EXIBIÇÃO: {data_label} //não entra na locução",
        "",
        "[Vh abertura GIRO]",
        "",
        "[LOC:] ",
        abertura_loc,
    ]

    for block in blocks:
        lines += [
            "",
            "[Vh passagem]",
            "",
            "[LOC:]",
            block,
        ]

    lines += [
        "",
        "[vht encerramento]",
        "",
    ]
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    txt_files = sorted(TTS_DIR.glob("*.txt"))
    converted = skipped_formatted = skipped_pauta = 0

    for fpath in txt_files:
        text = fpath.read_text(encoding="utf-8", errors="replace")

        if is_already_formatted(text):
            print(f"  [OK]   {fpath.name}  (já formatado, ignorado)")
            skipped_formatted += 1
            continue

        if is_pauta_bruta(text):
            print(f"  [!]    {fpath.name}  (pauta bruta - requer redação manual)")
            skipped_pauta += 1
            continue

        prog_num, data_str = extract_header(text)
        blocks = extract_materia_blocks(text)

        if not blocks:
            print(f"  [WARN] {fpath.name}  prog={prog_num}  — nenhum bloco extraído, pulando")
            skipped_pauta += 1
            continue

        novo_roteiro = build_roteiro(prog_num, data_str, blocks)
        fpath.write_text(novo_roteiro, encoding="utf-8")
        print(f"  [CONV] {fpath.name}  prog={prog_num}  data={data_str}  blocos={len(blocks)}")
        converted += 1

    print(f"\n{'='*55}")
    print(f"Convertidos  : {converted}")
    print(f"Já no padrão : {skipped_formatted}")
    print(f"Pauta bruta  : {skipped_pauta}  (requerem revisão manual)")

if __name__ == "__main__":
    main()
