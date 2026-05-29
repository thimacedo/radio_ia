"""
gerar_locucao_completo.py
─────────────────────────
Gerador de áudio para roteiros COMPLETOS (com sound design).

Lê os TXT processados por ``processar_roteiro_completo.py`` (que contêm
marcadores de seção) e produz MP3 finais com:
  • Vinheta de abertura
  • BG (trilha de fundo) a 30% na escalada e no encerramento
  • VHT passagem entre matérias
  • Vinheta de encerramento

Dependências:
  pip install edge-tts pydub
  ffmpeg no PATH do sistema
"""

import os
import re
import sys
import io
import asyncio
import argparse
import json

import edge_tts
from pydub import AudioSegment

# ─────────────────────────────────────────────
# CONFIGURAÇÃO PADRÃO
# ─────────────────────────────────────────────

DEFAULT_WORKSPACE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SRC_FOLDER = "roteiros_processados"
DEFAULT_DEST_FOLDER = "locucoes_geradas_tts"
DEFAULT_YEAR = 2026

# Vozes neurais
VOZ_SPEAKER_1 = "pt-BR-FranciscaNeural"
VOZ_SPEAKER_2 = "pt-BR-AntonioNeural"

# ─────────────────────────────────────────────
# ASSETS DE ÁUDIO — HANDLES
# ─────────────────────────────────────────────
# Coloque os arquivos MP3 na raiz do workspace (mesmo diretório deste script).
# Se o arquivo não existir, o programa funciona normalmente sem ele.
#
# Para alterar os nomes, edite as constantes abaixo ou use um config_njud.json:
#   {
#       "vh_abertura":     "NOME_DA_VINHETA_ABERTURA.mp3",
#       "vh_encerramento": "NOME_DA_VINHETA_ENCERRAMENTO.mp3",
#       "bg_escalada":     "NOME_DO_BG.mp3",
#       "vht_passagem":    "NOME_DO_EFEITO_PASSAGEM.mp3"
#   }
# ─────────────────────────────────────────────

# TODO: Atualizar com os nomes corretos dos assets de áudio
ASSET_VH_ABERTURA     = "VH AB - NOTICIAS DA HORA.mp3"         # Vinheta de abertura do programa
ASSET_VH_ENCERRAMENTO = "VH ENC - NOTICIAS DA HORA.mp3"        # Vinheta de encerramento do programa
ASSET_BG_ESCALADA     = "BG - BOLETIM NOTICIAS DA HORA.mp3"    # Trilha de fundo (escalada + encerramento)
ASSET_VHT_PASSAGEM    = "EFEITO - TRILHA BOLETIM NOTICIAS DA HORA.mp3"  # Efeito de transição entre matérias

# Volume do BG (em dB — negativo = mais baixo que o original)
BG_VOLUME_REDUCTION_DB = -12  # aprox. 30% do volume original


# ─────────────────────────────────────────────
# CARREGAR ASSETS DE ÁUDIO
# ─────────────────────────────────────────────

def carregar_asset(workspace, nome_arquivo, label=""):
    """Carrega um asset MP3 como AudioSegment. Retorna None se não encontrar."""
    caminho = os.path.join(workspace, nome_arquivo)
    if os.path.exists(caminho):
        try:
            seg = AudioSegment.from_mp3(caminho)
            print(f"  [ASSET] {label or nome_arquivo} carregado ({len(seg)}ms)")
            return seg
        except Exception as e:
            print(f"  [AVISO] Falha ao carregar {nome_arquivo}: {e}")
    else:
        print(f"  [AVISO] Asset não encontrado: {caminho}")
    return None


# ─────────────────────────────────────────────
# TTS
# ─────────────────────────────────────────────

async def gerar_tts_bytes(texto: str, voz: str) -> bytes:
    """Gera bytes de áudio via Edge TTS."""
    communicate = edge_tts.Communicate(texto, voz)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data


def bytes_to_segment(raw_bytes: bytes) -> AudioSegment:
    """Converte bytes MP3 para AudioSegment."""
    return AudioSegment.from_mp3(io.BytesIO(raw_bytes))


# ─────────────────────────────────────────────
# PARSER DO ROTEIRO PROCESSADO
# ─────────────────────────────────────────────

