"""
rewrite_giro_tts.py
====================
Aplica as diretrizes de radiojornalismo do TJRN a cada bloco [LOC:] dos
roteiros do Giro nas Comarcas, usando a API OpenAI (GPT-4o) como motor
de reescrita.

Regras aplicadas:
  - Números, valores, datas e horas por extenso
  - Siglas soletradas letra a letra (T J R N, N A P S…)
  - Linguagem simples: sem jargões, sem rodeios, frases diretas
  - Nenhuma formatação Markdown no texto falado
  - Texto mantido fiel à essência da notícia

Estrutura preservada:
  ROTEIRO GIRO NAS COMARCAS //…
  PROGRAMA …|  EXIBIÇÃO: … //…
  [Vh abertura GIRO]
  [LOC:] … (abertura padrão)
  [Vh passagem] / [LOC:] / (matéria) …
  [vht encerramento]
"""
from __future__ import annotations

import os
import re
import sys
import time
import pathlib

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TTS_DIR    = pathlib.Path(r"E:\NJUD\PROGRAMA GIRO NAS COMARCAS\tts_txt")
OUT_DIR    = TTS_DIR.parent / "tts_txt_revisado"
OUT_DIR.mkdir(exist_ok=True)

def get_openai_key():
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        env_path = pathlib.Path(r"e:\NJUD\.env")
        if env_path.exists():
            content = env_path.read_text(encoding="utf-8")
            # Busca a chave ignorando quebras de linha que o Select-String pode ter introduzido
            match = re.search(r"OPENAI_API_KEY\s*=\s*([^\s]+)", content)
            if match:
                key = match.group(1).strip()
    return key

OPENAI_KEY = get_openai_key()

if not OPENAI_KEY:
    sys.exit("OPENAI_API_KEY não encontrada. Configure no .env ou como variável de ambiente.")

# ---------------------------------------------------------------------------
# Cliente OpenAI
# ---------------------------------------------------------------------------
from openai import OpenAI
client = OpenAI(api_key=OPENAI_KEY)

# ---------------------------------------------------------------------------
# System prompt de reescrita
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
Você é um editor especializado em radiojornalismo para o TJRN.
Sua tarefa é reescrever o texto de locução recebido aplicando EXATAMENTE as regras abaixo.
O texto pode conter tags de locutor (ex: LOCUTOR 1:, LOCUTOR 2:, LOCUTOR 1 (CABEÇA):). 
Você DEVE PRESERVAR essas tags exatamente como estão no início das falas.

REGRAS OBRIGATÓRIAS:
1. Preserve as tags LOCUTOR 1: e LOCUTOR 2: no início dos blocos de fala.
2. Números, valores financeiros, porcentagens, datas e horas: escrever por extenso.
   Ex: "R$ 21,1 mil" → "vinte e um mil e cem reais"
       "37, parágrafo 6" → "trinta e sete, parágrafo sexto"
       "16 de janeiro de 2024" → "dezesseis de janeiro de dois mil e vinte e quatro"
       "8h" → "às oito horas"
3. Siglas: soletrar letra a letra separadas por espaço na PRIMEIRA menção; nas seguintes pode repetir a sigla soletrada.
   Ex: "TJRN" → "T J R N"  |  "NAPS" → "N A P S"  |  "CGJ" → "C G J"
4. Sites e links: leitura literal. Ex: "tjrn.jus.br" → "t j r n ponto jus ponto b r"
5. Linguagem simples: eliminar jargões jurídicos desnecessários, termos formalistas.
   Substituir por equivalentes diretos. Ex: "prolatou sentença" → "decidiu", "parte autora" → "a cidadã"
6. Nunca começar a nota pelo verbo. Reestruture se necessário.
7. Manter a essência e os fatos da notícia intactos.
8. Texto corrido dentro de cada fala, sem bullets, sem listas.
9. Nenhum markdown (sem *, sem **, sem #).
Devolva APENAS o texto reescrito, mantendo as tags de locutor.
"""

def rewrite_bloc(text: str, prog_id: str) -> str:
    """Envia um bloco de texto para reescrita via OpenAI."""
    if not text.strip() or len(text.strip()) < 20:
        return text
    # Não reescreve a abertura padrão (OLÁ// HOJE É…)
    if re.match(r"OL[AÁ]//", text.strip(), re.IGNORECASE):
        return text

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",   # rápido e econômico para reescrita
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": text.strip()},
                ],
                temperature=0.3,
                max_tokens=2048,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            print(f"    [!] Tentativa {attempt+1}/3 falhou: {exc}")
            time.sleep(2 ** attempt)
    return text   # devolve original se todas falharem

# ---------------------------------------------------------------------------
# Parser do roteiro
# ---------------------------------------------------------------------------
BLOC_RE = re.compile(
    r"(\[LOC:\]\s*\n)(.*?)(?=\n\[|\Z)",
    re.DOTALL | re.IGNORECASE,
)

def process_file(fpath: pathlib.Path) -> None:
    content = fpath.read_text(encoding="utf-8", errors="replace")

    # Pula arquivos de pauta bruta (sem [LOC:])
    if "[LOC:]" not in content and "[Vh " not in content:
        print(f"  [SKIP] {fpath.name}  (pauta bruta)")
        return

    new_content = content
    blocs = list(BLOC_RE.finditer(content))
    offset = 0

    for m in blocs:
        tag   = m.group(1)    # "[LOC:] \n"
        body  = m.group(2)    # texto do bloco

        new_body = rewrite_bloc(body, fpath.stem)

        old = tag + body
        new = tag + new_body
        pos = new_content.find(old, offset)
        if pos >= 0:
            new_content = new_content[:pos] + new + new_content[pos + len(old):]
            offset = pos + len(new)

    dest = OUT_DIR / fpath.name
    dest.write_text(new_content, encoding="utf-8")
    print(f"  [OK]  {fpath.name}  ({len(blocs)} bloco(s) reescritos)")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    files = sorted(TTS_DIR.glob("*.txt"))
    print(f"Arquivos encontrados: {len(files)}")
    print(f"Saída em: {OUT_DIR}\n")

    for i, f in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {f.name}")
        process_file(f)
        time.sleep(0.5)   # rate-limit gentil

    print(f"\n✅ Concluído. Arquivos revisados em:\n   {OUT_DIR}")

if __name__ == "__main__":
    main()
