import os
import shutil
import re
import sys
from pathlib import Path
from datetime import datetime

# Configurar caminhos relativos de forma dinâmica
script_dir = Path(__file__).parent.resolve()
project_root = script_dir.parent.parent.resolve()

if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

try:
    from core.best_practices import carregar_env_var, MONTH_MAP_SHORT, WEEKDAYS_PT
except ImportError:
    def carregar_env_var(chave, fallback):
        return fallback
    MONTH_MAP_SHORT = {
        1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR", 5: "MAI", 6: "JUN",
        7: "JUL", 8: "AGO", 9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ"
    }
    WEEKDAYS_PT = {0: "SEG", 1: "TER", 2: "QUA", 3: "QUI", 4: "SEX", 5: "SAB", 6: "DOM"}

# Obter bases do Drive
DRIVE_ROOT = Path(carregar_env_var("DRIVE_ROOT", "H:/Meu Drive/RADIO TJRN CONTEÚDO"))
DRIVE_ROTEIROS_BASE = DRIVE_ROOT / "00_PRODUCAO_2026" / "01_BOLETINS_DIARIOS" / "01_ROTEIROS"
DRIVE_MAILING_BASE = DRIVE_ROOT / "00_PRODUCAO_2026" / "01_BOLETINS_DIARIOS" / "02_AUDIOS_MAILING"
DRIVE_RADIO_BASE = DRIVE_ROOT / "00_PRODUCAO_2026" / "01_BOLETINS_DIARIOS" / "03_AUDIOS_RADIO"

LOCAL_BOLETINS_DIR = script_dir / "boletins"

def obter_dia_semana_pt(ano, mes, dia):
    try:
        dt = datetime(ano, mes, dia)
        return WEEKDAYS_PT[dt.weekday()]
    except Exception:
        return "SEG"

def buscar_ou_criar_pasta_mes(base_path: Path, mes_num: int) -> Path | None:
    if not base_path.exists():
        print(f"[AVISO] Pasta base não existe no Drive: {base_path}")
        return None
        
    prefix = f"{mes_num:02d} -"
    for item in base_path.iterdir():
        if item.is_dir() and item.name.startswith(prefix):
            return item
            
    # Criar se não existir no formato padronizado 5S: 0X - MES - 26 (Ex: 06 - JUN - 26)
    short_name = MONTH_MAP_SHORT.get(mes_num, "MES")
    folder_name = f"{mes_num:02d} - {short_name} - 26"
    
    new_path = base_path / folder_name
    new_path.mkdir(parents=True, exist_ok=True)
    print(f"Criada pasta de mês no Drive: {new_path}")
    return new_path

def sincronizar():
    print("=== Sincronizando Boletins com o Google Drive (Estrutura 5S 2026) ===")
    
    if not LOCAL_BOLETINS_DIR.exists():
        print(f"[ERRO] Pasta local de boletins não encontrada: {LOCAL_BOLETINS_DIR}")
        return
        
    total_copiados = 0
    
    # Percorrer a pasta local de boletins
    for mes_folder in LOCAL_BOLETINS_DIR.iterdir():
        if not mes_folder.is_dir():
            continue
        # Ignorar pastas de sistema ou auxiliares
        if mes_folder.name == "VHT" or mes_folder.name == "planilha_csv" or "-" not in mes_folder.name:
            continue
            
        # Extrair número do mês a partir de "5 - MAIO" ou "6 - JUNHO"
        m_match = re.match(r'(\d+)\s*-', mes_folder.name)
        if not m_match:
            continue
        mes_num = int(m_match.group(1))
        
        for dia_folder in mes_folder.iterdir():
            if not dia_folder.is_dir():
                continue
                
            try:
                dia_num = int(dia_folder.name)
            except ValueError:
                continue
                
            # Buscar/criar pastas de meses no Drive
            drive_roteiros_month = buscar_ou_criar_pasta_mes(DRIVE_ROTEIROS_BASE, mes_num)
            drive_mailing_month = buscar_ou_criar_pasta_mes(DRIVE_MAILING_BASE, mes_num)
            drive_radio_month = buscar_ou_criar_pasta_mes(DRIVE_RADIO_BASE, mes_num)
            
            if not drive_roteiros_month or not drive_mailing_month or not drive_radio_month:
                print(f"[AVISO] Falha ao acessar ou criar pastas no Drive para o mês {mes_num}.")
                continue
                
            # Definir caminhos de dias no Drive (Formato: "DD MM - DIA_DA_SEMANA", ex: "08 06 - SEG")
            dia_semana = obter_dia_semana_pt(2026, mes_num, dia_num)
            dia_folder_name = f"{dia_num:02d} {mes_num:02d} - {dia_semana}"
            drive_roteiros_day_path = drive_roteiros_month / dia_folder_name
            drive_mailing_day_path = drive_mailing_month / dia_folder_name
            drive_radio_day_path = drive_radio_month / dia_folder_name
            
            drive_roteiros_day_path.mkdir(parents=True, exist_ok=True)
            drive_mailing_day_path.mkdir(parents=True, exist_ok=True)
            drive_radio_day_path.mkdir(parents=True, exist_ok=True)
            
            # 1. Copiar arquivos de edit/ para a pasta do Drive de áudios rádio
            local_edit_dir = dia_folder / "edit"
            if local_edit_dir.exists():
                for file_path in local_edit_dir.iterdir():
                    if file_path.is_file() and file_path.suffix == ".mp3":
                        dst = drive_radio_day_path / file_path.name
                        shutil.copy2(file_path, dst)
                        print(f"  [RADIO/EDITADO] Copiado para o Drive: {dst}")
                        total_copiados += 1
                            
            # 2. Copiar arquivos de mailing/ para a pasta do Drive de mailing
            local_mailing_dir = dia_folder / "mailing"
            if local_mailing_dir.exists():
                for file_path in local_mailing_dir.iterdir():
                    if file_path.is_file() and file_path.suffix == ".mp3":
                        dst = drive_mailing_day_path / file_path.name
                        shutil.copy2(file_path, dst)
                        print(f"  [MAILING] Copiado para o Drive: {dst}")
                        total_copiados += 1
                            
            # 3. Copiar arquivos de texto (.txt) para a pasta do Drive de roteiros
            for file_path in dia_folder.iterdir():
                if file_path.is_file() and file_path.suffix == ".txt":
                    dst = drive_roteiros_day_path / file_path.name
                    shutil.copy2(file_path, dst)
                    print(f"  [ROTEIRO (TEXTO)] Copiado para o Drive: {dst}")
                    total_copiados += 1
                        
    print(f"\nSincronização concluída. Total de novos arquivos copiados: {total_copiados}")

if __name__ == "__main__":
    sincronizar()