def parse_roteiro_processado(caminho_txt: str) -> dict:
    """
    Lê um TXT processado e extrai as seções estruturadas.

    Retorna um dict com:
        {
            "header": str,
            "sections": [
                {"type": "ABERTURA", "falas": [("Speaker 1", "texto"), ...]},
                {"type": "ESCALADA", "falas": [...]},
                {"type": "MATERIA",  "falas": [...]},
                {"type": "VHT_PASSAGEM"},
                {"type": "MATERIA",  "falas": [...]},
                {"type": "ENCERRAMENTO", "falas": [...]},
            ]
        }
    """
    with open(caminho_txt, "r", encoding="utf-8") as f:
        linhas = f.readlines()

    result = {"header": "", "sections": []}
    current_section = None

    for linha in linhas:
        linha = linha.rstrip("\r\n")

        # Marcador de seção
        m_section = re.match(r"^\[SECTION:(\w+)\]$", linha)
        if m_section:
            tipo = m_section.group(1)
            current_section = {"type": tipo, "falas": []}
            result["sections"].append(current_section)
            continue

        # Marcador de passagem
        if linha.strip() == "[VHT_PASSAGEM]":
            result["sections"].append({"type": "VHT_PASSAGEM"})
            current_section = None
            continue

        # Fala de speaker
        m_fala = re.match(r"^(Speaker\s*[12]):\s*(?:\[.*?\])?\s*(.*)$", linha, re.IGNORECASE)
        if m_fala and current_section is not None:
            speaker = m_fala.group(1).strip()
            texto = m_fala.group(2).strip()
            if texto:
                current_section["falas"].append((speaker, texto))
            continue

        # Linha de header (não pertence a nenhuma seção)
        if current_section is None and linha.strip():
            result["header"] += linha + "\n"

    return result


# ─────────────────────────────────────────────
# MIXAGEM COM BG
# ─────────────────────────────────────────────

