import os
import sys
import re
import asyncio
import pathlib

# Ajuste de path para importar do core
current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.append(str(project_root))

from core.models import ProgramRecipe, VoiceStrategy, AssemblyRecipe
from core.engine import PipelineEngine

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
GIRO_DIR     = project_root / "PROGRAMA GIRO NAS COMARCAS"
VHT_DIR      = pathlib.Path(r"H:\Meu Drive\RADIO TJRN CONTEÚDO\PROGRAMAS\PROGRAMA GIRO NAS COMARCAS (10min)\_VHT")
DRIVE_BASE   = pathlib.Path(r"H:\Meu Drive\RADIO TJRN CONTEÚDO\PROGRAMAS\PROGRAMA GIRO NAS COMARCAS (10min)")

PAUTA_TO_SCRIPT_PROMPT = """Transforme a PAUTA abaixo em um ROTEIRO DE RADIOJORNALISMO completo para o programa 'Giro nas Comarcas'.

ESTRUTURA OBRIGATÓRIA:
ROTEIRO GIRO NAS COMARCAS //não entra na locução
PROGRAMA [NUMERO]|  EXIBIÇÃO: [DATA] //não entra na locução

[Vh abertura GIRO]

[LOC:] 
LOCUTOR 1: Olá! Hoje é [DIA-DA-SEMANA], [DATA-EXTENSO], e esse é o Giro pelas Comarcas do Rio Grande do Norte.

[Vh passagem]

[LOC:]
(Desenvolva as notícias da pauta aqui, alternando entre LOCUTOR 1 e LOCUTOR 2. 
Cada notícia deve começar com um [Vh passagem] e um novo bloco [LOC:].
Use o padrão 'LOCUTOR X (CABEÇA):' para o título da nota e 'LOCUTOR Y:' para o corpo.
Mantenha as tags [Vh passagem] e [LOC:] entre cada matéria separadamente.)

[vht encerramento]
"""

REWRITE_PROMPT = """Você é um editor especializado em radiojornalismo para o TJRN.
Sua tarefa é reescrever o texto de locução recebido aplicando EXATAMENTE as regras abaixo.
PRESERVE as tags técnicas ([LOC:], [Vh ...]) e de locutor (LOCUTOR 1:).

REGRAS:
1. Números, valores, datas e horas por extenso.
2. Siglas soletradas (T J R N).
3. Linguagem simples.
4. Nunca começar nota pelo verbo.
5. Sem markdown.
"""

def giro_pre_process(content: str) -> str:
    """Detecta se é pauta bruta e converte para roteiro, senão retorna o texto."""
    if "[LOC:]" not in content:
        print("  - Transformando pauta bruta em roteiro estruturado...")
        from core.llm_factory import LLMFactory
        llm = LLMFactory()
        return llm.ask(PAUTA_TO_SCRIPT_PROMPT, content)
    return content

def giro_parse_hook(content: str) -> list:
    """Divide o roteiro em blocos de VHT e LOC (com as falas extraídas)."""
    def extrair_falas_bloco(texto_bloco: str):
        pattern = r"(LOCUTOR\s*[12](?:\s*\(.*?\))?:)"
        parts = re.split(pattern, texto_bloco, flags=re.IGNORECASE)
        falas = []
        current_speaker = "speaker1"
        for part in parts:
            part = part.strip()
            if not part: continue
            match = re.match(r"LOCUTOR\s*([12])", part, re.IGNORECASE)
            if match: current_speaker = f"speaker{match.group(1)}"
            else: falas.append((current_speaker, part))
        return falas

    pattern = r"(\[(?:Vh|vht).*?\]|\[LOC:\])"
    parts = re.split(pattern, content, flags=re.IGNORECASE)
    blocks = []
    current_tag = None
    for part in parts:
        part = part.strip()
        if not part: continue
        if part.lower() == "[loc:]": current_tag = "[LOC:]"
        elif part.startswith("[") and part.endswith("]"):
            blocks.append(("VHT", part))
            current_tag = None
        elif current_tag == "[LOC:]":
            falas = extrair_falas_bloco(part)
            for speaker, texto in falas:
                blocks.append(("LOC", (speaker, texto)))
            current_tag = None
    return blocks

# ---------------------------------------------------------------------------
# Receita do Programa
# ---------------------------------------------------------------------------
receita_giro = ProgramRecipe(
    name="Giro nas Comarcas",
    drive_input_dir=GIRO_DIR / "tts_txt", # Não é exatamente no drive, mas é onde os arquivos brutos entram
    drive_output_dir=DRIVE_BASE,
    local_work_dir=GIRO_DIR,
    system_prompt=REWRITE_PROMPT,
    voice_strategy=VoiceStrategy(
        type='intra_file',
        voices=["pt-BR-FranciscaNeural", "pt-BR-AntonioNeural"]
    ),
    assembly=AssemblyRecipe(
        intro_vht=VHT_DIR / "VHT - ABERTURA.mp3",
        transition_vht=VHT_DIR / "VHT - PASSAGEM.mp3",
        outro_vht=VHT_DIR / "VHT - ENCERRAMENTO.mp3"
    ),
    pre_process_hook=giro_pre_process,
    parse_hook=giro_parse_hook
)

if __name__ == "__main__":
    motor = PipelineEngine(receita_giro)
    asyncio.run(motor.run_all())
