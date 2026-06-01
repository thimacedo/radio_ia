import os
import re
import sys
import io
import asyncio
import edge_tts
from pydub import AudioSegment

# Configurar caminhos
workspace_dir = r"e:\NJUD"
src_base_dir = os.path.join(workspace_dir, "roteiros_processados")
dest_base_dir = os.path.join(workspace_dir, "locucoes_geradas_tts")

# Configurar vozes neurais gratuitas (Padrão Microsoft Azure)
VOZ_SPEAKER_1 = "pt-BR-FranciscaNeural"  # Voz feminina jornalística
VOZ_SPEAKER_2 = "pt-BR-AntonioNeural"    # Voz masculina jornalística

def extrair_linhas_fala(caminho_txt):
    """
    Lê o roteiro tratado e extrai as falas separadas por locutor.
    Remove tags de expressão como [authoritative], [clear] para envio correto à API.
    """
    falas = []
    with open(caminho_txt, "r", encoding="utf-8") as f:
        linhas = f.readlines()
        
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
            
        # Captura "Speaker 1:" ou "Speaker 2:" e remove colchetes de tags de expressão
        match = re.match(r'^(Speaker\s*[12]):\s*(?:\[.*?\])?\s*(.*)$', linha, re.IGNORECASE)
        if match:
            speaker = match.group(1).lower().replace(" ", "")
            texto = match.group(2).strip()
            
            if texto:
                falas.append((speaker, texto))
                
    return falas

async def gerar_segmento_audio(texto, voz):
    """Gera os bytes de áudio para uma fala usando edge-tts em memória."""
    communicate = edge_tts.Communicate(texto, voz)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

async def processar_roteiro_completo(caminho_txt, caminho_saida):
    falas = extrair_linhas_fala(caminho_txt)
    
    if not falas:
        print("    [AVISO] Nenhuma fala com a tag 'Speaker 1:' ou 'Speaker 2:' encontrada no arquivo.")
        return False
        
    print(f"    -> Detectadas {len(falas)} falas alternadas. Gerando segmentos de áudio...")
    
    audio_segmentos = []
    
    for idx, (speaker, texto) in enumerate(falas):
        voz = VOZ_SPEAKER_1 if speaker == "speaker1" else VOZ_SPEAKER_2
        print(f"       [{idx+1}/{len(falas)}] Gravando {speaker} com voz '{voz}' ({len(texto)} caracteres)...")
        
        try:
            # Gerar o áudio para esta fala em memória
            segmento_bytes = await gerar_segmento_audio(texto, voz)
            audio_segmentos.append(segmento_bytes)
        except Exception as e:
            print(f"       [ERRO] Falha ao gerar segmento {idx+1}: {e}")
            return False
            
    # Concatenar todos os segmentos em um único arquivo de áudio usando pydub
    print("    -> Concatenando vinhetas e falas com pydub...")
    try:
        # Carregar vinheta de abertura
        vignette_start = None
        vinheta_start_path = r"e:\NJUD\VH AB - NOTICIAS DA HORA.mp3"
        if os.path.exists(vinheta_start_path):
            try:
                vignette_start = AudioSegment.from_mp3(vinheta_start_path)
                print("       [INFO] Vinheta de abertura carregada com sucesso.")
            except Exception as e:
                print(f"       [AVISO] Falha ao carregar vinheta de abertura: {e}")

        # Carregar vinheta de encerramento
        vignette_end = None
        vinheta_end_path = r"e:\NJUD\VH ENC - NOTICIAS DA HORA.mp3"
        if os.path.exists(vinheta_end_path):
            try:
                vignette_end = AudioSegment.from_mp3(vinheta_end_path)
                print("       [INFO] Vinheta de encerramento carregada com sucesso.")
            except Exception as e:
                print(f"       [AVISO] Falha ao carregar vinheta de encerramento: {e}")

        # Converter segmentos de bytes para AudioSegment
        segments_audio = []
        for idx, seg_bytes in enumerate(audio_segmentos):
            seg_io = io.BytesIO(seg_bytes)
            segments_audio.append(AudioSegment.from_mp3(seg_io))
            
        # Combinar tudo sequencialmente
        combined = vignette_start if vignette_start else AudioSegment.empty()
        for seg_aud in segments_audio:
            combined += seg_aud
            
        # Adicionar vinheta de encerramento no final
        if vignette_end:
            combined += vignette_end
            
        # Exportar arquivo final de áudio com bitrate de 192kbps
        combined.export(caminho_saida, format="mp3", bitrate="192k")
        return True
    except Exception as e:
        print(f"    [ERRO] Falha ao salvar arquivo final com pydub: {e}")
        return False

