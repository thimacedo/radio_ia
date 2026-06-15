import os
import shutil
import re
from datetime import datetime

# Obter o caminho relativo ao script atual de forma dinâmica
script_dir = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
LOCAL_BOLETINS_DIR = os.path.join(script_dir, "boletins").replace("\\", "/")

# Novas bases de caminhos do Drive configuradas de acordo com o mapeamento 5S de 2026
DRIVE_ROTEIROS_BASE = r"H:/Meu Drive/RADIO TJRN CONTEÚDO/00_PRODUCAO_2026/01_BOLETINS_DIARIOS/01_ROTEIROS"
DRIVE_MAILING_BASE = r"H:/Meu Drive/RADIO TJRN CONTEÚDO/00_PRODUCAO_2026/01_BOLETINS_DIARIOS/02_AUDIOS_MAILING"
DRIVE_RADIO_BASE = r"H:/Meu Drive/RADIO TJRN CONTEÚDO/00_PRODUCAO_2026/01_BOLETINS_DIARIOS/03_AUDIOS_RADIO"

MONTH_NAMES_SHORT = {
    1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR", 5: "MAI", 6: "JUN",
    7: "JUL", 8: "AGO", 9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ"
}

WEEKDAYS_PT = {
    0: "SEG", 1: "TER", 2: "QUA", 3: "QUI", 4: "SEX", 5: "SAB", 6: "DOM"
}

def obter_dia_semana_pt(ano, mes, dia):
    try:
        dt = datetime(ano, mes, dia)
        return WEEKDAYS_PT[dt.weekday()]
    except Exception:
        return "SEG"

def buscar_ou_criar_pasta_mes(base_path, mes_num):
    if not os.path.exists(base_path):
        print(f"[AVISO] Pasta base não existe no Drive: {base_path}")
        return None
        
    prefix = f"{mes_num:02d} -"
    for item in os.listdir(base_path):
        if item.startswith(prefix) and os.path.isdir(os.path.join(base_path, item)):
            return os.path.join(base_path, item).replace("\\", "/")
            
    # Criar se não existir no formato padronizado 5S: 0X - MES - 26 (Ex: 06 - JUN - 26)
    short_name = MONTH_NAMES_SHORT.get(mes_num, "MES")
    folder_name = f"{mes_num:02d} - {short_name} - 26"
        
    new_path = os.path.join(base_path, folder_name).replace("\\", "/")
    os.makedirs(new_path, exist_ok=True)
    print(f"Criada pasta de mês no Drive: {new_path}")
    return new_path

def sincronizar():
    print("=== Sincronizando Boletins com o Google Drive (Estrutura 5S 2026) ===")
    
    if not os.path.exists(LOCAL_BOLETINS_DIR):
        print(f"[ERRO] Pasta local de boletins não encontrada: {LOCAL_BOLETINS_DIR}")
        return
        
    total_copiados = 0
    
    # Percorrer a pasta local de boletins
    for mes_folder in os.listdir(LOCAL_BOLETINS_DIR):
        # Ignorar pastas de sistema ou auxiliares
        if mes_folder == "VHT" or mes_folder == "planilha_csv" or not "-" in mes_folder:
            continue
            
        mes_path = os.path.join(LOCAL_BOLETINS_DIR, mes_folder).replace("\\", "/")
        if not os.path.isdir(mes_path):
            continue
            
        # Extrair número do mês a partir de "5 - MAIO" ou "6 - JUNHO"
        m_match = re.match(r'(\d+)\s*-', mes_folder)
        if not m_match:
            continue
        mes_num = int(m_match.group(1))
        
        for dia_folder in os.listdir(mes_path):
            dia_path = os.path.join(mes_path, dia_folder).replace("\\", "/")
            if not os.path.isdir(dia_path):
                continue
                
            try:
                dia_num = int(dia_folder)
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
            drive_roteiros_day_path = os.path.join(drive_roteiros_month, dia_folder_name).replace("\\", "/")
            drive_mailing_day_path = os.path.join(drive_mailing_month, dia_folder_name).replace("\\", "/")
            drive_radio_day_path = os.path.join(drive_radio_month, dia_folder_name).replace("\\", "/")
            
            os.makedirs(drive_roteiros_day_path, exist_ok=True)
            os.makedirs(drive_mailing_day_path, exist_ok=True)
            os.makedirs(drive_radio_day_path, exist_ok=True)
            
            # 1. Copiar arquivos de edit/ para a pasta do Drive de áudios rádio
            local_edit_dir = os.path.join(dia_path, "edit").replace("\\", "/")
            if os.path.exists(local_edit_dir):
                for file in os.listdir(local_edit_dir):
                    if file.endswith(".mp3"):
                        src = os.path.join(local_edit_dir, file).replace("\\", "/")
                        dst = os.path.join(drive_radio_day_path, file).replace("\\", "/")
                        shutil.copy2(src, dst)
                        print(f"  [RADIO/EDITADO] Copiado para o Drive: {dst}")
                        total_copiados += 1
                            
            # 2. Copiar arquivos de mailing/ para a pasta do Drive de mailing
            local_mailing_dir = os.path.join(dia_path, "mailing").replace("\\", "/")
            if os.path.exists(local_mailing_dir):
                for file in os.listdir(local_mailing_dir):
                    if file.endswith(".mp3"):
                        src = os.path.join(local_mailing_dir, file).replace("\\", "/")
                        dst = os.path.join(drive_mailing_day_path, file).replace("\\", "/")
                        shutil.copy2(src, dst)
                        print(f"  [MAILING] Copiado para o Drive: {dst}")
                        total_copiados += 1
                            
            # 3. Copiar arquivos de texto (.txt) para a pasta do Drive de roteiros
            for file in os.listdir(dia_path):
                if file.endswith(".txt"):
                    src = os.path.join(dia_path, file).replace("\\", "/")
                    dst = os.path.join(drive_roteiros_day_path, file).replace("\\", "/")
                    shutil.copy2(src, dst)
                    print(f"  [ROTEIRO (TEXTO)] Copiado para o Drive: {dst}")
                    total_copiados += 1
                        
    print(f"\nSincronização concluída. Total de novos arquivos copiados: {total_copiados}")

if __name__ == "__main__":
    sincronizar()
