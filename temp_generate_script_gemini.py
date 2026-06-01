import json, pathlib, urllib.request, urllib.error, re

# Config
gemini_api_key = "AIzaSyBuTPqckeuTLsbxQywcS9SxzYTzyUN1naM"
pauta_path = pathlib.Path(r'E:\NJUD\PROGRAMA GIRO NAS COMARCAS\tts_txt\GNC-11-2025.txt')

# Se o backup não existe, faz agora
bak_path = pauta_path.with_suffix('.txt.bak')
if not bak_path.exists() and pauta_path.exists():
    pauta_content = pauta_path.read_text(encoding='utf-8')
    pauta_path.rename(bak_path)
else:
    pauta_content = bak_path.read_text(encoding='utf-8')

PROMPT = f"""Transforme a PAUTA abaixo em um ROTEIRO DE RADIOJORNALISMO completo para o programa 'Giro nas Comarcas'.

ESTRUTURA OBRIGATÓRIA:
ROTEIRO GIRO NAS COMARCAS //não entra na locução
PROGRAMA 11|  EXIBIÇÃO: 26/09/2025 //não entra na locução

[Vh abertura GIRO]

[LOC:] 
LOCUTOR 1: Olá! Hoje é sexta-feira, vinte e seis de setembro de dois mil e vinte e cinco, e esse é o Giro pelas Comarcas do Rio Grande do Norte.

[Vh passagem]

[LOC:]
(Desenvolva as notícias da pauta aqui, alternando entre LOCUTOR 1 e LOCUTOR 2. 
Cada notícia deve começar com um [Vh passagem] e um novo bloco [LOC:].
Use o padrão 'LOCUTOR X (CABEÇA):' para o título da nota e 'LOCUTOR Y:' para o corpo.
Mantenha as tags [Vh passagem] e [LOC:] entre cada matéria separadamente.)

[vht encerramento]

REGRAS DE CONTEÚDO:
1. Linguagem simples e direta.
2. Números, valores e datas por extenso.
3. Siglas soletradas (T J R N).
4. Sem jargão jurídico.
5. Mantenha os fatos da pauta.

PAUTA:
{pauta_content}
"""

url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash-lite:generateContent?key={gemini_api_key}"

payload = {
    "contents": [
        {
            "parts": [{"text": PROMPT}]
        }
    ],
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

try:
    with urllib.request.urlopen(req) as response:
        res_data = json.loads(response.read().decode('utf-8'))
        script = res_data['candidates'][0]['content']['parts'][0]['text'].strip()
        # Remove markdown code blocks if present
        script = re.sub(r'^```[a-z]*\n', '', script, flags=re.MULTILINE)
        script = re.sub(r'\n```$', '', script, flags=re.MULTILINE)
        
        pauta_path.write_text(script, encoding='utf-8')
        print(f"Script gerado via Gemini e salvo em: {pauta_path}")
except Exception as e:
    print(f"Erro ao chamar Gemini: {e}")
