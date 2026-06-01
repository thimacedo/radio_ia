import os
import sys
import re
import asyncio
import pathlib
import shutil
import io
import edge_tts
from pydub import AudioSegment

# Ajuste de path para importar do core
current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "core"))

from llm_factory import LLMFactory

# ---------------------------------------------------------------------------
# Configuração de Caminhos
# ---------------------------------------------------------------------------
BASE_DIR     = pathlib.Path(r"E:\NJUD")
GIRO_DIR     = BASE_DIR / "PROGRAMA GIRO NAS COMARCAS"
TTS_DIR      = GIRO_DIR / "tts_txt"
REVISADO_DIR = GIRO_DIR / "tts_txt_revisado"
OUTPUT_DIR   = GIRO_DIR / "tts_mp3_premium"
VHT_DIR      = pathlib.Path(r"H:\Meu Drive\RADIO TJRN CONTEÚDO\PROGRAMAS\PROGRAMA GIRO NAS COMARCAS (10min)\_VHT")
DRIVE_BASE   = pathlib.Path(r"H:\Meu Drive\RADIO TJRN CONTEÚDO\PROGRAMAS\PROGRAMA GIRO NAS COMARCAS (10min)")

REVISADO_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Mapeamento de Tags para Arquivos de Vinheta
VHT_MAP = {
    "[Vh abertura GIRO]": VHT_DIR / "VHT - ABERTURA.mp3",
    "[Vh passagem]":      VHT_DIR / "VHT - PASSAGEM.mp3",
    "[vht encerramento]": VHT_DIR / "VHT - ENCERRAMENTO.mp3"
}

VOZ_SPEAKER_1 = "pt-BR-FranciscaNeural"
VOZ_SPEAKER_2 = "pt-BR-AntonioNeural"

llm = LLMFactory()

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Funções de Áudio
# ---------------------------------------------------------------------------

async def synthesize_text(text: str, voice: str) -> bytes:
    for attempt in range(3):
        try:
            communicate = edge_tts.Communicate(text, voice)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio": audio_data += chunk["data"]
            return audio_data
        except Exception as e:
            print(f"      [!] Falha TTS (Tentativa {attempt+1}/3): {e}")
            if attempt < 2: await asyncio.sleep(3 ** attempt)
    raise Exception("Falha persistente no serviço TTS.")

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

def parse_roteiro(content: str):
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

async def generate_premium_audio(txt_path: pathlib.Path):
    content = txt_path.read_text(encoding="utf-8")
    blocks = parse_roteiro(content)
    combined_audio = AudioSegment.empty()
    for kind, value in blocks:
        if kind == "VHT":
            vht_path = VHT_MAP.get(value)
            if vht_path and vht_path.exists():
                combined_audio += AudioSegment.from_mp3(str(vht_path))
        elif kind == "LOC":
            speaker, texto = value
            voz = VOZ_SPEAKER_1 if speaker == "speaker1" else VOZ_SPEAKER_2
            audio_bytes = await synthesize_text(texto, voz)
            combined_audio += AudioSegment.from_mp3(io.BytesIO(audio_bytes))
    out_path = OUTPUT_DIR / txt_path.with_suffix(".mp3").name
    combined_audio.export(str(out_path), format="mp3", bitrate="192k")
    return out_path

# ---------------------------------------------------------------------------
# Pipeline e Sincronização
# ---------------------------------------------------------------------------

def get_drive_path(mp3_name: str):
    year = "2025" if "2025" in mp3_name else "2026"
    dest_dir = DRIVE_BASE / year
    month_match = re.search(r"-(\d{2})-", mp3_name)
    if month_match:
        month_map = {"01":"JAN","02":"FEV","03":"MAR","04":"ABR","05":"MAI","06":"JUN","07":"JUL","08":"AGO","09":"SET","10":"OUT","11":"NOV","12":"DEZ"}
        dest_dir = dest_dir / month_map.get(month_match.group(1), "OUTROS")
    return dest_dir / mp3_name

def sync_to_drive(local_mp3: pathlib.Path):
    try:
        dest_path = get_drive_path(local_mp3.name)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_mp3, dest_path)
        print(f"    [SYNC] {local_mp3.name} -> {dest_path.parent}")
    except Exception as e: print(f"    [ERRO SYNC] {e}")

async def process_pipeline(fpath: pathlib.Path):
    mp3_name = fpath.with_suffix(".mp3").name
    drive_dest = get_drive_path(mp3_name)
    
    if drive_dest.exists():
        print(f"  [SKIP] {fpath.name} já existe no Drive.")
        return

    print(f"\n[PIPELINE] {fpath.name}")
    content = fpath.read_text(encoding="utf-8", errors="replace")
    
    if "[LOC:]" not in content:
        print("  - Transformando pauta em roteiro...")
        content = llm.ask(PAUTA_TO_SCRIPT_PROMPT, content)
    
    print("  - Reescrita jornalística...")
    content_revisado = llm.ask(REWRITE_PROMPT, content)
    revisado_path = REVISADO_DIR / fpath.name
    revisado_path.write_text(content_revisado, encoding="utf-8")
    
    print("  - Gerando áudio e sincronizando...")
    try:
        mp3_path = await generate_premium_audio(revisado_path)
        if mp3_path.exists():
            sync_to_drive(mp3_path)
    except Exception as e:
        print(f"    [ERRO PIPELINE] {e}")

async def main():
    files = sorted([f for f in TTS_DIR.glob("*.txt") if not f.name.endswith(".bak")])
    for f in files:
        await process_pipeline(f)

if __name__ == "__main__":
    asyncio.run(main())
