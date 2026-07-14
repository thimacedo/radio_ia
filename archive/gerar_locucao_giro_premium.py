import os
import re
import asyncio
import io
import edge_tts
from pydub import AudioSegment
from pathlib import Path

# ---------------------------------------------------------------------------
import sys
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))
from core.best_practices import carregar_env_var

BASE_DIR    = project_root
GIRO_DIR    = BASE_DIR / "modules" / "giro" / "workspace"
INPUT_DIR   = GIRO_DIR / "tts_txt_revisado"
OUTPUT_DIR  = GIRO_DIR / "tts_mp3_premium"

# Tenta usar .env primeiro; fallback para path local (compatível com instaladores)
import sys
import os as _os
_current = _os.path.dirname(_os.path.abspath(__file__)).replace("\\", "/")
_project_root = _os.path.dirname(_os.path.dirname(_current)).replace("\\", "/")
sys.path.insert(0, _project_root)
try:
    from core.best_practices import carregar_env_var
    _vht_fallback = r"H:\Meu Drive\RADIO TJRN CONTEÚDO\PROGRAMAS\PROGRAMA GIRO NAS COMARCAS (10min)\_VHT"
    VHT_DIR = Path(carregar_env_var("DRIVE_GIRO_VHT_DIR", _vht_fallback))
except Exception:
    VHT_DIR = Path(r"H:\Meu Drive\RADIO TJRN CONTEÚDO\PROGRAMAS\PROGRAMA GIRO NAS COMARCAS (10min)\_VHT")

# Criar pasta de saída se não existir
OUTPUT_DIR.mkdir(exist_ok=True)

# Mapeamento de Tags para Arquivos de Vinheta
VHT_MAP = {
    "[Vh abertura GIRO]": VHT_DIR / "VHT - ABERTURA.mp3",
    "[Vh passagem]":      VHT_DIR / "VHT - PASSAGEM.mp3",
    "[vht encerramento]": VHT_DIR / "VHT - ENCERRAMENTO.mp3"
}

# Configuração de Vozes
VOZ_SPEAKER_1 = "pt-BR-FranciscaNeural"  # Feminina
VOZ_SPEAKER_2 = "pt-BR-AntonioNeural"    # Masculina

# ---------------------------------------------------------------------------
# Funções de Processamento
# ---------------------------------------------------------------------------

async def synthesize_text(text: str, voice: str) -> bytes:
    """Gera bytes de áudio usando edge-tts."""
    communicate = edge_tts.Communicate(text, voice)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

def extrair_falas_bloco(texto_bloco: str):
    """
    Divide um bloco [LOC:] em falas individuais de locutores.
    Detecta 'LOCUTOR 1' e 'LOCUTOR 2'.
    """
    # Regex para capturar LOCUTOR 1 ou LOCUTOR 2 (com ou sem (CABEÇA))
    pattern = r"(LOCUTOR\s*[12](?:\s*\(.*?\))?:)"
    parts = re.split(pattern, texto_bloco, flags=re.IGNORECASE)
    
    falas = []
    current_speaker = "speaker1" # Default se não houver tag no início
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        match = re.match(r"LOCUTOR\s*([12])", part, re.IGNORECASE)
        if match:
            current_speaker = f"speaker{match.group(1)}"
        else:
            falas.append((current_speaker, part))
            
    return falas

def parse_roteiro(content: str):
    """
    Divide o roteiro em blocos de Vinheta e Locução.
    Retorna uma lista de tuplas (tipo, conteúdo).
    """
    pattern = r"(\[(?:Vh|vht).*?\]|\[LOC:\])"
    parts = re.split(pattern, content, flags=re.IGNORECASE)
    
    blocks = []
    current_tag = None
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        if part.lower() == "[loc:]":
            current_tag = "[LOC:]"
        elif part.startswith("[") and part.endswith("]"):
            blocks.append(("VHT", part))
            current_tag = None
        elif current_tag == "[LOC:]":
            # Processa o conteúdo do bloco LOC para identificar locutores
            falas = extrair_falas_bloco(part)
            for speaker, texto in falas:
                blocks.append(("LOC", (speaker, texto)))
            current_tag = None
            
    return blocks

async def process_file(fpath: Path):
    print(f"  [PROCESSANDO] {fpath.name}")
    
    try:
        content = fpath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"    [ERRO] Falha ao ler arquivo: {e}")
        return

    blocks = parse_roteiro(content)
    if not blocks:
        print(f"    [AVISO] Nenhum bloco válido encontrado em {fpath.name}")
        return

    combined_audio = AudioSegment.empty()

    for i, (kind, value) in enumerate(blocks):
        if kind == "VHT":
            vht_path = VHT_MAP.get(value)
            if vht_path and vht_path.exists():
                print(f"    ({i+1}) Vinheta: {value}")
                vht_audio = AudioSegment.from_mp3(str(vht_path))
                combined_audio += vht_audio
            else:
                print(f"    [!] Vinheta não encontrada: {value}")
        
        elif kind == "LOC":
            speaker, texto = value
            voz = VOZ_SPEAKER_1 if speaker == "speaker1" else VOZ_SPEAKER_2
            print(f"    ({i+1}) {speaker.upper()} ({voz}): {texto[:50]}...")
            try:
                audio_bytes = await synthesize_text(texto, voz)
                loc_audio = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
                combined_audio += loc_audio
            except Exception as e:
                print(f"    [ERRO] Falha na síntese: {e}")

    # Exportar arquivo final
    out_path = OUTPUT_DIR / fpath.with_suffix(".mp3").name
    combined_audio.export(str(out_path), format="mp3", bitrate="192k")
    print(f"  [SUCESSO] Gerado: {out_path.name}\n")

async def main():
    print("=== Gerador de Locução Premium — Giro nas Comarcas ===\n")
    
    files = sorted(list(INPUT_DIR.glob("*.txt")))
    if not files:
        print(f"Nenhum arquivo .txt encontrado em: {INPUT_DIR}")
        return

    print(f"Arquivos para processar: {len(files)}")
    print(f"Vozes: {VOZ_SPEAKER_1} / {VOZ_SPEAKER_2}\n")

    for f in files:
        await process_file(f)

    print(f"✅ Concluído! Áudios salvos em:\n   {OUTPUT_DIR}")

if __name__ == "__main__":
    asyncio.run(main())
