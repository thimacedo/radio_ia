import os
import sys
import re
import asyncio
import pathlib
import openpyxl
import urllib.request

# Ajuste de path para importar do core
current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.append(str(project_root))

from core.models import ProgramRecipe, VoiceStrategy, AssemblyRecipe
from core.engine import PipelineEngine
from core.gdoc_exporter import export_gdoc_to_txt
from core.best_practices import carregar_env_var, MONTH_MAP_SHORT

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
SPREADSHEET_ID = "1Xbftz33ZEE4oc66ppgI5Sjy0T99WTUrN9gCJ85ZLDSo"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=xlsx"

GIRO_DRIVE_INPUT = current_dir # Excel baixado aqui
GIRO_DRIVE_OUTPUT = pathlib.Path(carregar_env_var("DRIVE_GIRO_OUTPUT_DIR", r"H:\Meu Drive\RADIO TJRN CONTEÚDO\PROGRAMAS\PROGRAMA GIRO NAS COMARCAS (10min)"))
LOCAL_WORK_DIR = project_root / "modules" / "giro" / "workspace"

def fetch_giro_from_sheet(txt_dir: pathlib.Path):
    """Baixa a planilha do Giro e faz o download dos textos do Google Docs pendentes."""
    print("Baixando planilha de controle do Giro...")
    txt_dir.mkdir(parents=True, exist_ok=True)
    local_xlsx = GIRO_DRIVE_INPUT / "GIRO_ATUAL.xlsx"
    try:
        urllib.request.urlretrieve(SHEET_URL, local_xlsx)
    except Exception as e:
        print(f"[ERRO] Falha ao baixar a planilha: {e}")
        return 0

    wb = openpyxl.load_workbook(local_xlsx, data_only=True)
    count = 0
    
    # Processa todas as abas
    for s_name in wb.sheetnames:
        ws = wb[s_name]
        
        # Pula cabeçalho, começa na linha 2
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row or not any(row): continue
            
            caminho = str(row[0]).strip() if row[0] else ""
            nome = str(row[1]).strip() if len(row) > 1 and row[1] else ""
            url = str(row[2]).strip() if len(row) > 2 and row[2] else ""
            status = str(row[3]).strip().lower() if len(row) > 3 and row[3] else ""
            
            if not nome or "docs.google.com" not in url:
                continue
                
            if "✔" not in status and "ok" not in status:
                print(f"  - Baixando pendência: {nome}...")
                try:
                    # Extrair o ID do doc da URL
                    match = re.search(r"[?&/](?:id=|d/)([a-zA-Z0-9_-]{25,})", url)
                    if match:
                        doc_id = match.group(1)
                        # Sanitizar nome do arquivo (remove barras e caracteres ilegais)
                        safe_name = re.sub(r'[\\/*?:"<>|]', "-", nome)
                        
                        # Salva temporariamente um .gdoc mockado para o exporter ler
                        temp_gdoc = txt_dir / f"{safe_name}.gdoc"
                        temp_gdoc.write_text(f'{{"doc_id": "{doc_id}"}}', encoding="utf-8")
                        
                        texto_extraido = export_gdoc_to_txt(temp_gdoc)
                        
                        # Salva o txt limpo
                        file_name = f"{safe_name}.txt"
                        (txt_dir / file_name).write_text(texto_extraido, encoding="utf-8")
                        temp_gdoc.unlink() # remove temp
                        count += 1
                        print(f"    [OK] {nome} extraído.")
                except Exception as e:
                    print(f"    [ERRO] Falha ao extrair Google Doc para {nome}: {e}")

    print(f"[{count}] novos roteiros do Giro extraídos da planilha.")
    return count

