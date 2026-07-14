import os
import sys

# Certificar caminhos corretos no python path antes de importar core
workspace_dir = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
project_root = os.path.dirname(os.path.dirname(workspace_dir)).replace("\\", "/")
if project_root not in sys.path:
    sys.path.append(project_root)
if workspace_dir not in sys.path:
    sys.path.append(workspace_dir)

# Adicionar a pasta do jornal para importar o processador de roteiro (limpeza)
jornal_dir = os.path.join(os.path.dirname(workspace_dir), "jornal").replace("\\", "/")
if jornal_dir not in sys.path:
    sys.path.append(jornal_dir)

import re
import time
import io
import json
import asyncio
import urllib.request
import pandas as pd
import openpyxl
from core.voice_queue import VoiceQueue
from core.best_practices import retry_async, aplicar_pronuncia, carregar_env_var
from datetime import datetime
from pydub import AudioSegment

try:
    from processar_roteiro_completo import limpar_texto_locutor
except ImportError:
    print("[AVISO] Não foi possível importar 'limpar_texto_locutor' de 'processar_roteiro_completo.py'. Usando fallback simples.")
    def limpar_texto_locutor(texto):
        return texto

# Configuração de caminhos e constantes
SPREADSHEET_ID = "1b1xnzvA00H1JC9uTvd6c-PBwQjEzGRs6t_raXG_ztsU"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=xlsx"
DRIVE_DIR = carregar_env_var("DRIVE_BOLETINS_DIR", r"H:/Meu Drive/RADIO TJRN CONTEÚDO/00_PRODUCAO_2026/07_MODELOS_TUTORIAIS")
LOCAL_BOLETINS_DIR = os.path.join(workspace_dir, "boletins").replace("\\", "/")

def obter_webapp_url():
    try:
        project_root = os.path.dirname(os.path.dirname(workspace_dir))
        env_path = os.path.join(project_root, ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.split("=", 1)
                        if k.strip() == "BOLETINS_WEBAPP_URL":
                            return v.strip()
    except Exception as e:
        print(f"[AVISO] Falha ao carregar URL do Web App: {e}")
    return None

def enviar_atualizacoes_web_app(url, updates):
    import urllib.error
    payload = {
        "action": "update_status",
        "updates": updates
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url, 
        data=data, 
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    )
    try:
        print(f"\n[GDrive] Enviando {len(updates)} atualizações diretamente para a planilha no Google Sheets...")
        with urllib.request.urlopen(req) as response:
            res_content = response.read().decode('utf-8')
            res_json = json.loads(res_content)
            if res_json.get('status') == 'success':
                print(f"[OK] Planilha na nuvem atualizada com sucesso: {res_json.get('message')}")
            else:
                print(f"[AVISO] Falha na resposta do Web App: {res_json.get('message')}")
    except Exception as e:
        print(f"[ERRO] Falha ao conectar com o Apps Script Web App: {e}")

def enviar_trigger_sync_web_app(url, sheet_names):
    import urllib.error
    if not sheet_names:
        sheet_names = [None]
    for sheet_name in sheet_names:
        payload = {
            "action": "trigger_sync"
        }
        if sheet_name:
            payload["sheetName"] = sheet_name
            
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
        )
        try:
            desc = f"para a aba: {sheet_name}" if sheet_name else "para o mês atual"
            print(f"\n[GDrive] Disparando webhook de sincronização da planilha {desc}...")
            with urllib.request.urlopen(req) as response:
                res_content = response.read().decode('utf-8')
                res_json = json.loads(res_content)
                if res_json.get('status') == 'success':
                    print(f"[OK] Sincronização executada com sucesso: {res_json.get('message')}")
                else:
                    print(f"[AVISO] Falha na resposta da sincronização: {res_json.get('message')}")
        except Exception as e:
            print(f"[ERRO] Falha ao conectar para disparar a sincronização: {e}")

try:
    from core.constants import MONTH_MAP_FULL as MONTH_MAP
except ImportError:
    MONTH_MAP = {
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
        12: "12 - DEZEMBRO"
    }

# Carregar assets de áudio
def carregar_audio_asset(caminho, label):
    if os.path.exists(caminho):
        try:
            seg = AudioSegment.from_mp3(caminho)
            print(f"  [ASSET] {label} carregado ({len(seg)}ms)")
            return seg
        except Exception as e:
            print(f"  [ERRO] Falha ao carregar asset {label} ({caminho}): {e}")
    else:
        print(f"  [AVISO] Asset não encontrado: {caminho}")
    return None

