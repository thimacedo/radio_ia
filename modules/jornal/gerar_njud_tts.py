import os
import sys
import re
import io
import asyncio
import urllib.request
import openpyxl
import shutil
from pydub import AudioSegment
import shutil

# Certificar caminhos corretos no python path
current_dir = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
project_root = os.path.dirname(os.path.dirname(current_dir)).replace("\\", "/")
sys.path.append(project_root)
sys.path.append(current_dir)

from core.llm_factory import LLMFactory
from processar_roteiro_completo import limpar_texto_locutor
from core.best_practices import carregar_env_var
from core.constants import MONTH_MAP_SHORT, MONTH_MAP_FULL, ANO_SHORT, extrair_mes_num_de_caminho

DRIVE_ROOT = carregar_env_var("DRIVE_ROOT", "H:/Meu Drive/RADIO TJRN CONTEÚDO")

from core.best_practices import carregar_env_var

# Configurações
PATH_PLANILHA = os.path.join(DRIVE_ROOT, "NOT JUDICIARIO (5 MIN)", "NJUD 2026.xlsx").replace("\\", "/")
LOCAL_WORKSPACE = os.path.join(current_dir, "workspace").replace("\\", "/")
GLOBAL_VHT_DIR = os.path.join(project_root, "assets/vht").replace("\\", "/")
DRIVE_BASE_DIR = os.path.join(DRIVE_ROOT, "00_PRODUCAO_2026", "02_JORNAIS_NJUD").replace("\\", "/")

def baixar_roteiro_via_api(doc_id):
    try:
        core_dir = os.path.join(project_root, "core").replace("\\", "/")
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

SYSTEM_PROMPT = """Você é um especialista em edição de roteiros de radiojornalismo. O objetivo é processar roteiros técnicos e entregá-los formatados para síntese de voz de bancada (locução alternada), mantendo TODO o conteúdo de notícias e aplicando diretrizes de rádio.

REGRAS:
1. Sem formatação Markdown.
2. NUNCA reduza ou resuma o conteúdo do roteiro. Mantenha todas as informações completas. O texto original é composto por Notas de Introdução (LOC/LOC 2) e corpos de matérias detalhadas (OFF/CONTEÚDO). Você deve integrar o texto da introdução com o respectivo corpo da matéria para cada NOTA.
3. Divida o roteiro final estritamente nas seguintes seções usando cabeçalhos entre colchetes:
   - [ESCALADA]: Contém a acolhida inicial (Olá, confira os destaques...) e a leitura de todos os destaques (manchetes).
   - [NOTA 1]: Contém a primeira notícia completa (a fusão da introdução LOC1 e do corpo da matéria OFF correspondente).
   - [NOTA 2]: Contém a segunda notícia completa (introdução + corpo).
   - [NOTA 3]: Contém a terceira notícia completa (introdução + corpo).
   - [NOTA 4]: Contém a quarta notícia completa (introdução + corpo).
   - [ENCERRAMENTO]: Contém o encerramento completo do programa (E o Notícias do Judiciário termina aqui...).
4. Dentro de cada seção, substitua as marcações originais de locutores por falas alternadas e fluidas entre:
   Speaker 1: [texto da fala]
   Speaker 2: [texto da fala]
   A Escalada deve começar obrigatoriamente com o Speaker 1. Alternar as falas a cada parágrafo ou frase para dar dinâmica de bancada.
5. NUNCA permita que os apresentadores se apresentem ou digam seus nomes ou codinomes (ex: "eu sou o Speaker 1", "sou o apresentador virtual", "aqui fala o locutor", etc.). Se houver apresentações desse tipo no texto original, remova-as e inicie direto com "Olá".
6. Escrever números, valores, porcentagens, datas e horas por extenso.
7. Escrever siglas letra por letra separadas por espaço (ex: t j r n).
8. Sites de forma literal (ex: t j r n ponto jus ponto b r).
9. Linguagem simples e direta de rádio.
"""

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

def obter_id_documento(url):
    if os.path.exists(url) and os.path.isfile(url):
        return "local_file"
    m = re.search(r'/d/([a-zA-Z0-9_-]{25,})', str(url))
    if m:
        return m.group(1)
    return None