def mixar_com_bg(speech: AudioSegment, bg: AudioSegment, volume_reduction_db: int = BG_VOLUME_REDUCTION_DB) -> AudioSegment:
    """
    Mixa a fala sobre a trilha de fundo (BG).
    O BG é reduzido em volume e repetido/cortado para cobrir a duração da fala.
    """
    bg_low = bg + volume_reduction_db  # reduzir volume

    # Repetir BG se for mais curto que a fala
    duracao_fala = len(speech)
    duracao_bg = len(bg_low)

    if duracao_bg < duracao_fala:
        repeticoes = (duracao_fala // duracao_bg) + 1
        bg_low = bg_low * repeticoes

    # Cortar BG para a duração exata da fala
    bg_low = bg_low[:duracao_fala]

    # Aplicar fade in/out no BG
    bg_low = bg_low.fade_in(500).fade_out(800)

    # Overlay
    return bg_low.overlay(speech)


# ─────────────────────────────────────────────
# GERAÇÃO DE UM PROGRAMA COMPLETO
# ─────────────────────────────────────────────

async def gerar_programa_completo(caminho_txt: str, caminho_saida: str, assets: dict):
    """
    Gera o áudio completo de um programa NJUD com sound design.

    Fluxo:
        [VH Abertura] → Abertura(fala) → [BG + Escalada] → [VHT] →
        Manchete1(S1) + Nota1(S2) → [VHT] → Manchete2(S1) + Nota2(S2) → ... →
        [BG + Encerramento] → [VH Encerramento]
    """
    roteiro = parse_roteiro_processado(caminho_txt)

    if not roteiro["sections"]:
        print("    [AVISO] Nenhuma seção encontrada no roteiro.")
        return False

    # Programa final será montado como sequência de AudioSegments
    programa = AudioSegment.empty()

    # Inserir vinheta de abertura
    if assets.get("vh_abertura"):
        programa += assets["vh_abertura"]

    for section in roteiro["sections"]:
        tipo = section["type"]

        if tipo == "VHT_PASSAGEM":
            # Inserir efeito de passagem
            if assets.get("vht_passagem"):
                programa += assets["vht_passagem"]
            continue

        falas = section.get("falas", [])
        if not falas:
            continue

        # Gerar TTS para todas as falas desta seção
        segmentos_audio = []
        for speaker, texto in falas:
            voz = VOZ_SPEAKER_1 if "1" in speaker else VOZ_SPEAKER_2
            print(f"       [{tipo}] {speaker} ({len(texto)} chars)...")
            try:
                raw = await gerar_tts_bytes(texto, voz)
                segmentos_audio.append(bytes_to_segment(raw))
            except Exception as e:
                print(f"       [ERRO] Falha TTS: {e}")
                return False

        # Concatenar os segmentos desta seção
        speech_section = AudioSegment.empty()
        for seg in segmentos_audio:
            speech_section += seg

        # Aplicar sound design por tipo de seção
        if tipo == "ABERTURA":
            programa += speech_section

        elif tipo == "ESCALADA":
            if assets.get("bg_escalada"):
                programa += mixar_com_bg(speech_section, assets["bg_escalada"])
            else:
                programa += speech_section
            # VHT passagem após a escalada
            if assets.get("vht_passagem"):
                programa += assets["vht_passagem"]

        elif tipo == "MATERIA":
            programa += speech_section

        elif tipo == "ENCERRAMENTO":
            if assets.get("bg_escalada"):
                programa += mixar_com_bg(speech_section, assets["bg_escalada"])
            else:
                programa += speech_section

    # Inserir vinheta de encerramento
    if assets.get("vh_encerramento"):
        programa += assets["vh_encerramento"]

    # Exportar
    try:
        programa.export(caminho_saida, format="mp3", bitrate="192k")
        return True
    except Exception as e:
        print(f"    [ERRO] Falha ao exportar: {e}")
        return False


# ─────────────────────────────────────────────
# EXTRAÇÃO DE EPISÓDIO E DATA DO ROTEIRO
# ─────────────────────────────────────────────

def extrair_info_do_header(caminho_txt: str) -> tuple:
    """Extrai (ep, data_str) do header do roteiro processado."""
    ep = None
    data_str = None
    with open(caminho_txt, "r", encoding="utf-8") as f:
        for linha in f:
            m = re.search(r"NJUD\s*(\d{3,4})\s+(\d{2})-(\d{2})", linha)
            if m:
                ep = int(m.group(1))
                data_str = f"{m.group(2)}-{m.group(3)}-{DEFAULT_YEAR}"
                break
    return ep, data_str


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(
        description="Gerador de locuções NJUD completas com sound design."
    )
    parser.add_argument("--workspace", default=DEFAULT_WORKSPACE, help="Diretório raiz do projeto")
    parser.add_argument("--src", default=DEFAULT_SRC_FOLDER, help="Subpasta dos roteiros processados")
    parser.add_argument("--dest", default=DEFAULT_DEST_FOLDER, help="Subpasta de destino dos áudios")
    parser.add_argument("--single", help="Processar um único arquivo TXT")
    args = parser.parse_args()

    workspace = os.path.abspath(args.workspace)
    src_base = os.path.join(workspace, args.src)
    dest_base = os.path.join(workspace, args.dest)

    print("=== Gerador de Locuções Completas com Sound Design ===\n")
    print(f"Workspace: {workspace}")

    # Carregar assets
    print("\nCarregando assets de áudio...")
    assets = {
        "vh_abertura": carregar_asset(workspace, ASSET_VH_ABERTURA, "Vinheta Abertura"),
        "vh_encerramento": carregar_asset(workspace, ASSET_VH_ENCERRAMENTO, "Vinheta Encerramento"),
        "bg_escalada": carregar_asset(workspace, ASSET_BG_ESCALADA, "BG Escalada"),
        "vht_passagem": carregar_asset(workspace, ASSET_VHT_PASSAGEM, "VHT Passagem"),
    }
    print()

    # Modo arquivo único
    if args.single:
        caminho_txt = args.single if os.path.isabs(args.single) else os.path.join(workspace, args.single)
        if not os.path.exists(caminho_txt):
            print(f"[ERRO] Arquivo não encontrado: {caminho_txt}")
            sys.exit(1)
        ep, data_str = extrair_info_do_header(caminho_txt)
        nome = f"NJUD_{ep}_{data_str}.mp3" if ep and data_str else "saida_completa.mp3"
        caminho_saida = os.path.join(dest_base, nome)
        os.makedirs(dest_base, exist_ok=True)
        print(f"Processando: {caminho_txt}")
        if await gerar_programa_completo(caminho_txt, caminho_saida, assets):
            print(f"\n[SUCESSO] Áudio salvo em: {caminho_saida}")
        else:
            print(f"\n[ERRO] Falha na geração.")
        return

    # Modo lote
    if not os.path.exists(src_base):
        print(f"[ERRO] Pasta de origem não encontrada: {src_base}")
        sys.exit(1)

    # Enumerar subpastas
    subpastas = sorted([
        d for d in os.listdir(src_base)
        if os.path.isdir(os.path.join(src_base, d))
    ])
    if not subpastas:
        subpastas = [""]

    total = 0
    sucessos = 0

    for sub in subpastas:
        src_dir = os.path.join(src_base, sub) if sub else src_base
        dest_dir = os.path.join(dest_base, sub) if sub else dest_base
        os.makedirs(dest_dir, exist_ok=True)

        arquivos = sorted([f for f in os.listdir(src_dir) if f.lower().endswith(".txt")])
        if not arquivos:
            continue

        print(f"\n--- {sub or 'Raiz'}: {len(arquivos)} roteiro(s) ---")

        for arq in arquivos:
            total += 1
            caminho_txt = os.path.join(src_dir, arq)
            ep, data_str = extrair_info_do_header(caminho_txt)

            if ep and data_str:
                nome_saida = f"NJUD_{ep}_{data_str}.mp3"
            elif ep:
                nome_saida = f"NJUD_{ep}.mp3"
            else:
                nome_saida = f"{os.path.splitext(arq)[0]}.mp3"

            caminho_saida = os.path.join(dest_dir, nome_saida)

            if os.path.exists(caminho_saida):
                print(f"  - NJUD {ep or arq} (ignorado, já existe)")
                continue

            print(f"\n* Gerando NJUD {ep or arq} ({sub})...")
            if await gerar_programa_completo(caminho_txt, caminho_saida, assets):
                print(f"  [SUCESSO] {nome_saida}")
                sucessos += 1
            else:
                print(f"  [ERRO] Falha ao gerar {nome_saida}")

    print(f"\n=== GERAÇÃO CONCLUÍDA ===")
    print(f"Novas locuções: {sucessos} de {total}")
    print(f"Destino: {dest_base}")


if __name__ == "__main__":
    asyncio.run(main())