# Mapear iniciais do locutor para voz Edge TTS
def obter_config_voz(locutor=None):
    """Return voice identifier and label.
    If `locutor` matches a known explicit code, use the legacy mapping.
    Otherwise, select the next voice from the rotating queue."""
    loc_str = str(locutor).upper() if locutor else ""
    legacy_map = {
        "LEO": ("pt-BR-AntonioNeural", "LEO"),
        "LIV": ("pt-BR-FranciscaNeural", "LIV"),
        "LET": ("pt-BR-FranciscaNeural", "LET"),
        "SIL": ("pt-BR-FranciscaNeural", "SIL"),
    }
    if loc_str in legacy_map:
        return legacy_map[loc_str]
    # Fallback to rotating queue
    voice = VoiceQueue().next_voice()
    # Mapear as vozes de rotação para o padrão de nomenclatura (LEO, LIV, LET)
    voice_to_label = {
        "pt-BR-AntonioNeural": "LEO",
        "pt-BR-FranciscaNeural": "LIV",
        "pt-BR-ElzaNeural": "LET",
        "pt-BR-ThalitaNeural": "LET",
    }
    label = voice_to_label.get(voice, "LIV")
    return voice, label


# Extrair data de criação a partir das colunas do registro
def extrair_data_registro(nome_edicao, data_criacao, caminho):
    if nome_edicao:
        m = re.search(r'BOLETIM_RADIO_TJRN_(\d{2})_(\d{2})_(\d{4})', nome_edicao, re.IGNORECASE)
        if m:
            return int(m.group(1)), int(m.group(2)), int(m.group(3))
            
    if data_criacao:
        if isinstance(data_criacao, datetime):
            return data_criacao.day, data_criacao.month, data_criacao.year
        if isinstance(data_criacao, str):
            m = re.search(r'(\d{4})-(\d{2})-(\d{2})', data_criacao)
            if m:
                return int(m.group(3)), int(m.group(2)), int(m.group(1))
            m = re.search(r'(\d{2})[/-](\d{2})[/-](\d{4})', data_criacao)
            if m:
                return int(m.group(1)), int(m.group(2)), int(m.group(3))
                
    if caminho:
        m = re.search(r'(\d{2})/(\d{2})', str(caminho))
        if m:
            return int(m.group(1)), int(m.group(2)), 2026
            
    return None, None, None

# Baixar roteiro do Google Docs usando a API segura do Drive
def baixar_roteiro_via_api(doc_id):
    try:
        core_dir = os.path.join(os.path.dirname(os.path.dirname(workspace_dir)), "core").replace("\\", "/")
        if core_dir not in sys.path:
            sys.path.append(core_dir)
        from gdoc_exporter import CREDENTIALS_PATH, _build_drive_service
        import io
        from googleapiclient.http import MediaIoBaseDownload
        
        service = _build_drive_service(CREDENTIALS_PATH)
        request = service.files().export_media(
            fileId=doc_id,
            mimeType="text/plain",
        )
        
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return fh.getvalue().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"      [AVISO] Erro no download via API da Conta de Serviço: {e}")
        return None

