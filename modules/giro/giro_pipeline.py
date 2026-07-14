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

def buscar_pendencias_giro_drive(drive_root):
    print("\n[Mapeamento Físico] Varrendo pastas de Giro nas Comarcas no Google Drive...")
    path_roteiros_base = os.path.join(drive_root, "00_PRODUCAO_2026", "03_GIRO_NAS_COMARCAS", "01_ROTEIROS").replace("\\", "/")
    path_audios_base = os.path.join(drive_root, "00_PRODUCAO_2026", "03_GIRO_NAS_COMARCAS").replace("\\", "/")
    
    pendencias_fisicas = []
    
    if not os.path.exists(path_roteiros_base):
        print(f"  [AVISO] Pasta base de roteiros do Giro não encontrada: {path_roteiros_base}")
        return []
        
    from core.constants import folder_name_5s, ANO_SHORT
    
    # Varre recursivamente a pasta de roteiros do Giro
    for root, dirs, files in os.walk(path_roteiros_base):
        for file_name in files:
            if file_name.startswith("desktop.ini") or file_name.startswith("."):
                continue
                
            suffix = os.path.splitext(file_name)[1].lower()
            if suffix not in [".gdoc", ".txt"]:
                continue
                
            nome_doc = os.path.splitext(file_name)[0]
            if "GIRO" not in nome_doc.upper():
                continue
                
            file_path = os.path.join(root, file_name).replace("\\", "/")
            
            # Extrair mês do nome do arquivo
            mes_num = None
            month_match = re.search(r"[-_](\d{2})", nome_doc)
            if month_match:
                mes_num = int(month_match.group(1))
            else:
                # Se não encontrar no nome, tenta extrair da pasta correspondente
                parent_folder = os.path.basename(root)
                sub_match = re.match(r"(\d+)\s*-", parent_folder)
                if sub_match:
                    mes_num = int(sub_match.group(1))
                else:
                    from datetime import datetime
                    mes_num = datetime.now().month
                    
            folder_name = folder_name_5s(mes_num, ANO_SHORT)
            
            # Verificar se já existe o áudio correspondente na pasta de áudio do respectivo mês
            drive_audio_path = os.path.join(path_audios_base, folder_name, f"{nome_doc}.mp3").replace("\\", "/")
            
            if os.path.exists(drive_audio_path):
                continue
                
            print(f"  [PENDÊNCIA DETECTADA VIA DRIVE] Giro: '{nome_doc}' -> Sem áudio em '{folder_name}'.")
            pendencias_fisicas.append((nome_doc, file_path, folder_name))
            
    return pendencias_fisicas

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
        drive_root = carregar_env_var("DRIVE_ROOT", "H:/Meu Drive/RADIO TJRN CONTEÚDO")
        
        print("Buscando pendências físicas de Giro no Drive...")
        pendencias = buscar_pendencias_giro_drive(drive_root)
        
        if not pendencias:
            print("\n[INFO] Nenhuma pendência do Giro nas Comarcas encontrada! Tudo finalizado.")
            print("[PRODUCAO_COUNT] 0")
            sys.exit(0)
            
        print(f"\nTotal de pendências detectadas no Giro: {len(pendencias)}")
        
        # 1. Extrair os roteiros para a pasta de trabalho local
        motor.txt_dir.mkdir(parents=True, exist_ok=True)
        for nome_doc, file_path, folder_name in pendencias:
            suffix = os.path.splitext(file_path)[1].lower()
            try:
                if suffix == ".gdoc":
                    texto = export_gdoc_to_txt(pathlib.Path(file_path))
                else:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f_in:
                        texto = f_in.read()
                
                dest_txt = motor.txt_dir / f"{nome_doc}.txt"
                dest_txt.write_text(texto, encoding="utf-8")
                print(f"  [OK] Roteiro extraído para {dest_txt.name}")
            except Exception as e_ext:
                print(f"  [ERRO] Falha ao extrair/copiar roteiro de {file_path}: {e_ext}")
                
        print("\nIniciando o processamento dos roteiros do Giro...")
        files = sorted([f for f in motor.txt_dir.glob("*.txt") if not f.name.endswith(".bak")])
        
        from core.constants import folder_name_5s, ANO_SHORT
        import shutil
        
        sucessos = 0
        for idx, f in enumerate(files):
            subfolder = ""
            
            # Procura por padrão de data DD-MM no nome do arquivo (ex: 09-06)
            month_match = re.search(r"-(\d{2})", f.name) 
            if month_match:
                mes_num = int(month_match.group(1))
                subfolder = folder_name_5s(mes_num, ANO_SHORT)
            else:
                from datetime import datetime
                mes_num = datetime.now().month
                subfolder = folder_name_5s(mes_num, ANO_SHORT)
            
            try:
                await motor.run_file(f, file_idx=idx, subfolder=subfolder)
                sucessos += 1
                
                # Copiar o roteiro revisado txt para a pasta correspondente no Drive
                local_rev = motor.rev_dir / f.name
                if local_rev.exists():
                    drive_roteiro_dir = pathlib.Path(drive_root) / "00_PRODUCAO_2026" / "03_GIRO_NAS_COMARCAS" / "01_ROTEIROS" / subfolder
                    drive_roteiro_dir.mkdir(parents=True, exist_ok=True)
                    drive_roteiro_dest = drive_roteiro_dir / f.name
                    shutil.copy2(local_rev, drive_roteiro_dest)
                    print(f"  [ROTEIRO 5S] Copiado de volta para: {drive_roteiro_dest}")
            except Exception as e_proc:
                print(f"  [ERRO] Falha no processamento de {f.name}: {e_proc}")
                
        # Limpar lixo do workspace local (padrão 5S)
        try:
            for folder in ["1_txt_bruto", "2_txt_revisado", "3_audio_final"]:
                dir_to_clean = LOCAL_WORK_DIR / folder
                if dir_to_clean.exists():
                    for file_path in dir_to_clean.iterdir():
                        if file_path.is_file():
                            file_path.unlink()
            print("  [LIMPEZA 5S] Lixo local limpo no workspace de Giro.")
        except Exception as e_clean:
            print(f"  [AVISO] Falha ao limpar workspace local: {e_clean}")
            
        print(f"\n[PRODUCAO_COUNT] {sucessos}")
        print("\n=== PIPELINE DO GIRO CONCLUÍDO ===")
            
    asyncio.run(run_giro())
