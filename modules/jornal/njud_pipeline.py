import os
import sys
import re
import asyncio
import pathlib

# Ajuste de path para importar do core
current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.append(str(project_root))

from core.models import ProgramRecipe, VoiceStrategy, AssemblyRecipe
from core.engine import PipelineEngine
from core.best_practices import carregar_env_var

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
NJUD_INPUT_DIR = pathlib.Path(carregar_env_var("DRIVE_NJUD_INPUT_DIR", r"H:\Meu Drive\RADIO TJRN CONTEÚDO\NOT JUDICIARIO (5 MIN)\NJUD 2026\Roteiros TXT Original"))
NJUD_OUTPUT_DIR = pathlib.Path(carregar_env_var("DRIVE_NJUD_OUTPUT_DIR", r"H:\Meu Drive\RADIO TJRN CONTEÚDO\NOT JUDICIARIO (5 MIN)\NJUD 2026"))
LOCAL_WORK_DIR = project_root / "modules" / "jornal" / "workspace"

VHT_DIR = project_root / "assets" / "vht" # Vinhetas do NJUD estão com as do boletim
# Assumindo que NJUD 1806 28-01.mp3 é um exemplo ou BG. 
# Para manter genérico, vamos mapear o BG do boletim ou deixar None e editar depois se necessário.

SYSTEM_PROMPT = """Você é um especialista em edição de roteiros de radiojornalismo. O objetivo é processar boletins informativos e entregá-los formatados para síntese de voz e edição automática.

REGRAS:
1. Sem formatação Markdown.
2. Identificar o cabeçalho no padrão: NJUD [NÚMERO] [DIA-MÊS].
3. O roteiro é dividido em 3 partes: ESCALADA (manchetes lidas de forma alternada), NOTAS (desenvolvimento das matérias) e ENCERRAMENTO.
4. O formato de edição de áudio segue o padrão 'Audio-as-Text'. Insira OBRIGATORIAMENTE as tags de controle em letras maiúsculas:
   - ANTES DA ESCALADA (início do programa): [ASSET: ABERTURA] e na linha abaixo [TRILHA: LIGAR]
   - DEPOIS de todas as manchetes da escalada (antes de começar a ler o texto da primeira nota): [TRILHA: DESLIGAR] e na linha abaixo [ASSET: PASSAGEM]
   - ENTRE AS NOTAS (quando terminar uma matéria e começar outra): [ASSET: PASSAGEM] (não ligue a trilha nas notas)
   - ANTES DO ENCERRAMENTO (início da despedida): [ASSET: PASSAGEM] e na linha abaixo [TRILHA: LIGAR]
   - FIM DO PROGRAMA (após a última fala de tchau): [TRILHA: DESLIGAR] e na linha abaixo [ASSET: ENCERRAMENTO]
5. Reter exclusivamente as falas: Cabeça (Abertura), Escalada (Manchetes), Notas e Encerramento. Ignorar marcações como OFF ou NOTA do texto original.
6. Substituir as marcações originais de locutores por:
Speaker 1: [texto da fala]
Speaker 2: [texto da fala]
7. Na Escalada (leitura dos destaques) e nas Notas, alterne as vozes, iniciando sempre com o Speaker 1.
8. REMOVA TOTALMENTE nomes próprios de apresentadores, repórteres e locutores. JAMAIS utilize substitutos bizarros como "eu sou a equipe" ou "eu sou o apresentador". Se a frase original for "Olá, eu sou João, confira os destaques", transforme apenas em "Olá, confira os destaques". Vá direto ao assunto.
9. Escrever números, valores, porcentagens, datas e horas por extenso. Siglas letra por letra (ex: t j r n). Sites de forma literal.
"""

def njud_parse_hook(content: str) -> list:
    """Extrai comandos de ASSET, TRILHA e as falas separadas por locutor."""
    blocks = []
    
    for linha in content.splitlines():
        linha = linha.strip()
        if not linha:
            continue
            
        # 1. Checar por Assets
        match_asset = re.match(r'^\[ASSET:\s*(.*?)\]$', linha, re.IGNORECASE)
        if match_asset:
            blocks.append(("ASSET", match_asset.group(1).strip().upper()))
            continue
            
        # 2. Checar por Trilha
        match_trilha = re.match(r'^\[TRILHA:\s*(LIGAR|DESLIGAR)\]$', linha, re.IGNORECASE)
        if match_trilha:
            blocks.append(("TRILHA", match_trilha.group(1).strip().upper()))
            continue

        # 3. Capturar falas (Speaker 1 ou 2)
        match_loc = re.match(r'^(Speaker\s*[12]):\s*((?:\[.*?\])?\s*.*)$', linha, re.IGNORECASE)
        if match_loc:
            speaker = match_loc.group(1).lower().replace(" ", "")
            texto = match_loc.group(2).strip()
            
            # Limpar chaves sobressalentes como [EFEITO ...] se o LLM alucinar
            texto = re.sub(r'\[.*?\]', '', texto).strip()
            
            if texto:
                blocks.append(("LOC", (speaker, texto)))
                
    return blocks

# ---------------------------------------------------------------------------
# Receita do Programa
# ---------------------------------------------------------------------------
receita_njud = ProgramRecipe(
    name="Notícias do Judiciário (NJUD)",
    drive_input_dir=NJUD_INPUT_DIR,
    drive_output_dir=NJUD_OUTPUT_DIR,
    local_work_dir=LOCAL_WORK_DIR,
    system_prompt=SYSTEM_PROMPT,
    voice_strategy=VoiceStrategy(
        type='intra_file',
        voices=["pt-BR-FranciscaNeural", "pt-BR-AntonioNeural", "pt-BR-ElzaNeural", "pt-BR-ThalitaNeural"]
    ),
    assembly=AssemblyRecipe(
        profile_path=project_root / "assets" / "profiles" / "njud_profile.json"
    ),
    parse_hook=njud_parse_hook
)

if __name__ == "__main__":
    motor = PipelineEngine(receita_njud)
    
    async def run_njud():
        print("Iniciando o processamento dos roteiros na pasta local 1_txt_bruto...")
        files = sorted([f for f in motor.txt_dir.glob("*.txt") if not f.name.endswith(".bak")])
        
        month_map_njud = {
            "01": "1 - JANEIRO", "02": "2 - FEVEREIRO", "03": "3 - MARÇO", "04": "4 - ABRIL",
            "05": "5 - MAIO", "06": "6 - JUNHO", "07": "7 - JULHO", "08": "8 - AGOSTO",
            "09": "9 - SETEMBRO", "10": "10 - OUTUBRO", "11": "11 - NOVEMBRO", "12": "12 - DEZEMBRO"
        }
        
        for idx, f in enumerate(files):
            subfolder = ""
            # Procura por padrão de data DD-MM no nome do arquivo (ex: 02-06)
            month_match = re.search(r"-(\d{2})", f.name) 
            if month_match:
                mes_num = month_match.group(1)
                mes_pasta = month_map_njud.get(mes_num, "")
                if mes_pasta:
                    subfolder = f"{mes_pasta}/EDITADOS"
            
            await motor.run_file(f, file_idx=idx, subfolder=subfolder)
                
    asyncio.run(run_njud())