# Baixar e parsear Google Doc do roteiro
def baixar_e_parsear_roteiro(url):
    if os.path.exists(url) and os.path.isfile(url):
        print(f"      [INFO] Lendo roteiro local diretamente: {url}")
        with open(url, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    else:
        m = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
        if not m:
            raise ValueError("URL do Google Doc inválida.")
        doc_id = m.group(1)
        
        # 1. Tentar download seguro via API da Conta de Serviço
        content = baixar_roteiro_via_api(doc_id)
        
        # 2. Fallback público via urllib se a API falhar
        if not content:
            print("      [INFO] Tentando download público via urllib...")
            export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
            req = urllib.request.Request(export_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                content = response.read().decode('utf-8-sig', errors='ignore')
        
    lines = content.split('\n')
    cabeca_lines = []
    off_lines = []
    
    in_cabeca = False
    in_off = False
    
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            continue
            
        if re.match(r'^(?:cabeça|cabeca|cab)\b', line_strip, re.IGNORECASE):
            in_cabeca = True
            in_off = False
            parts = re.split(r'^(?:cabeça|cabeca|cab)\s*:?\s*', line_strip, flags=re.IGNORECASE)
            if len(parts) > 1 and parts[1].strip():
                cabeca_lines.append(parts[1].strip())
            continue
            
        if re.match(r'^off\b', line_strip, re.IGNORECASE):
            in_off = True
            in_cabeca = False
            parts = re.split(r'^off\s*:?\s*', line_strip, flags=re.IGNORECASE)
            if len(parts) > 1 and parts[1].strip():
                off_lines.append(parts[1].strip())
            continue
            
        if in_cabeca:
            cabeca_lines.append(line_strip)
        elif in_off:
            off_lines.append(line_strip)
            
    cabeca_text = " ".join(cabeca_lines).strip()
    off_text = " ".join(off_lines).strip()
    
    # Fallback simples caso não encontre marcadores estruturados
    if not cabeca_text and not off_text:
        # Tenta dividir ao meio ou assume tudo como OFF
        print("    [AVISO] Roteiro sem marcadores estruturados. Tentando fallback.")
        off_text = " ".join([l.strip() for l in lines if l.strip()]).strip()
        
    return cabeca_text, off_text

# Gerar bytes de áudio via Edge TTS com retry
@retry_async(retries=3, backoff=1.0)
async def gerar_tts_com_retry(text, voice, rate="+0%"):
    import edge_tts
    text_fonetizado = aplicar_pronuncia(text)
    communicate = edge_tts.Communicate(text_fonetizado, voice, rate=rate)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    if not audio_data:
        raise Exception("Nenhum dado de áudio retornado pelo Edge TTS.")
    return audio_data

# Mixar Mailing com Trilha de Fundo a 20% do volume original (-14 dB)
def mixar_mailing_com_bg(mailing_audio, bg_audio):
    bg_low = bg_audio - 14  # Redução para 20% do volume
    dur_mailing = len(mailing_audio)
    dur_bg = len(bg_low)
    
    if dur_bg < dur_mailing:
        repeats = (dur_mailing // dur_bg) + 1
        bg_low = bg_low * repeats
        
    bg_low = bg_low[:dur_mailing]
    bg_low = bg_low.fade_in(500).fade_out(800)
    
    return bg_low.overlay(mailing_audio)

# Função central para processar uma pendência
async def processar_boletim(row_idx, row_data, assets, test_mode):
    caminho_col = row_data[0]
    nome_arquivo = row_data[1]
    locutor_col = row_data[3]
    nome_edicao = row_data[6]
    url_doc = row_data[7]
    data_criacao_col = row_data[8]
    
    voice_name, speaker_name = obter_config_voz(locutor_col)
    print(f"\n* Processando linha {row_idx}: {nome_arquivo}")
    
    # 1. Resolver datas e subpastas
    day, month_num, year = extrair_data_registro(nome_edicao, data_criacao_col, caminho_col)
    if not day or not month_num:
        print(f"  [ERRO] Não foi possível resolver a data para a linha {row_idx}.")
        return False
        
    month_name = MONTH_MAP.get(month_num)
    if not month_name:
        print(f"  [ERRO] Mês inválido: {month_num}")
        return False
        
    day_str = str(day).zfill(2)
    
    # 2. Definir caminhos locais de saída
    dia_dir = os.path.join(LOCAL_BOLETINS_DIR, month_name, day_str)
    mailing_dir = os.path.join(dia_dir, "mailing")
    edit_dir = os.path.join(dia_dir, "edit")
    
    os.makedirs(mailing_dir, exist_ok=True)
    os.makedirs(edit_dir, exist_ok=True)
    
    filename_base = nome_edicao if nome_edicao else f"BOLETIM_{day_str}_{month_num}_{year}_{row_idx}"
    txt_saida_path = os.path.join(dia_dir, f"{filename_base}.txt")
    mailing_saida_path = os.path.join(mailing_dir, f"{filename_base}.mp3")
    edit_saida_path = os.path.join(edit_dir, f"{filename_base}.mp3")
    
    # Verificar se já processamos localmente para evitar reprocessamento
    if os.path.exists(mailing_saida_path) and os.path.exists(edit_saida_path) and os.path.exists(txt_saida_path):
        print(f"  - {filename_base} (ignorado, áudios e texto já existem)")
        return speaker_name
    
    # 3. Baixar roteiro e parsear
    print(f"  -> Baixando roteiro: {url_doc[:50]}...")
    try:
        cabeca_raw, off_raw = baixar_e_parsear_roteiro(url_doc)
    except Exception as e:
        print(f"  [ERRO] Falha ao baixar ou estruturar roteiro: {e}")
        return False
        
    # Salvar script bruto em txt no diretório do dia
    with open(txt_saida_path, "w", encoding="utf-8") as f:
        f.write(f"CABEÇA:\n{cabeca_raw}\n\nOFF:\n{off_raw}\n")
    print(f"  -> Roteiro em texto salvo em: {txt_saida_path}")
    
    # 4. Limpeza e normalização do texto
    cabeca_limpa = limpar_texto_locutor(cabeca_raw)
    off_limpa = limpar_texto_locutor(off_raw)
    
    # 5. Voz e geração TTS
    print(f"  -> Gravando com a voz '{voice_name}' (Iniciais: {speaker_name})")
    
    try:
        # Gravar Cabeça (rate="+0%" para entonação firme)
        cabeca_bytes = b""
        if cabeca_limpa:
            print("     [TTS] Sintetizando Cabeça...")
            cabeca_bytes = await gerar_tts_com_retry(cabeca_limpa, voice_name, rate="+0%")
            
        # Gravar OFF (rate="+4%" para entonação jornalística)
        off_bytes = b""
        if off_limpa:
            print("     [TTS] Sintetizando OFF...")
            off_bytes = await gerar_tts_com_retry(off_limpa, voice_name, rate="+4%")
    except Exception as e:
        print(f"  [ERRO] Falha na síntese de voz (TTS): {e}")
        return False
        
    # 6. Mixagem de Áudio com Pydub
    try:
        # Converter bytes para AudioSegments
        cabeca_seg = AudioSegment.from_mp3(io.BytesIO(cabeca_bytes)) if cabeca_bytes else AudioSegment.empty()
        off_seg = AudioSegment.from_mp3(io.BytesIO(off_bytes)) if off_bytes else AudioSegment.empty()
        
        # Montar Mailing: Cabeça + Passage Vignette + OFF
        print("  -> Mixando versão Mailing...")
        vht_passagem = assets["vht_passagem"]
        
        # Se houver apenas cabeça ou apenas off, lida elegantemente
        mailing_audio = AudioSegment.empty()
        if cabeca_seg and off_seg:
            mailing_audio = cabeca_seg + vht_passagem + off_seg
        elif cabeca_seg:
            mailing_audio = cabeca_seg
        else:
            mailing_audio = off_seg
            
        # Exportar Mailing a 192k
        mailing_audio.export(mailing_saida_path, format="mp3", bitrate="192k")
        print(f"  [OK] Mailing gerado em: {mailing_saida_path}")
        
        # Montar Editada: Abertura Vignette + Cabeça + Passagem Vignette + (OFF mixado com BG a 20%) + Encerramento Vignette
        print("  -> Mixando versão Editada (com Trilha de Fundo a 20% apenas no OFF e Vinhetas)...")
        vht_abertura = assets["vht_abertura"]
        vht_encerramento = assets["vht_encerramento"]
        bg_boletim = assets["bg_boletim"]
        
        # Mixar apenas o OFF com a trilha de fundo se houver OFF
        if off_seg:
            off_mixed = mixar_mailing_com_bg(off_seg, bg_boletim)
        else:
            off_mixed = AudioSegment.empty()
            
        # Concatenação final
        edit_audio = vht_abertura
        if cabeca_seg and off_seg:
            edit_audio = edit_audio + cabeca_seg + vht_passagem + off_mixed
        elif cabeca_seg:
            edit_audio = edit_audio + cabeca_seg
        else:
            edit_audio = edit_audio + off_mixed
            
        edit_audio = edit_audio + vht_encerramento
        
        # Exportar Editada a 192k
        edit_audio.export(edit_saida_path, format="mp3", bitrate="192k")
        print(f"  [OK] Editada gerada em: {edit_saida_path}")
        
    except Exception as e:
        print(f"  [ERRO] Falha no processamento ou exportação de áudio: {e}")
        return False

# Funções auxiliares para auto-descoberta física
def extrair_url_de_gdoc_local(filepath):
    try:
        import json
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("url")
    except Exception:
        pass
    return None

def buscar_pendencias_boletins_drive(drive_root):
    print("\n[Mapeamento Físico] Varrendo pastas de Boletins no Google Drive...")
    path_roteiros_base = os.path.join(drive_root, "00_PRODUCAO_2026", "01_BOLETINS_DIARIOS", "01_ROTEIROS").replace("\\", "/")
    path_mailing_base = os.path.join(drive_root, "00_PRODUCAO_2026", "01_BOLETINS_DIARIOS", "02_AUDIOS_MAILING").replace("\\", "/")
    path_radio_base = os.path.join(drive_root, "00_PRODUCAO_2026", "01_BOLETINS_DIARIOS", "03_AUDIOS_RADIO").replace("\\", "/")
    
    pendencias_fisicas = []
    
    if not os.path.exists(path_roteiros_base):
        print(f"  [AVISO] Pasta base de roteiros de Boletins não encontrada: {path_roteiros_base}")
        return []
        
    from core.constants import MONTH_MAP_FULL
    
    try:
        for mes_folder in os.listdir(path_roteiros_base):
            mes_path = os.path.join(path_roteiros_base, mes_folder).replace("\\", "/")
            if not os.path.isdir(mes_path):
                continue
                
            m_mes = re.match(r'(\d+)\s*-', mes_folder)
            if not m_mes:
                continue
            mes_num = int(m_mes.group(1))
            
            sheet_name = MONTH_MAP_FULL.get(mes_num, f"{mes_num} - MES")
            
            for dia_folder in os.listdir(mes_path):
                dia_path = os.path.join(mes_path, dia_folder).replace("\\", "/")
                if not os.path.isdir(dia_path):
                    continue
                    
                m_dia = re.match(r'(\d+)\s+(\d+)', dia_folder)
                if not m_dia:
                    continue
                dia_num = int(m_dia.group(1))
                
                for file_name in os.listdir(dia_path):
                    file_path = os.path.join(dia_path, file_name).replace("\\", "/")
                    if not os.path.isfile(file_path):
                        continue
                        
                    if file_name.startswith("desktop.ini") or file_name.startswith("."):
                        continue
                        
                    suffix = os.path.splitext(file_name)[1].lower()
                    if suffix not in [".gdoc", ".txt"]:
                        continue
                        
                    nome_base = os.path.splitext(file_name)[0]
                    
                    audio_mailing_path = os.path.join(path_mailing_base, mes_folder, dia_folder, f"{nome_base}.mp3").replace("\\", "/")
                    audio_radio_path = os.path.join(path_radio_base, mes_folder, dia_folder, f"{nome_base}.mp3").replace("\\", "/")
                    
                    if os.path.exists(audio_mailing_path) or os.path.exists(audio_radio_path):
                        continue
                        
                    url_doc = ""
                    if suffix == ".gdoc":
                        url_doc = extrair_url_de_gdoc_local(file_path)
                    elif suffix == ".txt":
                        url_doc = file_path
                        
                    if not url_doc:
                        continue
                        
                    caminho_col = f"{dia_num:02d}/{mes_num:02d}"
                    locutor = ""
                    if "B1" in nome_base or "B3" in nome_base or "B5" in nome_base:
                        locutor = "LIV"
                    elif "B2" in nome_base or "B4" in nome_base:
                        locutor = "LEO"
                        
                    row_data = [
                        caminho_col,
                        nome_base,
                        "Pendente",
                        locutor,
                        "THI",
                        "",
                        nome_base,
                        url_doc,
                        datetime.now()
                    ]
                    
                    pendencias_fisicas.append((sheet_name, 9999, row_data))
                    print(f"  [PENDÊNCIA DETECTADA VIA DRIVE] Roteiro: '{nome_base}' -> Sem áudio correspondente.")
    except Exception as e_scan:
        print(f"  [ERRO] Falha ao varrer pastas físicas do Drive para Boletins: {e_scan}")
        
    return pendencias_fisicas

# Execução do pipeline principal
async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Centralizador de Gravação Automática de Boletins via TTS.")
    parser.add_argument("--test", action="store_true", help="Executa apenas uma gravação de teste.")
    args = parser.parse_args()
    
    print("=== Processador Central de Boletins Rádio TJRN — Início ===")
    
    # 2. Carregar vinhetas e BG do boletim
    vht_abertura_path = os.path.join(LOCAL_BOLETINS_DIR, "VHT/vht_abertura.mp3").replace("\\", "/")
    vht_encerramento_path = os.path.join(LOCAL_BOLETINS_DIR, "VHT/vht_encerramento.mp3").replace("\\", "/")
    vht_passagem_path = os.path.join(LOCAL_BOLETINS_DIR, "VHT/vht_passagem.mp3").replace("\\", "/")
    bg_boletim_path = os.path.join(LOCAL_BOLETINS_DIR, "VHT/bg_boletim.mp3").replace("\\", "/")
    
    print("\nCarregando assets de áudio para boletins...")
    assets = {
        "vht_abertura": carregar_audio_asset(vht_abertura_path, "Abertura"),
        "vht_encerramento": carregar_audio_asset(vht_encerramento_path, "Encerramento"),
        "vht_passagem": carregar_audio_asset(vht_passagem_path, "Passagem"),
        "bg_boletim": carregar_audio_asset(bg_boletim_path, "BG Trilha")
    }
    
    if not all(assets.values()):
        print("[ERRO CRÍTICO] Algum asset de áudio essencial não pôde ser carregado. Abortando.")
        sys.exit(1)
        
    pendencias = []
    
    # 3. Varredura Física (Fonte da Verdade Única)
    pendencias_drive = buscar_pendencias_boletins_drive(DRIVE_DIR.split("/00_PRODUCAO_2026")[0]) # Obtém o DRIVE_ROOT
    pendencias.extend(pendencias_drive)
            
    if not pendencias:
        print("\n[INFO] Nenhuma pendência de Boletins encontrada! Tudo finalizado.")
        print("[PRODUCAO_COUNT] 0")
        sys.exit(0)
        
    print(f"\nTotal de pendências detectadas nos Boletins: {len(pendencias)}")
    
    if args.test:
        print("\n*** MODO DE TESTE ATIVO — Processando apenas 1 pendência ***")
        pendencias = pendencias[:1]
        
    sucessos = 0
    
    sem = asyncio.Semaphore(4)
    
    async def processar_com_sem(sheet_name, row_idx, row_data):
        async with sem:
            try:
                speaker_result = await processar_boletim(row_idx, row_data, assets, args.test)
                if speaker_result:
                    await asyncio.sleep(1.0)
                    return sheet_name, row_idx, row_data, speaker_result
            except Exception as e:
                print(f"  [ERRO] Falha crítica ao processar linha {row_idx} ({sheet_name}): {e}")
            return None

    print(f"Iniciando processamento concorrente de {len(pendencias)} pendências...")
    tasks = [processar_com_sem(s_name, r_idx, r_data) for s_name, r_idx, r_data in pendencias]
    results = await asyncio.gather(*tasks)
    
    for res in results:
        if res:
            sucessos += 1
            
    print(f"\n=== PROCESSAMENTO FINALIZADO: {sucessos} de {len(pendencias)} concluídos ===")
    
    # 5. Sincronizar os áudios e textos gerados com as pastas do Drive
    if not args.test and sucessos > 0:
        try:
            from sincronizar_boletins_drive import sincronizar
            sincronizar()
        except Exception as e:
            print(f"[ERRO] Falha ao executar sincronização com o Drive: {e}")
            
    # Limpar lixo do workspace local (padrão 5S)
    try:
        if os.path.exists(LOCAL_BOLETINS_DIR):
            for item in os.listdir(LOCAL_BOLETINS_DIR):
                item_path = os.path.join(LOCAL_BOLETINS_DIR, item)
                if os.path.isdir(item_path) and item.upper() != "VHT":
                    import shutil
                    shutil.rmtree(item_path)
            print("  [LIMPEZA 5S] Lixo local limpo no workspace de Boletins.")
    except Exception as e_clean:
        print(f"  [AVISO] Falha ao limpar workspace local de Boletins: {e_clean}")
                
    print(f"\n[PRODUCAO_COUNT] {sucessos}")
    print("\n=== PIPELINE CONCLUÍDO ===")

if __name__ == "__main__":
    asyncio.run(main())