def extrair_numero_episodio(nome_arquivo):
    match = re.search(r'(?:NJUD|MJUD|\b)[\s_]*(\d{4})\b', nome_arquivo, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

def extrair_data_roteiro(caminho_txt, ep):
    """Extrai e normaliza a data (DD-MM) do roteiro tratado."""
    try:
        with open(caminho_txt, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Procurar padrão como: NJUD 1826 02-03
        match = re.search(r'NJUD\s*' + str(ep) + r'\s+([\d]{2}[-/][\d]{2}|[\d]{2}[-/][a-zA-Z]+)', content, re.IGNORECASE)
        date_str = None
        if match:
            date_str = match.group(1)
        else:
            # Fallback
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            for line in lines:
                if str(ep) in line and re.search(r'(\d{2}[-/]\d{2})', line):
                    date_str = re.search(r'(\d{2}[-/]\d{2})', line).group(1)
                    break
                    
        if date_str:
            date_str = date_str.replace('/', '-')
            parts = date_str.split('-')
            if len(parts) == 2:
                day, month = parts[0], parts[1].lower()
                month_map = {
                    'março': '03', 'marco': '03', 'mar': '03',
                    'abril': '04', 'abr': '04',
                    'maio': '05', 'mai': '05',
                    'junho': '06', 'jun': '06'
                }
                if month in month_map:
                    month = month_map[month]
                return f"{day}-{month}-2026"
    except Exception as e:
        print(f"    [AVISO] Erro ao extrair data do roteiro {ep}: {e}")
    return None

async def main():
    print("=== Edge TTS Multi-speaker — Locução Automática Gratuita em Lote ===")
    
    # 1. Listar arquivos tratados nas pastas (dinamicamente por subpastas)
    if os.path.exists(src_base_dir):
        target_months = sorted([
            d for d in os.listdir(src_base_dir)
            if os.path.isdir(os.path.join(src_base_dir, d)) and not d.startswith('.')
        ])
    else:
        target_months = []
        
    arquivos_processados = []
    
    for m in target_months:
        month_dir = os.path.join(src_base_dir, m)
        arquivos = [os.path.join(month_dir, f) for f in os.listdir(month_dir) if f.endswith(".txt")]
        arquivos_processados.extend(arquivos)
            
    if not arquivos_processados:
        print(f"\n[AVISO] Nenhum arquivo .txt encontrado em '{src_base_dir}'.")
        print("Certifique-se de que os roteiros foram processados e salvos localmente primeiro.")
        return
        
    print(f"\nEncontrados {len(arquivos_processados)} roteiro(s) tratados para geração de locução.")
    
    sucessos = 0
    for file_path in sorted(arquivos_processados):
        nome_arquivo = os.path.basename(file_path)
        ep = extrair_numero_episodio(nome_arquivo)
        ep_label = f"NJUD {ep}" if ep else nome_arquivo
        
        # Extrair a data do roteiro
        date_str = extrair_data_roteiro(file_path, ep) if ep else None
        
        # Determinar caminho de destino
        parent_month = os.path.basename(os.path.dirname(file_path))
        dest_month_dir = os.path.join(dest_base_dir, parent_month)
        os.makedirs(dest_month_dir, exist_ok=True)
        
        if ep:
            if date_str:
                caminho_saida_audio = os.path.join(dest_month_dir, f"NJUD_{ep}_{date_str}.mp3")
            else:
                caminho_saida_audio = os.path.join(dest_month_dir, f"NJUD_{ep}.mp3")
        else:
            caminho_saida_audio = os.path.join(dest_month_dir, f"{os.path.splitext(nome_arquivo)[0]}.mp3")
        
        # Pular se já existir para poupar tempo/requisições
        if os.path.exists(caminho_saida_audio):
            # Log discreto para arquivos já existentes
            print(f"  - {ep_label} (Ignorado, áudio final já existe)")
            continue
            
        print(f"\n* Iniciando locução para {ep_label} ({parent_month})...")
        
        sucesso = await processar_roteiro_completo(file_path, caminho_saida_audio)
        if sucesso:
            print(f"  [SUCESSO] Áudio final gerado em: {caminho_saida_audio}")
            sucessos += 1
            
    print(f"\n=== GERAÇÃO CONCLUÍDA ===")
    print(f"Total de novas locuções criadas: {sucessos}")
    print(f"Áudios salvos na pasta: {dest_base_dir}")

if __name__ == "__main__":
    asyncio.run(main())
