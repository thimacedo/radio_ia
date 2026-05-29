import os
import re
import json
import time
import urllib.request
import urllib.error

# Configurar chaves e caminhos
gemini_api_key = "AIzaSyBuTPqckeuTLsbxQywcS9SxzYTzyUN1naM"
src_base_dir = r"H:\Meu Drive\RADIO TJRN CONTEÚDO\NOT JUDICIARIO (5 MIN)\NJUD 2026\Roteiros TXT Original"
dest_base_dir = r"e:\NJUD\roteiros_processados"

# Lista de modelos válidos e suportados em 2026 para contornar limites diários individuais
MODEL_LIST = [
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash-lite-preview",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3-flash-preview",
    "gemini-pro-latest",
    "gemini-2.5-pro"
]

current_model_idx = 0

SYSTEM_PROMPT = """Atuar como especialista em edição de roteiros de radiojornalismo para o Google AI Studio (modo Multi-speaker audio). O objetivo é processar boletins informativos e entregá-los formatados para síntese de voz em formato de texto bruto ("Raw structure"), aplicando as diretrizes de redação para locução, linguagem simples e tags de expressão.

REGRAS DE ESTRUTURA E FORMATAÇÃO (RAW TEXT):
1. O texto final não deve conter nenhuma formatação Markdown (sem asteriscos para negrito, sem itálico, sem blockquotes).
2. Inserir no topo da resposta, apenas uma vez antes do primeiro roteiro, a instrução de estilo global:
Read in a professional news anchor style suitable for Brazilian radio. The tone should be authoritative, clear, and dynamic.
3. Pular uma linha após a instrução global.
4. Identificar o cabeçalho no padrão: NJUD [NÚMERO] [DIA-MÊS].
5. Reter exclusivamente os blocos: Cabeça (Abertura), Escalada (Destaques) e Encerramento. Ignorar os textos integrais das reportagens (indicados como OFF ou NOTA).
6. Substituir as marcações originais de locutores pelo texto exato abaixo, seguido obrigatoriamente por uma tag de expressão entre colchetes (ex: [authoritative], [clear], [dynamic], [professional]):
Speaker 1: [tag] [texto da fala]
Speaker 2: [tag] [texto da fala]
7. Na Escalada (leitura dos destaques), alternar as vozes sucessivamente, iniciando obrigatoriamente com o Speaker 1.
8. Remover completamente nomes próprios de apresentadores, repórteres e locutores do texto que será falado.

REGRAS DE REDAÇÃO E LOCUÇÃO (Baseadas no Manual de Boletins e Linguagem Simples):
1. Escrever números, valores financeiros, porcentagens, datas e horas por extenso (ex: "sete mil reais", "quinze dias", "dezesseis de abril de dois mil e vinte e seis").
2. Escrever siglas letra por letra separadas por espaço (ex: t j r n, I P V A) ou o nome por extenso na primeira menção.
3. Escrever sites e redes sociais de forma literal para a leitura da IA (ex: "t j r n ponto jus ponto b r", "Xis").
4. Eliminar termos formalistas, jargões jurídicos desnecessários e adotar linguagem direta e concisa.
5. Evitar começar frases pelo verbo (ação) na cabeça das notas.
6. Manter a essência da notícia inalterada; as modificações devem se restringir aos ajustes técnicos de locução e simplificação gramatical.

COMPORTAMENTO:
Ao receber um ou mais roteiros brutos, processar as informações e devolver o texto final formatado na íntegra, estritamente em texto puro. Fornecer unicamente o script pronto para cópia e inserção no AI Studio. Não incluir explicações extras, saudações, despedidas ou comentários sobre as edições realizadas.
"""

