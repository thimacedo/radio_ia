import os
import re
import asyncio
import pathlib
from llm_factory import LLMFactory
from gerar_locucao_giro_premium import process_file as generate_audio

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
TTS_DIR    = pathlib.Path(r"E:\NJUD\PROGRAMA GIRO NAS COMARCAS\tts_txt")
REVISADO_DIR = TTS_DIR.parent / "tts_txt_revisado"
REVISADO_DIR.mkdir(exist_ok=True)

llm = LLMFactory()

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
PAUTA_TO_SCRIPT_PROMPT = """\
Transforme a PAUTA abaixo em um ROTEIRO DE RADIOJORNALISMO completo para o programa 'Giro nas Comarcas'.

ESTRUTURA OBRIGATÓRIA (RESPEITE EXATAMENTE):
ROTEIRO GIRO NAS COMARCAS //não entra na locução
PROGRAMA [NUMERO]|  EXIBIÇÃO: [DATA] //não entra na locução

[Vh abertura GIRO]

[LOC:] 
LOCUTOR 1: Olá! Hoje é [DIA-DA-SEMANA], [DATA-EXTENSO], e esse é o Giro pelas Comarcas do Rio Grande do Norte.

[Vh passagem]

[LOC:]
(Desenvolva as notícias da pauta aqui, alternando entre LOCUTOR 1 e LOCUTOR 2. 
Cada notícia deve começar com um [Vh passagem] e um novo bloco [LOC:].
Use o padrão 'LOCUTOR X (CABEÇA):' para o título da nota e 'LOCUTOR Y:' para o corpo.
Mantenha as tags [Vh passagem] e [LOC:] entre cada matéria separadamente.)

[vht encerramento]
"""

REWRITE_PROMPT = """\
Você é um editor especializado em radiojornalismo para o TJRN.
Sua tarefa é reescrever o texto de locução recebido aplicando EXATAMENTE as regras abaixo.
Você DEVE PRESERVAR as tags de locutor (ex: LOCUTOR 1:, LOCUTOR 2:, LOCUTOR 1 (CABEÇA):) e tags técnicas ([LOC:], [Vh ...]).

REGRAS OBRIGATÓRIAS:
1. Preserve as tags técnicas e de locutor.
2. Números, valores financeiros, porcentagens, datas e horas: escrever por extenso.
3. Siglas: soletrar letra a letra separadas por espaço na PRIMEIRA menção.
4. Linguagem simples: eliminar jargões jurídicos desnecessários.
5. Nunca começar a nota pelo verbo.
6. Nenhum markdown.
Devolva o roteiro completo mantendo a estrutura.
"""

# ---------------------------------------------------------------------------
# Lógica Principal
# ---------------------------------------------------------------------------

def is_raw_pauta(content: str) -> bool:
    """Detecta se o conteúdo é uma pauta bruta ou já é um roteiro."""
    return "[LOC:]" not in content and "PAUTA" in content.upper()

async def pipeline(file_path: pathlib.Path):
    print(f"\n--- Iniciando Pipeline para: {file_path.name} ---")
    content = file_path.read_text(encoding="utf-8", errors="replace")
    
    # 1. Transformar Pauta em Roteiro (se necessário)
    if is_raw_pauta(content):
        print(f"  [ETAPA 1] Transformando pauta bruta em roteiro...")
        content = llm.ask(PAUTA_TO_SCRIPT_PROMPT, content)
        print(f"    -> Roteiro estruturado gerado.")
    else:
        print(f"  [ETAPA 1] Arquivo já identificado como roteiro.")

    # 2. Reescrita Jornalística
    print(f"  [ETAPA 2] Aplicando diretrizes de radiojornalismo (Reescrita)...")
    content_revisado = llm.ask(REWRITE_PROMPT, content)
    
    # Salvar roteiro revisado
    revisado_path = REVISADO_DIR / file_path.name
    revisado_path.write_text(content_revisado, encoding="utf-8")
    print(f"    -> Roteiro revisado salvo em: {revisado_path.name}")

    # 3. Geração de Áudio Premium
    print(f"  [ETAPA 3] Gerando áudio premium e mixando vinhetas...")
    try:
        await generate_audio(revisado_path)
    except Exception as e:
        print(f"    [ERRO] Falha na geração de áudio: {e}")

async def main():
    files = sorted(list(TTS_DIR.glob("*.txt")))
    print(f"=== Giro nas Comarcas: Pipeline Integrado (LLM Fallback) ===")
    print(f"Arquivos encontrados: {len(files)}\n")

    for f in files:
        # Pular backups
        if f.suffix == ".bak": continue
        
        await pipeline(f)

if __name__ == "__main__":
    asyncio.run(main())
