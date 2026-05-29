# agente_njud.py
"""Portable agent for NJUD locução generation.

This script wraps the existing ``gerar_locucao_multi_speaker.py`` logic but makes all
paths configurable so it can be executed on any machine, regardless of the folder
layout.  It can be used directly as a CLI tool or imported as a module.

Usage examples:

    # Run with defaults (expects the current directory to be the project root)
    python agente_njud.py

    # Specify a custom workspace directory
    python agente_njud.py --workspace "D:\\Projects\\NJUD"

    # Use an explicit configuration file
    python agente_njud.py --config config_njud.json

The configuration file (JSON) can contain the following keys:

    {
        "workspace_dir": "e:/NJUD",
        "src_folder": "roteiros_processados",
        "dest_folder": "locucoes_geradas_tts",
        "vinheta_start": "VH AB - NOTICIAS DA HORA.mp3",
        "vinheta_end": "VH ENC - NOTICIAS DA HORA.mp3",
        "year": 2026
    }

All keys are optional – missing values fall back to the defaults shown above.
"""

import os
import re
import sys
import io
import json
import argparse
import asyncio
from typing import List, Tuple, Optional

import edge_tts
from pydub import AudioSegment

# ---------------------------------------------------------------------------
# Helper functions – copied/adjusted from ``gerar_locucao_multi_speaker.py``
# ---------------------------------------------------------------------------

def load_config(config_path: Optional[str], workspace_override: Optional[str]) -> dict:
    """Load configuration from a JSON file and apply CLI overrides.

    Parameters
    ----------
    config_path: Optional[str]
        Path to a JSON file containing configuration keys.
    workspace_override: Optional[str]
        If provided, replaces the ``workspace_dir`` entry.
    """
    # Default configuration
    config = {
        "workspace_dir": os.getcwd(),
        "src_folder": "roteiros_processados",
        "dest_folder": "locucoes_geradas_tts",
        "vinheta_start": "VH AB - NOTICIAS DA HORA.mp3",
        "vinheta_end": "VH ENC - NOTICIAS DA HORA.mp3",
        "year": 2026,
    }

    if config_path:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
                config.update(file_cfg)
        except Exception as e:
            print(f"[AVISO] Não foi possível ler o arquivo de configuração '{config_path}': {e}")

    if workspace_override:
        config["workspace_dir"] = workspace_override

    # Normalise paths to absolute strings using forward slashes (Windows tolerant)
    config["workspace_dir"] = os.path.abspath(config["workspace_dir"]).replace("\\", "/")
    config["src_base_dir"] = os.path.join(config["workspace_dir"], config["src_folder"]).replace("\\", "/")
    config["dest_base_dir"] = os.path.join(config["workspace_dir"], config["dest_folder"]).replace("\\", "/")
    config["vinheta_start_path"] = os.path.join(config["workspace_dir"], config["vinheta_start"]).replace("\\", "/")
    config["vinheta_end_path"] = os.path.join(config["workspace_dir"], config["vinheta_end"]).replace("\\", "/")
    return config


def extrair_linhas_fala(caminho_txt: str) -> List[Tuple[str, str]]:
    """Extract speech lines from a processed script.

    Returns a list of tuples ``(speaker, text)`` where ``speaker`` is either
    ``speaker1`` or ``speaker2``.
    """
    falas = []
    with open(caminho_txt, "r", encoding="utf-8") as f:
        linhas = f.readlines()
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        match = re.match(r'^(Speaker\s*[12]):\s*(?:\[.*?\])?\s*(.*)$', linha, re.IGNORECASE)
        if match:
            speaker = match.group(1).lower().replace(" ", "")
            texto = match.group(2).strip()
            if texto:
                falas.append((speaker, texto))
    return falas


async def gerar_segmento_audio(texto: str, voz: str) -> bytes:
    """Generate audio bytes for a speech segment using Edge TTS."""
    communicate = edge_tts.Communicate(texto, voz)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data


async def processar_roteiro_completo(caminho_txt: str, caminho_saida: str, cfg: dict) -> bool:
    falas = extrair_linhas_fala(caminho_txt)
    if not falas:
        print("    [AVISO] Nenhuma fala encontrada no arquivo.")
        return False

    VOZ_SPEAKER_1 = "pt-BR-FranciscaNeural"
    VOZ_SPEAKER_2 = "pt-BR-AntonioNeural"

    audio_segmentos = []
    for idx, (speaker, texto) in enumerate(falas):
        voz = VOZ_SPEAKER_1 if speaker == "speaker1" else VOZ_SPEAKER_2
        print(f"       [{idx+1}/{len(falas)}] Gravando {speaker} com voz '{voz}' ({len(texto)} chars)...")
        try:
            segmento_bytes = await gerar_segmento_audio(texto, voz)
            audio_segmentos.append(segimento_bytes)
        except Exception as e:
            print(f"       [ERRO] Falha ao gerar segmento {idx+1}: {e}")
            return False

    # Load vignette files if they exist
    vignette_start = None
    vignette_end = None
    if os.path.exists(cfg["vinheta_start_path"]):
        try:
            vignette_start = AudioSegment.from_mp3(cfg["vinheta_start_path"])
            print("       [INFO] Vinheta de abertura carregada.")
        except Exception as e:
            print(f"       [AVISO] Falha ao carregar vinheta de abertura: {e}")
    if os.path.exists(cfg["vinheta_end_path"]):
        try:
            vignette_end = AudioSegment.from_mp3(cfg["vinheta_end_path"])
            print("       [INFO] Vinheta de encerramento carregada.")
        except Exception as e:
            print(f"       [AVISO] Falha ao carregar vinheta de encerramento: {e}")

    # Convert raw segment bytes to AudioSegment objects
    segments_audio = []
    for seg_bytes in audio_segmentos:
        seg_io = io.BytesIO(seg_bytes)
        segments_audio.append(AudioSegment.from_mp3(seg_io))

    combined = vignette_start if vignette_start else AudioSegment.empty()
    for seg in segments_audio:
        combined += seg
    if vignette_end:
        combined += vignette_end

    # Export final file
    try:
        combined.export(caminho_saida, format="mp3", bitrate="192k")
        return True
    except Exception as e:
        print(f"    [ERRO] Falha ao salvar áudio final: {e}")
        return False