def lines_to_falas(linhas):
    falas = []
    for linha in linhas:
        match = re.match(r'^(Speaker\s*[12]):\s*(?:\[.*?\])?\s*(.*)$', linha, re.IGNORECASE)
        if match:
            speaker = match.group(1).lower().replace(" ", "")
            texto = match.group(2).strip()
            if texto:
                falas.append((speaker, texto))
    return falas

def separar_secoes(texto_revisado):
    secoes = {}
    secao_atual = None
    linhas_secao = []
    
    for linha in texto_revisado.splitlines():
        linha = linha.strip()
        if not linha:
            continue
        
        # Procura por marcas como [ESCALADA], [NOTA 1], [NOTA 2], [NOTA 3], [NOTA 4], [ENCERRAMENTO]
        m = re.match(r'^\[\s*(ESCALADA|NOTA\s*\d+|ENCERRAMENTO)\s*\]$', linha, re.IGNORECASE)
        if m:
            if secao_atual:
                secoes[secao_atual] = lines_to_falas(linhas_secao)
            secao_atual = m.group(1).upper().replace(" ", "")
            linhas_secao = []
        else:
            linhas_secao.append(linha)
            
    if secao_atual and linhas_secao:
        secoes[secao_atual] = lines_to_falas(linhas_secao)
        
    return secoes

