import os
import sys
import re
import io
import asyncio
import urllib.request
import openpyxl
import shutil
from pydub import AudioSegment

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
        falas = extrair_linhas_fala(roteiro_revisado)
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
    
    URL_SPREADSHEET = "https://docs.google.com/spreadsheets/d/1HegL-SudxPLI4Y6wsj1nnJocXHOvi-6inGqQld1lYec/export?format=xlsx"
    temp_file = os.path.join(LOCAL_WORKSPACE, "njud_temp_downloaded.xlsx").replace("\\", "/")
    os.makedirs(LOCAL_WORKSPACE, exist_ok=True)
    
    # 1. Carregar a planilha controle (Tentar online primeiro, senão local)
    wb = None
    loaded_source = None
    
    print("Tentando baixar planilha online do Google Sheets...")
    try:
        req = urllib.request.Request(URL_SPREADSHEET, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            content = response.read()
        with open(temp_file, "wb") as f:
            f.write(content)
        wb = openpyxl.load_workbook(temp_file, data_only=True)
        loaded_source = "online_google_sheet"
        print("Planilha carregada com sucesso diretamente do Google Sheets (online).")
        try:
            os.remove(temp_file)
        except Exception:
            pass
    except Exception as e:
        print(f"Não foi possível carregar do Google Sheets online ({e}). Usando arquivo local...")
        if os.path.exists(PATH_PLANILHA):
            wb = openpyxl.load_workbook(PATH_PLANILHA, data_only=True)
            loaded_source = "local_excel"
            print(f"Planilha local carregada: {PATH_PLANILHA}")
        else:
            print(f"[ERRO CRÍTICO] Planilha local do NJUD não encontrada: {PATH_PLANILHA}")
            sys.exit(1)
            
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
        m2 = re.search(r'(\d{2})[-/](\d{2})[-/](\d{4})', refer_str)
        if m2:
            return f"{m2.group(1)}-{m2.group(2)}"
        return ""

    # 4. Localizar pendências baseando-se na ausência de arquivo final no Drive
    sheets_to_process = [name for name in wb.sheetnames if name != 'DASHBOARD GERAL']
    pendencias = [] # Tuplas: (sheet_name, row_idx, normalized_row)
    sheet_njud_names = set()
    
    for s_name in sheets_to_process:
        ws = wb[s_name]
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) <= 1:
            continue
            
        # Mapeamento dinâmico de colunas baseando-se nos cabeçalhos
        header_row = [str(h).upper().strip() if h is not None else "" for h in rows[0]]
        idx_refer = -1
        idx_njud = -1
        idx_url = -1
        idx_audio = -1
        
        for idx, h in enumerate(header_row):
            if "REFER" in h or "CAMINHO" in h:
                idx_refer = idx
            elif "NJUD" in h or "NOME DO ARQUIVO" in h:
                idx_njud = idx
            elif "URL" in h:
                idx_url = idx
            elif "AUDIO" in h or "ÁUDIO" in h:
                idx_audio = idx
                
        if idx_njud == -1 or idx_url == -1:
            print(f"  [Aviso] Não foi possível mapear colunas necessárias na aba {s_name}. Ignorando aba.")
            continue
            
        for idx, r in enumerate(rows[1:], start=1):
            nome_raw = r[idx_njud]
            if not nome_raw:
                continue
            nome_arquivo = str(nome_raw).strip()
            
            # Garantir que é um arquivo NJUD
            if "NJUD" not in nome_arquivo.upper():
                continue
                
            sheet_njud_names.add(nome_arquivo)
            
            # Verificar se a coluna de status de áudio indica que já está OK
            if idx_audio != -1 and idx_audio < len(r):
                audio_status = r[idx_audio]
                if audio_status and any(ok in str(audio_status).upper() for ok in ["OK", "SIM", "✔", "PRONTO", "CONCLUÍDO", "CONCLUIDO"]):
                    continue
                
            url = r[idx_url] if idx_url < len(r) else None
            if not url or 'document/d/' not in str(url):
                continue
                
            refer_val = r[idx_refer] if (idx_refer != -1 and idx_refer < len(r)) else None
            caminho_col = obter_caminho_mes(refer_val)
            sufixo_data = obter_sufixo_data(refer_val)
            
            # Padrão final de nomenclatura: NJUD + Número + Data de Veiculação
            nome_final = f"{nome_arquivo} {sufixo_data}" if sufixo_data else nome_arquivo
            
            # Extrair mes_num para estruturação 5S
            mes_num = 6
            m_mes = re.search(r'(\d+)', caminho_col)
            if m_mes:
                mes_num = int(m_mes.group(1))
            short_name = MONTH_MAP_SHORT.get(mes_num, "JUN")
            folder_name = f"{mes_num:02d} - {short_name} - {ANO_SHORT}"
            
            # 1. Verificar na estrutura 5S (Mailing e Rádio)
            drive_5s_base = os.path.join(DRIVE_ROOT, "00_PRODUCAO_2026", "02_JORNAIS_NJUD").replace("\\", "/")
            drive_audio_path_5s_mailing = os.path.join(drive_5s_base, "02_AUDIOS_MAILING", folder_name, f"{nome_final}.mp3").replace("\\", "/")
            drive_audio_path_5s_radio = os.path.join(drive_5s_base, "03_AUDIOS_RADIO", folder_name, f"{nome_final}.mp3").replace("\\", "/")
            
            # 2. Verificar na estrutura tradicional antiga (legada)
            drive_audio_path_trad = os.path.join(DRIVE_ROOT, "NOT JUDICIARIO (5 MIN)", "NJUD 2026", caminho_col, "EDITADOS", f"{nome_final}.mp3").replace("\\", "/")
            drive_audio_path_trad_old = os.path.join(DRIVE_ROOT, "NOT JUDICIARIO (5 MIN)", "NJUD 2026", caminho_col, f"{nome_arquivo} LOC.mp3").replace("\\", "/")
            
            if (os.path.exists(drive_audio_path_5s_mailing) or 
                os.path.exists(drive_audio_path_5s_radio) or 
                os.path.exists(drive_audio_path_trad) or 
                os.path.exists(drive_audio_path_trad_old)):
                # O áudio final já existe no Drive (em qualquer formato), ignora!
                print(f"  - {nome_final} (ignorado, áudio final já existe no Drive)")
                continue
                
            normalized_row = (caminho_col, nome_arquivo, url, sufixo_data)
            pendencias.append((s_name, idx + 1, normalized_row))

    # --- Detecção Dinâmica Complementar via Google Drive ---
    print("\n[INFO] Escaneando Google Drive para detectar roteiros extras (não listados na planilha)...")
    try:
        core_dir = os.path.join(project_root, "core").replace("\\", "/")
        if core_dir not in sys.path:
            sys.path.append(core_dir)
        from gdoc_exporter import CREDENTIALS_PATH, _build_drive_service
        service_drive = _build_drive_service(CREDENTIALS_PATH)
        
        # Listar subpastas de 01_ROTEIROS (ID: 1UHYp4SCterbUJF27MHj3bOh6ju1OBzIG)
        query_folders = "'1UHYp4SCterbUJF27MHj3bOh6ju1OBzIG' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        folders = service_drive.files().list(q=query_folders, fields="files(id, name)").execute().get('files', [])
        
        # MONTH_MAP já vem de core.constants (MONTH_MAP_FULL)
        
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
            
        for folder in folders:
            # Padrão: 06 - JUN - 26 ou similar
            m_caminho = re.search(r'(\d{2})\s*-\s*([A-Z]{3})', folder['name'].upper())
            if not m_caminho:
                continue
            mes_num = int(m_caminho.group(1))
            caminho_col = MONTH_MAP_FULL.get(mes_num, "6 - JUNHO")
            
            # Limitar apenas aos meses relevantes (atual, anterior e futuros de 2026) para evitar buscas excessivas
            current_month = datetime.datetime.now().month
            prev_month = current_month - 1 if current_month > 1 else 12
            active_months = [current_month, prev_month]
            for m in range(current_month + 1, 13):
                active_months.append(m)
                
            if mes_num not in active_months:
                continue
                
            query_docs = f"'{folder['id']}' in parents and mimeType = 'application/vnd.google-apps.document' and trashed = false"
            docs = service_drive.files().list(q=query_docs, fields="files(id, name)").execute().get('files', [])
            
            for doc in docs:
                nome_doc = doc['name'].strip()
                if "NJUD" not in nome_doc.upper():
                    continue
                # Se o nome já está na planilha ou nas pendências já adicionadas, ignorar
                if nome_doc in sheet_njud_names or any(p[2][1] == nome_doc for p in pendencias):
                    continue
                    
                print(f"  -> Roteiro extra detectado no Drive: {nome_doc} (ID: {doc['id']})")
                
                # Baixar texto para tentar inferir data de veiculação
                texto_roteiro = baixar_roteiro_via_api(doc['id'])
                sufixo_data = obter_sufixo_data_do_conteudo(texto_roteiro)
                
                # Se não conseguiu obter sufixo, usar padrão vazio
                nome_final = f"{nome_doc} {sufixo_data}" if sufixo_data else nome_doc
                
                # Verificar se o áudio já existe no Drive
                drive_editados_dir = os.path.join(DRIVE_BASE_DIR, caminho_col, "EDITADOS").replace("\\", "/")
                drive_audio_path_new = os.path.join(drive_editados_dir, f"{nome_final}.mp3").replace("\\", "/")
                
                drive_month_dir_old = os.path.join(DRIVE_BASE_DIR, caminho_col).replace("\\", "/")
                drive_audio_path_old = os.path.join(drive_month_dir_old, f"{nome_doc} LOC.mp3").replace("\\", "/")
                
                filename_base = f"{nome_doc} {sufixo_data}" if sufixo_data else f"{nome_doc} LOC"
                local_audio_path = os.path.join(LOCAL_WORKSPACE, "3_audio_final", f"{filename_base}.mp3").replace("\\", "/")
                
                if os.path.exists(drive_audio_path_new) or os.path.exists(drive_audio_path_old) or os.path.exists(local_audio_path):
                    print(f"  - {nome_final} (ignorado, áudio final já existe localmente ou no Drive)")
                    continue
                    
                url_doc = f"https://docs.google.com/document/d/{doc['id']}/edit"
                normalized_row = (caminho_col, nome_doc, url_doc, sufixo_data)
                
                pendencias.append((folder['name'], 999, normalized_row))
                print(f"  [PEND\u00caNCIA] Adicionado dinamicamente: {nome_doc} ({sufixo_data})")
                
    except Exception as e:
        print(f"  [AVISO] Erro ao buscar pend\u00eancias extras no Google Drive: {e}")
        
    if not pendencias:
        print("\n[INFO] Nenhuma pendência de gravação encontrada no Jornal NJUD! Todos os jornais da planilha/Drive já possuem áudio.")
        sys.exit(0)
        
    print(f"\nTotal de pendências detectadas no NJUD: {len(pendencias)}")
    
    if args.test:
        print("\n*** MODO DE TESTE ATIVO — Processando apenas 1 pendência ***")
        pendencias = pendencias[:1]
        
    sucessos = 0
    results = []
    
    # Processar jornais (limitar concorrência para 2 devido a chamadas de LLM e TTS)
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
            
            # --- Caminhos Estruturados 5S de 2026 ---
            try:
                # Extrair mes_num de caminho_col
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
                
                # Copiar roteiro
                if os.path.exists(local_txt_file):
                    shutil.copy2(local_txt_file, drive_5s_txt_path)
                    print(f"  [ROTEIRO 5S] Copiado para: {drive_5s_txt_path}")
                    total_sincronizados += 1
                    
                # Copiar áudio para mailing
                if os.path.exists(local_audio_file):
                    shutil.copy2(local_audio_file, drive_5s_audio_path_mailing)
                    print(f"  [ÁUDIO MAILING 5S] Copiado para: {drive_5s_audio_path_mailing}")
                    total_sincronizados += 1
                    
                # Copiar áudio para rádio
                if os.path.exists(local_audio_file):
                    shutil.copy2(local_audio_file, drive_5s_audio_path_radio)
                    print(f"  [ÁUDIO RÁDIO 5S] Copiado para: {drive_5s_audio_path_radio}")
                    total_sincronizados += 1
            except Exception as e_5s:
                print(f"  [ERRO] Falha ao sincronizar na nova estrutura 5S: {e_5s}")
                
        print(f"Sincronização com o Drive concluída! Total de arquivos copiados: {total_sincronizados}")
        
    print("\n=== PIPELINE DO NJUD CONCLUÍDO ===")

if __name__ == "__main__":
    asyncio.run(main())