def extrair_numero_episodio(nome_arquivo: str) -> Optional[int]:
    match = re.search(r'(?:NJUD|MJUD|\b)[\s_]*(\d{4})\b', nome_arquivo, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def extrair_data_roteiro(caminho_txt: str, ep: int, year: int) -> Optional[str]:
    try:
        with open(caminho_txt, "r", encoding="utf-8") as f:
            content = f.read()
        # Search for patterns like "NJUD 1826 02-03" or month name
        match = re.search(r'NJUD\s*' + str(ep) + r'\s+([\d]{2}[-/][\d]{2}|[\d]{2}[-/][a-zA-Z]+)', content, re.IGNORECASE)
        date_str = None
        if match:
            date_str = match.group(1)
        else:
            # Fallback: look line‑by‑line for a DD‑MM pattern
            for line in content.split('\n'):
                if str(ep) in line:
                    m = re.search(r'(\d{2}[-/]\d{2})', line)
                    if m:
                        date_str = m.group(1)
                        break
        if date_str:
            date_str = date_str.replace('/', '-')
            day, month = date_str.split('-')
            month_map = {
                'março': '03', 'marco': '03', 'mar': '03',
                'abril': '04', 'abr': '04',
                'maio': '05', 'mai': '05',
                'junho': '06', 'jun': '06',
            }
            month = month_map.get(month.lower(), month)
            return f"{day}-{month}-{year}"
    except Exception as e:
        print(f"    [AVISO] Erro ao extrair data do roteiro {ep}: {e}")
    return None


async def main():
    parser = argparse.ArgumentParser(description="Agente portátil para geração de locuções NJUD.")
    parser.add_argument("--workspace", help="Diretório raiz do projeto (padrão: diretório atual)")
    parser.add_argument("--config", help="Caminho opcional para arquivo JSON de configuração")
    args = parser.parse_args()

    cfg = load_config(args.config, args.workspace)
    print("=== Início da geração de locuções (agente portátil) ===")
    print(f"Workspace: {cfg['workspace_dir']}")
    # Enumerate months – we keep the original list but allow any sub‑folder name
    target_months = os.listdir(cfg["src_base_dir"])
    arquivos_processados = []
    for month_dir in target_months:
        full_month_path = os.path.join(cfg["src_base_dir"], month_dir)
        if not os.path.isdir(full_month_path):
            continue
        for f in os.listdir(full_month_path):
            if f.lower().endswith('.txt'):
                arquivos_processados.append(os.path.join(full_month_path, f))

    if not arquivos_processados:
        print(f"[AVISO] Nenhum roteiro .txt encontrado em {cfg['src_base_dir']}")
        return

    print(f"Encontrados {len(arquivos_processados)} roteiros para processar.")
    sucessos = 0
    for file_path in sorted(arquivos_processados):
        nome_arquivo = os.path.basename(file_path)
        ep = extrair_numero_episodio(nome_arquivo)
        ep_label = f"NJUD {ep}" if ep else nome_arquivo
        date_str = extrair_data_roteiro(file_path, ep, cfg["year"]) if ep else None
        parent_month = os.path.basename(os.path.dirname(file_path))
        dest_month_dir = os.path.join(cfg["dest_base_dir"], parent_month)
        os.makedirs(dest_month_dir, exist_ok=True)
        if ep:
            if date_str:
                caminho_saida = os.path.join(dest_month_dir, f"NJUD_{ep}_{date_str}.mp3")
            else:
                caminho_saida = os.path.join(dest_month_dir, f"NJUD_{ep}.mp3")
        else:
            base_name = os.path.splitext(nome_arquivo)[0]
            caminho_saida = os.path.join(dest_month_dir, f"{base_name}.mp3")
        if os.path.exists(caminho_saida):
            print(f"  - {ep_label} (ignorado, já existe)")
            continue
        print(f"\n* Processando {ep_label} ({parent_month}) …")
        if await processar_roteiro_completo(file_path, caminho_saida, cfg):
            print(f"  [SUCESSO] Áudio salvo em: {caminho_saida}")
            sucessos += 1
        else:
            print(f"  [ERRO] Falha ao gerar {ep_label}")

    print("\n=== GERAÇÃO CONCLUÍDA ===")
    print(f"Novas locuções criadas: {sucessos}")
    print(f"Áudios armazenados em: {cfg['dest_base_dir']}")

if __name__ == "__main__":
    asyncio.run(main())