def mix_voice_with_bg(voice_segment, bg_segment, bg_volume_db=-20):
    if len(voice_segment) == 0:
        return AudioSegment.empty()
        
    fade_in_ms = 1500
    fade_out_ms = 1500
    
    # Duração total = Duração da voz + tempo de fade out da trilha
    total_len = len(voice_segment) + fade_out_ms + 1000 # 1s extra no final
    
    # Garantir que a trilha cobre o tamanho total (loop se necessário)
    bg_sub = bg_segment[:total_len]
    if len(bg_sub) < total_len:
        bg_sub = (bg_segment * (total_len // len(bg_segment) + 1))[:total_len]
        
    # Aplicar volume ducking
    bg_sub = bg_sub + bg_volume_db
    
    # Fades
    bg_sub = bg_sub.fade_in(fade_in_ms)
    bg_sub = bg_sub.fade_out(fade_out_ms)
    
    # Inicia a voz 1 segundo após a trilha começar (efeito rádio profissional)
    voice_start = 1000
    mixed = bg_sub.overlay(voice_segment, position=voice_start)
    
    return mixed

async def gerar_tts_com_retry(text, voice):
    import edge_tts
    for tentativa in range(3):
        try:
            communicate = edge_tts.Communicate(text, voice)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            if audio_data:
                return audio_data
        except Exception as e:
            print(f"      [AVISO] Falha na geração do áudio TTS (tentativa {tentativa+1}): {e}")
            await asyncio.sleep(2)
    raise Exception("Falha de rede ou de serviço com Edge TTS.")

async def processar_jornal(row_idx, row_data, assets, llm, test_mode):
    caminho_col = row_data[0] # Ex: 6 - JUNHO
    nome_arquivo = row_data[1] # Ex: NJUD 1887
    url_doc = row_data[2] # Link do Google Doc
    
    print(f"\n* Processando linha {row_idx}: {nome_arquivo}")
    
    # 1. Obter ID do Documento
    doc_id = obter_id_documento(url_doc)
    if not doc_id:
        print(f"  [ERRO] Link do documento inválido na linha {row_idx}: {url_doc}")
        return False
        
    # 2. Criar diretórios locais
    txt_bruto_dir = os.path.join(LOCAL_WORKSPACE, "1_txt_bruto").replace("\\", "/")
    txt_revisado_dir = os.path.join(LOCAL_WORKSPACE, "2_txt_revisado").replace("\\", "/")
    audio_final_dir = os.path.join(LOCAL_WORKSPACE, "3_audio_final").replace("\\", "/")
    
    os.makedirs(txt_bruto_dir, exist_ok=True)
    os.makedirs(txt_revisado_dir, exist_ok=True)
    os.makedirs(audio_final_dir, exist_ok=True)
    
    sufixo_data = row_data[3] if len(row_data) > 3 else ""
    filename_base = f"{nome_arquivo} {sufixo_data}" if sufixo_data else f"{nome_arquivo} LOC"
    txt_bruto_path = os.path.join(txt_bruto_dir, f"{filename_base}_bruto.txt")
    txt_revisado_path = os.path.join(txt_revisado_dir, f"{filename_base}.txt")
    audio_saida_path = os.path.join(audio_final_dir, f"{filename_base}.mp3")
    
    # Verificar se já processamos localmente para evitar reprocessamento
    if os.path.exists(audio_saida_path) and os.path.exists(txt_revisado_path):
        print(f"  - {filename_base} (ignorado, áudio e texto revisado já existem localmente)")
        return True
        
    # 3. Baixar roteiro bruto
    roteiro_bruto = None
    if doc_id == "local_file":
        print(f"  -> Lendo roteiro local diretamente de: {url_doc}")
        try:
            with open(url_doc, "r", encoding="utf-8", errors="ignore") as f:
                roteiro_bruto = f.read()
        except Exception as e:
            print(f"  [ERRO] Falha ao ler roteiro local: {e}")
            return False
    else:
        print(f"  -> Baixando roteiro técnico do Google Docs...")
        roteiro_bruto = baixar_roteiro_via_api(doc_id)
        if not roteiro_bruto:
            print("  -> Tentando download alternativo...")
            try:
                export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
                req = urllib.request.Request(export_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    roteiro_bruto = response.read().decode('utf-8-sig', errors='ignore')
            except Exception as e:
                print(f"  [ERRO] Falha ao baixar roteiro do Docs (API e fallback): {e}")
                return False
            
    try:
        with open(txt_bruto_path, "w", encoding="utf-8") as f:
            f.write(roteiro_bruto)
        print(f"  -> Roteiro bruto salvo em: {txt_bruto_path}")
    except Exception as e:
        print(f"  [ERRO] Falha ao salvar roteiro bruto: {e}")
        return False
        
    # 4. Processamento via IA (Reescrita Técnica)
    print(f"  -> Revisando roteiro via IA (Orquestração de Bancada)...")
    try:
        roteiro_revisado = llm.ask(SYSTEM_PROMPT, roteiro_bruto)
        with open(txt_revisado_path, "w", encoding="utf-8") as f:
            f.write(roteiro_revisado)
        print(f"  -> Roteiro revisado salvo em: {txt_revisado_path}")
    except Exception as e:
        print(f"  [ERRO] Falha na reescrita de IA: {e}")
        return False
        
    # 5. Extração de falas e geração de áudio por seções
    secoes = separar_secoes(roteiro_revisado)
    
    VOZ_SPEAKER_1 = "pt-BR-FranciscaNeural"
    VOZ_SPEAKER_2 = "pt-BR-AntonioNeural"
    
    # Se conseguimos separar as seções corretamente, fazemos o processamento profissional estruturado
    if secoes and ("ESCALADA" in secoes or any(k.startswith("NOTA") for k in secoes.keys())):
        print("  -> Estrutura por seções detectada. Iniciando gravação estruturada com trilhas e vinhetas...")
        secoes_audio = {}
        
        for secao_nome, falas in secoes.items():
            if not falas:
                continue
            print(f"     * Processando seção [{secao_nome}] ({len(falas)} falas)...")
            
            silence = AudioSegment.silent(duration=450) # 450ms de silêncio entre falas
            combined_voice = AudioSegment.empty()
            
            for idx, (speaker, texto) in enumerate(falas):
                voz = VOZ_SPEAKER_1 if speaker == "speaker1" else VOZ_SPEAKER_2
                
                # Limpar texto do locutor (siglas, ordinais, etc.)
                texto_limpo = limpar_texto_locutor(texto)
                
                # Remover apresentações de codinomes/nomes dos locutores virtuais
                texto_limpo = re.sub(r'\b(?:eu\s+)?sou\s+o\s+speaker\s*[12]\b', '', texto_limpo, flags=re.IGNORECASE)
                texto_limpo = re.sub(r'\b(?:eu\s+)?sou\s+a\s+speaker\s*[12]\b', '', texto_limpo, flags=re.IGNORECASE)
                texto_limpo = re.sub(r'\bapresentador\s+virtual\b', '', texto_limpo, flags=re.IGNORECASE)
                texto_limpo = re.sub(r'\blocutor\s+virtual\b', '', texto_limpo, flags=re.IGNORECASE)
                texto_limpo = re.sub(r'\s+', ' ', texto_limpo).strip()
                texto_limpo = re.sub(r',\s*\.', '.', texto_limpo)
                texto_limpo = re.sub(r'\s*\.', '.', texto_limpo)
                
                if not texto_limpo:
                    continue
                    
                print(f"       [{secao_nome}] Sintetizando fala {idx+1}/{len(falas)} com voz '{voz}'...")
                try:
                    seg_bytes = await gerar_tts_com_retry(texto_limpo, voz)
                    fala_seg = AudioSegment.from_mp3(io.BytesIO(seg_bytes))
                    if len(combined_voice) > 0:
                        combined_voice += silence
                    combined_voice += fala_seg
                except Exception as e:
                    print(f"       [ERRO] Falha na síntese de voz na seção {secao_nome}: {e}")
                    return False
            
            # Mixar a voz da seção com a trilha sonora (se houver trilha e for Escalada, Nota ou Encerramento)
            if len(combined_voice) > 0:
                if assets.get("bg_trilha"):
                    print(f"     * Mixando trilha BG na seção [{secao_nome}]...")
                    secoes_audio[secao_nome] = mix_voice_with_bg(combined_voice, assets["bg_trilha"], bg_volume_db=-20)
                else:
                    secoes_audio[secao_nome] = combined_voice
                    
        # 6. Mixagem de Áudio Final com Vinhetas
        print("  -> Fazendo a montagem final do Jornal com Vinhetas...")
        try:
            combined = AudioSegment.empty()
            
            # 1. Escalada (Destaques)
            if "ESCALADA" in secoes_audio:
                combined += secoes_audio["ESCALADA"]
                combined += AudioSegment.silent(duration=500)
                
            # 2. Vinheta de Abertura
            if assets["abertura"]:
                combined += assets["abertura"]
                combined += AudioSegment.silent(duration=500)
                
            # 3. Notas 1 a 4 com Vinheta de Passagem entre elas
            notas_list = ["NOTA1", "NOTA2", "NOTA3", "NOTA4"]
            added_notas = 0
            
            for i, nota_key in enumerate(notas_list):
                if nota_key in secoes_audio:
                    # Adiciona a vinheta de passagem entre notas
                    if added_notas > 0 and assets["passagem"]:
                        combined += assets["passagem"]
                        combined += AudioSegment.silent(duration=500)
                    combined += secoes_audio[nota_key]
                    combined += AudioSegment.silent(duration=500)
                    added_notas += 1
                    
            # 4. Encerramento
            if "ENCERRAMENTO" in secoes_audio:
                combined += secoes_audio["ENCERRAMENTO"]
                combined += AudioSegment.silent(duration=500)
                
            # 5. Vinheta de Encerramento
            if assets["encerramento"]:
                combined += assets["encerramento"]
                
            # Exportar arquivo final
            combined.export(audio_saida_path, format="mp3", bitrate="192k")
            print(f"  [OK] Áudio final estruturado gerado em: {audio_saida_path}")
            return True
        except Exception as e:
            print(f"  [ERRO] Falha na montagem final do áudio estruturado: {e}")
            return False
            
    else:
        # FALLBACK: Processamento linear antigo
        print("  -> Usando fallback linear (sem estrutura de seções)...")
        falas = lines_to_falas(roteiro_revisado.splitlines())
        if not falas:
            print(f"  [ERRO] Nenhuma fala extraída no modo fallback.")
            return False
            
        audio_segmentos = []
        for idx, (speaker, texto) in enumerate(falas):
            voz = VOZ_SPEAKER_1 if speaker == "speaker1" else VOZ_SPEAKER_2
            texto_limpo = limpar_texto_locutor(texto)
            texto_limpo = re.sub(r'\b(?:eu\s+)?sou\s+o\s+speaker\s*[12]\b', '', texto_limpo, flags=re.IGNORECASE)
            texto_limpo = re.sub(r'\b(?:eu\s+)?sou\s+a\s+speaker\s*[12]\b', '', texto_limpo, flags=re.IGNORECASE)
            texto_limpo = re.sub(r'\bapresentador\s+virtual\b', '', texto_limpo, flags=re.IGNORECASE)
            texto_limpo = re.sub(r'\blocutor\s+virtual\b', '', texto_limpo, flags=re.IGNORECASE)
            texto_limpo = re.sub(r'\s+', ' ', texto_limpo).strip()
            texto_limpo = re.sub(r',\s*\.', '.', texto_limpo)
            texto_limpo = re.sub(r'\s*\.', '.', texto_limpo)
            
            print(f"     [{idx+1}/{len(falas)}] Sintetizando {speaker}...")
            try:
                seg_bytes = await gerar_tts_com_retry(texto_limpo, voz)
                audio_segmentos.append(AudioSegment.from_mp3(io.BytesIO(seg_bytes)))
            except Exception as e:
                print(f"     [ERRO] Falha no fallback: {e}")
                return False
                
        try:
            combined = AudioSegment.empty()
            if assets["abertura"]:
                combined += assets["abertura"]
            for seg in audio_segmentos:
                combined += seg
            if assets["encerramento"]:
                combined += assets["encerramento"]
                
            combined.export(audio_saida_path, format="mp3", bitrate="192k")
            print(f"  [OK] Áudio final fallback gerado em: {audio_saida_path}")
            return True
        except Exception as e:
            print(f"  [ERRO] Falha no fallback de áudio: {e}")
            return False

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Centralizador de Gravação Automática do Jornal NJUD via TTS.")
    parser.add_argument("--test", action="store_true", help="Executa apenas um teste e não altera os arquivos do Drive.")
    args = parser.parse_args()
    
    print("=== Processador Central de Jornal (NJUD) Rádio TJRN — Início ===")
    
    import datetime
    os.makedirs(LOCAL_WORKSPACE, exist_ok=True)
            
    # 2. Carregar assets de áudio (Nomes corrigidos de acordo com o padrão de arquivos do NJUD)
    vht_abertura_path = os.path.join(GLOBAL_VHT_DIR, "NJUD - VHT - ABERTURA.mp3").replace("\\", "/")
    vht_encerramento_path = os.path.join(GLOBAL_VHT_DIR, "NJUD - VHT - ENCERRAMENTO.mp3").replace("\\", "/")
    vht_passagem_path = os.path.join(GLOBAL_VHT_DIR, "NJUD - VHT - PASSAGEM.mp3").replace("\\", "/")
    bg_trilha_path = os.path.join(GLOBAL_VHT_DIR, "NJUD - BG.mp3").replace("\\", "/")
    
    print("\nCarregando vinhetas e trilhas para o NJUD...")
    assets = {
        "abertura": carregar_audio_asset(vht_abertura_path, "Abertura do Jornal"),
        "encerramento": carregar_audio_asset(vht_encerramento_path, "Encerramento do Jornal"),
        "passagem": carregar_audio_asset(vht_passagem_path, "Vinheta de Passagem"),
        "bg_trilha": carregar_audio_asset(bg_trilha_path, "Trilha BG")
    }
    
    # 3. Inicializar fábrica de IA
    llm = LLMFactory()
    
    def obter_caminho_mes(refer_val):
        """Resolve o caminho do mês a partir de um valor de referência."""
        if not refer_val:
            return MONTH_MAP_FULL.get(6, "6 - JUNHO")
        if isinstance(refer_val, datetime.datetime):
            return MONTH_MAP_FULL.get(refer_val.month, "6 - JUNHO")
        # Tenta extrair o número do mês da string
        import re as _re
        m = _re.search(r"(\d{4})[-/](\d{2})[-/]", str(refer_val))
        if m:
            return MONTH_MAP_FULL.get(int(m.group(2)), "6 - JUNHO")
        m2 = _re.search(r"(\d{2})[-/](\d{2})[-/]", str(refer_val))
        if m2:
            return MONTH_MAP_FULL.get(int(m2.group(1)), "6 - JUNHO")
        # Usa o helper de constants se nada casar
        mes_num = extrair_mes_num_de_caminho(str(refer_val))
        return MONTH_MAP_FULL.get(mes_num, "6 - JUNHO")

    def obter_sufixo_data(refer_val):
        if not refer_val:
            return ""
        if isinstance(refer_val, (datetime.datetime, datetime.date)):
            return refer_val.strftime("%d-%m")
        refer_str = str(refer_val).strip()
        
        m = re.search(r'(\d{4})[-/](\d{2})[-/](\d{2})', refer_str)
        if m:
            return f"{m.group(3)}-{m.group(2)}"
           # 4. Funções auxiliares para auto-descoberta de arquivos física
    def extrair_url_de_gdoc_local(filepath):
        try:
            import json
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("url")
        except Exception:
            pass
        return None

    def obter_sufixo_data_do_conteudo(texto_roteiro):
        if not texto_roteiro:
            return ""
        m = re.search(r'PROGRAMA\s*(?:N[\u00ba\u00b0\.]\s*)?\d+\s*\(\s*(\d{2})[\/-](\d{2})\s*\)', texto_roteiro, re.IGNORECASE)
        if m:
            return f"{m.group(1)}-{m.group(2)}"
        m2 = re.search(r'(\d{2})\s*de\s*(janeiro|fevereiro|mar\u00e7o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)', texto_roteiro, re.IGNORECASE)
        if m2:
            meses = ['janeiro', 'fevereiro', 'mar\u00e7o', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
            dia = m2.group(1).zfill(2)
            mes_nome = m2.group(2).lower()
            if mes_nome in meses:
                mes = str(meses.index(mes_nome) + 1).zfill(2)
                return f"{dia}-{mes}"
        return ""

    def buscar_pendencias_njud_drive(drive_root):
        print("\n[Mapeamento Físico] Varrendo pastas de NJUD no Google Drive...")
        path_roteiros_base = os.path.join(drive_root, "00_PRODUCAO_2026", "02_JORNAIS_NJUD", "01_ROTEIROS").replace("\\", "/")
        path_mailing_base = os.path.join(drive_root, "00_PRODUCAO_2026", "02_JORNAIS_NJUD", "02_AUDIOS_MAILING").replace("\\", "/")
        path_radio_base = os.path.join(drive_root, "00_PRODUCAO_2026", "02_JORNAIS_NJUD", "03_AUDIOS_RADIO").replace("\\", "/")
        
        pendencias_fisicas = []
        
        if not os.path.exists(path_roteiros_base):
            print(f"  [AVISO] Pasta base de roteiros do NJUD não encontrada: {path_roteiros_base}")
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
                
                caminho_col = MONTH_MAP_FULL.get(mes_num, f"{mes_num} - MES")
                short_name = MONTH_MAP_SHORT.get(mes_num, "JUN")
                folder_name = f"{mes_num:02d} - {short_name} - {ANO_SHORT}"
                
                for file_name in os.listdir(mes_path):
                    file_path = os.path.join(mes_path, file_name).replace("\\", "/")
                    if not os.path.isfile(file_path):
                        continue
                        
                    if file_name.startswith("desktop.ini") or file_name.startswith("."):
                        continue
                        
                    suffix = os.path.splitext(file_name)[1].lower()
                    if suffix not in [".gdoc", ".txt"]:
                        continue
                        
                    nome_doc = os.path.splitext(file_name)[0]
                    if "NJUD" not in nome_doc.upper():
                        continue
                        
                    url_doc = ""
                    if suffix == ".gdoc":
                        url_doc = extrair_url_de_gdoc_local(file_path)
                    elif suffix == ".txt":
                        url_doc = file_path
                        
                    if not url_doc:
                        continue
                        
                    sufixo_data = ""
                    try:
                        texto_roteiro = ""
                        if suffix == ".txt":
                            with open(file_path, "r", encoding="utf-8", errors="ignore") as f_r:
                                texto_roteiro = f_r.read()
                        else:
                            # Para gdoc, tenta ler via API
                            doc_id = obter_id_documento(url_doc)
                            if doc_id:
                                texto_roteiro = baixar_roteiro_via_api(doc_id) or ""
                        sufixo_data = obter_sufixo_data_do_conteudo(texto_roteiro)
                    except Exception:
                        pass
                        
                    nome_final = f"{nome_doc} {sufixo_data}" if sufixo_data else nome_doc
                    
                    # 1. Verificar na estrutura 5S (Mailing e Rádio)
                    drive_audio_path_5s_mailing = os.path.join(path_mailing_base, folder_name, f"{nome_final}.mp3").replace("\\", "/")
                    drive_audio_path_5s_radio = os.path.join(path_radio_base, folder_name, f"{nome_final}.mp3").replace("\\", "/")
                    
                    # 2. Verificar na estrutura legada
                    drive_audio_path_trad = os.path.join(DRIVE_ROOT, "NOT JUDICIARIO (5 MIN)", "NJUD 2026", caminho_col, "EDITADOS", f"{nome_final}.mp3").replace("\\", "/")
                    drive_audio_path_trad_old = os.path.join(DRIVE_ROOT, "NOT JUDICIARIO (5 MIN)", "NJUD 2026", caminho_col, f"{nome_doc} LOC.mp3").replace("\\", "/")
                    
                    if (os.path.exists(drive_audio_path_5s_mailing) or 
                        os.path.exists(drive_audio_path_5s_radio) or 
                        os.path.exists(drive_audio_path_trad) or 
                        os.path.exists(drive_audio_path_trad_old)):
                        continue
                        
                    normalized_row = (caminho_col, nome_doc, url_doc, sufixo_data)
                    pendencias_fisicas.append((mes_folder, 9999, normalized_row))
        except Exception as e_scan:
            print(f"  [ERRO] Falha ao varrer pastas físicas do Drive para NJUD: {e_scan}")
            
        return pendencias_fisicas

    pendencias = []
    
    # 5. Buscar pendências via varredura de arquivos físicos (Fonte Única)
    pendencias_drive = buscar_pendencias_njud_drive(DRIVE_ROOT)
    pendencias.extend(pendencias_drive)
    
    if not pendencias:
        print("\n[INFO] Nenhuma pendência de gravação encontrada no Jornal NJUD! Todos os jornais já possuem áudio.")
        print("[PRODUCAO_COUNT] 0")
        sys.exit(0)
        
    print(f"\nTotal de pendências detectadas no NJUD: {len(pendencias)}")
    
    if args.test:
        print("\n*** MODO DE TESTE ATIVO — Processando apenas 1 pendência ***")
        pendencias = pendencias[:1]
        
    sucessos = 0
    results = []
    
    sem = asyncio.Semaphore(2)
    
    async def processar_com_sem(sheet_name, row_idx, row_data):
        async with sem:
            try:
                processado = await processar_jornal(row_idx, row_data, assets, llm, args.test)
                if processado:
                    await asyncio.sleep(1.0)
                    return sheet_name, row_idx, row_data
            except Exception as e:
                print(f"  [ERRO] Falha crítica ao processar linha {row_idx} ({sheet_name}): {e}")
            return None
            
    print(f"Iniciando gravação de {len(pendencias)} jornais...")
    tasks = [processar_com_sem(s_name, r_idx, r_data) for s_name, r_idx, r_data in pendencias]
    results_raw = await asyncio.gather(*tasks)
    
    for res in results_raw:
        if res:
            sucessos += 1
            results.append(res)
                
    print(f"\n=== PROCESSAMENTO FINALIZADO: {sucessos} de {len(pendencias)} concluídos ===")
    
    # 5. Sincronizar com o Drive (apenas se não for teste e houver sucessos)
    if not args.test and sucessos > 0:
        print("\nSincronizando áudios e roteiros do NJUD com o Google Drive...")
        total_sincronizados = 0
        for sheet_name, r_idx, row_data in results:
            caminho_col = row_data[0]
            nome_arquivo = row_data[1]
            sufixo_data = row_data[3] if len(row_data) > 3 else ""
            
            filename_base = f"{nome_arquivo} {sufixo_data}" if sufixo_data else f"{nome_arquivo} LOC"
            local_audio_file = os.path.join(LOCAL_WORKSPACE, f"3_audio_final/{filename_base}.mp3").replace("\\", "/")
            local_txt_file = os.path.join(LOCAL_WORKSPACE, f"2_txt_revisado/{filename_base}.txt").replace("\\", "/")
            
            try:
                mes_num = 6
                m_mes = re.search(r'(\d+)', caminho_col)
                if m_mes:
                    mes_num = int(m_mes.group(1))
                    
                short_name = MONTH_MAP_SHORT.get(mes_num, "JUN")
                folder_name = f"{mes_num:02d} - {short_name} - {ANO_SHORT}"
                
                drive_5s_base = os.path.join(DRIVE_ROOT, "00_PRODUCAO_2026", "02_JORNAIS_NJUD").replace("\\", "/")
                drive_5s_roteiros_dir = os.path.join(drive_5s_base, "01_ROTEIROS", folder_name).replace("\\", "/")
                drive_5s_mailing_dir = os.path.join(drive_5s_base, "02_AUDIOS_MAILING", folder_name).replace("\\", "/")
                drive_5s_radio_dir = os.path.join(drive_5s_base, "03_AUDIOS_RADIO", folder_name).replace("\\", "/")
                
                os.makedirs(drive_5s_roteiros_dir, exist_ok=True)
                os.makedirs(drive_5s_mailing_dir, exist_ok=True)
                os.makedirs(drive_5s_radio_dir, exist_ok=True)
                
                drive_5s_txt_path = os.path.join(drive_5s_roteiros_dir, f"{filename_base}.txt").replace("\\", "/")
                drive_5s_audio_path_mailing = os.path.join(drive_5s_mailing_dir, f"{filename_base}.mp3").replace("\\", "/")
                drive_5s_audio_path_radio = os.path.join(drive_5s_radio_dir, f"{filename_base}.mp3").replace("\\", "/")
                
                if os.path.exists(local_txt_file):
                    shutil.copy2(local_txt_file, drive_5s_txt_path)
                    print(f"  [ROTEIRO 5S] Copiado para: {drive_5s_txt_path}")
                    total_sincronizados += 1
                    
                if os.path.exists(local_audio_file):
                    shutil.copy2(local_audio_file, drive_5s_audio_path_mailing)
                    print(f"  [ÁUDIO MAILING 5S] Copiado para: {drive_5s_audio_path_mailing}")
                    total_sincronizados += 1
                    
                if os.path.exists(local_audio_file):
                    shutil.copy2(local_audio_file, drive_5s_audio_path_radio)
                    print(f"  [ÁUDIO RÁDIO 5S] Copiado para: {drive_5s_audio_path_radio}")
                    total_sincronizados += 1
            except Exception as e_5s:
                print(f"  [ERRO] Falha ao sincronizar na nova estrutura 5S: {e_5s}")
                
        print(f"Sincronização com o Drive concluída! Total de arquivos copiados: {total_sincronizados}")
        
    # Limpar lixo do workspace local (padrão 5S)
    try:
        for folder in ["1_txt_bruto", "2_txt_revisado", "3_audio_final"]:
            dir_to_clean = os.path.join(LOCAL_WORKSPACE, folder)
            if os.path.exists(dir_to_clean):
                for filename in os.listdir(dir_to_clean):
                    file_path = os.path.join(dir_to_clean, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
        print("  [LIMPEZA 5S] Lixo local limpo no workspace de NJUD.")
    except Exception as e_clean:
        print(f"  [AVISO] Falha ao limpar workspace local: {e_clean}")
        
    print(f"\n[PRODUCAO_COUNT] {sucessos}")
    print("\n=== PIPELINE DO NJUD CONCLUÍDO ===")

if __name__ == "__main__":
    asyncio.run(main())