def chamar_gemini_api_multi(texto_roteiro):
    global current_model_idx
    
    while current_model_idx < len(MODEL_LIST):
        model_name = MODEL_LIST[current_model_idx]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_api_key}"
        
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"Aqui está o roteiro bruto para tratamento:\n\n{texto_roteiro}"}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "generationConfig": {
                "temperature": 0.2
            }
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={'Content-Type': 'application/json'}
        )
        
        max_tentativas = 2
        for tentativa in range(max_tentativas):
            try:
                with urllib.request.urlopen(req) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    if 'candidates' in res_data and res_data['candidates']:
                        return res_data['candidates'][0]['content']['parts'][0]['text']
                    else:
                        raise ValueError(f"Resposta inválida da API: {res_data}")
            except urllib.error.HTTPError as e:
                err_code = e.code
                err_msg = e.read().decode('utf-8')
                
                # Se for quota excedida (limite de 20 requisições diárias no free tier)
                if err_code == 429 and ("quota" in err_msg.lower() or "limit" in err_msg.lower()):
                    print(f"  [COTA ESGOTADA] Modelo '{model_name}' excedeu o limite diário.")
                    current_model_idx += 1
                    print(f"  -> Trocando para o próximo modelo da lista: '{MODEL_LIST[current_model_idx]}'...")
                    break # Quebra o loop de tentativas deste modelo para ir ao próximo
                    
                # Se for instabilidade temporária (503 ou outro 429 de pico)
                elif err_code in [503, 429] and tentativa < max_tentativas - 1:
                    wait_time = 4
                    print(f"  [Servidor Ocupado] Modelo '{model_name}' instável. Aguardando {wait_time}s antes de tentar novamente...")
                    time.sleep(wait_time)
                else:
                    print(f"  [ERRO NO MODELO '{model_name}'] HTTP {err_code}: {err_msg}")
                    # Pula para o próximo modelo se der erro persistente
                    current_model_idx += 1
                    break
            except Exception as e:
                if tentativa < max_tentativas - 1:
                    time.sleep(3)
                else:
                    print(f"  [ERRO CONEXÃO '{model_name}'] {e}")
                    current_model_idx += 1
                    break
                    
    raise Exception("Todos os modelos disponíveis no Google AI Studio foram esgotados ou estão inacessíveis.")

def extrair_numero_episodio(nome_arquivo):
    match = re.search(r'(?:NJUD|MJUD|\b)\s*(\d{4})\b', nome_arquivo, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

def main():
    print("=== Processador Central de Roteiros — Gemini Multi-Model Fallback ===")
    
    if not os.path.exists(src_base_dir):
        print(f"[ERRO] Pasta do Drive não encontrada: {src_base_dir}")
        return
        
    target_months = ["3 - MARÇO", "4 - ABRIL", "5 - MAIO"]
    total_sucessos = 0
    
    for m in target_months:
        src_month_dir = os.path.join(src_base_dir, m)
        dest_month_dir = os.path.join(dest_base_dir, m)
        
        if not os.path.exists(src_month_dir):
            continue
            
        os.makedirs(dest_month_dir, exist_ok=True)
        
        arquivos = [f for f in os.listdir(src_month_dir) if f.endswith(".txt")]
        if not arquivos:
            continue
            
        print(f"\n--- Processando mês: {m} ({len(arquivos)} arquivos encontrados) ---")
        
        for f in sorted(arquivos):
            ep = extrair_numero_episodio(f)
            ep_label = f"NJUD {ep}" if ep else f
            
            caminho_src = os.path.join(src_month_dir, f)
            caminho_dest = os.path.join(dest_month_dir, f"NJUD_{ep}.txt" if ep else f)
            
            # Verificar se já processamos
            if os.path.exists(caminho_dest):
                # Ignorar logs de arquivos já finalizados para manter o console limpo
                continue
                
            print(f"  - Processando {ep_label}...")
            try:
                with open(caminho_src, "r", encoding="utf-8") as file:
                    conteudo = file.read()
                    
                # Processar texto com fallback automático de modelos
                texto_tratado = chamar_gemini_api_multi(conteudo)
                
                # Salvar saída
                with open(caminho_dest, "w", encoding="utf-8") as out:
                    out.write(texto_tratado)
                    
                print(f"    [SUCESSO] Salvo em: {caminho_dest}")
                total_sucessos += 1
                
                # Intervalo pequeno para respeitar os limites de requisições por minuto (RPM)
                time.sleep(4.2)
                
            except Exception as e:
                print(f"    [FALHA CRÍTICA] Não foi possível processar {ep_label}: {e}")
                sys.exit(1)
                
    print(f"\n=== PROCESSAMENTO CONCLUÍDO ===")
    print(f"Novos arquivos tratados com sucesso: {total_sucessos}")
    print(f"Pasta de destino: {dest_base_dir}")

if __name__ == "__main__":
    main()
