import os, pathlib, re
from openai import OpenAI

# Config
env_path = pathlib.Path(r'E:\NJUD\.env')
key = ''
if env_path.exists():
    content = env_path.read_text(encoding='utf-8')
    match = re.search(r'OPENAI_API_KEY\s*=\s*([^\s]+)', content)
    if match: key = match.group(1).strip()

client = OpenAI(api_key=key)

pauta_path = pathlib.Path(r'E:\NJUD\PROGRAMA GIRO NAS COMARCAS\tts_txt\GNC-11-2025.txt')
pauta_content = pauta_path.read_text(encoding='utf-8')

prompt = f"""Transforme a PAUTA abaixo em um ROTEIRO DE RADIOJORNALISMO completo para o programa 'Giro nas Comarcas'.

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

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.7
)

script = response.choices[0].message.content.strip()
output_path = pathlib.Path(r'E:\NJUD\PROGRAMA GIRO NAS COMARCAS\tts_txt\GNC-11-2025.txt')
# Faz backup do original
pauta_path.rename(pauta_path.with_suffix('.txt.bak'))
output_path.write_text(script, encoding='utf-8')
print(f'Script gerado e salvo em: {output_path}')