SYSTEM_PROMPT = """Você é um especialista em edição de roteiros de radiojornalismo. Sua tarefa é processar o texto recebido para o programa 'Giro nas Comarcas' e entregá-lo formatado para síntese de voz e edição automática.

REGRAS:
1. Sem formatação Markdown.
2. O formato de edição de áudio segue o padrão 'Audio-as-Text'. Insira OBRIGATORIAMENTE as tags de controle em letras maiúsculas:
   - ANTES da primeira fala (início do programa): [ASSET: ABERTURA]
   - DEPOIS da fala de introdução e ANTES da primeira matéria: [ASSET: PASSAGEM]
   - ENTRE AS MATÉRIAS (quando terminar de falar de uma comarca e passar para outra): [ASSET: PASSAGEM]
   - FIM DO PROGRAMA (após a última fala de tchau): [ASSET: ENCERRAMENTO]
3. O Giro não usa Trilha (BG). Não gere tags de TRILHA.
4. Substituir as marcações originais de locutores por:
Speaker 1: [texto da fala]
Speaker 2: [texto da fala]
5. Alterne as vozes entre as matérias para dar dinâmica ao programa, iniciando o programa com o Speaker 1.
6. REMOVA TOTALMENTE nomes próprios de apresentadores, repórteres e locutores. Não crie substitutos literais como "eu sou a equipe". Simplesmente exclua a apresentação. Ex: De "Olá, eu sou João, bem-vindos ao Giro", mude para "Olá, muito bem-vindos a mais uma edição do Giro nas Comarcas".
7. Escrever números, valores, porcentagens, datas e horas por extenso. Siglas letra por letra (ex: t j r n). Sites de forma literal.
8. Linguagem coloquial, leve e ágil.
"""

def giro_parse_hook(content: str) -> list:
    """Extrai comandos de ASSET e as falas separadas por locutor."""
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

        # 2. Capturar falas (Speaker 1 ou 2)
        match_loc = re.match(r'^(Speaker\s*[12]):\s*((?:\[.*?\])?\s*.*)$', linha, re.IGNORECASE)
        if match_loc:
            speaker = match_loc.group(1).lower().replace(" ", "")
            texto = match_loc.group(2).strip()
            
            # Limpar chaves sobressalentes
            texto = re.sub(r'\[.*?\]', '', texto).strip()
            
            if texto:
                blocks.append(("LOC", (speaker, texto)))
                
    return blocks

# ---------------------------------------------------------------------------
# Receita do Programa
# ---------------------------------------------------------------------------
receita_giro = ProgramRecipe(
    name="Giro nas Comarcas",
    drive_input_dir=GIRO_DRIVE_INPUT, 
    drive_output_dir=GIRO_DRIVE_OUTPUT,
    local_work_dir=LOCAL_WORK_DIR,
    system_prompt=SYSTEM_PROMPT,
    voice_strategy=VoiceStrategy(
        type='intra_file',
        voices=["pt-BR-FranciscaNeural", "pt-BR-AntonioNeural", "pt-BR-ElzaNeural", "pt-BR-ThalitaNeural"]
    ),
    assembly=AssemblyRecipe(
        profile_path=project_root / "assets" / "profiles" / "giro_profile.json"
    ),
    parse_hook=giro_parse_hook
)

if __name__ == "__main__":
    motor = PipelineEngine(receita_giro)
    
    async def run_giro():
        print("Sincronizando com a Planilha de Controle...")
        fetch_giro_from_sheet(motor.txt_dir)
        
        print("\nIniciando o processamento dos roteiros na pasta local 1_txt_bruto do Giro...")
        files = sorted([f for f in motor.txt_dir.glob("*.txt") if not f.name.endswith(".bak")])
        
        month_map_giro = {f"{k:02d}": f"{k} - {v}" for k, v in MONTH_MAP_SHORT.items()}
        
        for idx, f in enumerate(files):
            subfolder = ""
            ano = "2026" # Assumindo o ano padrão se não especificado no nome
            if "2025" in f.name:
                ano = "2025"

            # Procura por padrão de data DD-MM no nome do arquivo (ex: 09-06)
            month_match = re.search(r"-(\d{2})", f.name) 
            if month_match:
                mes_num = month_match.group(1)
                mes_pasta = month_map_giro.get(mes_num, "")
                if mes_pasta:
                    subfolder = f"{ano}/{mes_pasta}"
            else:
                # Fallback para o mês/ano atual para manter a organização 5S
                from datetime import datetime
                now = datetime.now()
                mes_num = f"{now.month:02d}"
                mes_pasta = month_map_giro.get(mes_num, "6 - JUN")
                subfolder = f"{now.year}/{mes_pasta}"
            
            await motor.run_file(f, file_idx=idx, subfolder=subfolder)
            
    asyncio.run(run_giro())
