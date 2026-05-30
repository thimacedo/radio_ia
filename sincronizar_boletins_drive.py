import os
import shutil
import re
from datetime import datetime

LOCAL_BOLETINS_DIR = r"e:/NJUD/boletins"
DRIVE_EDITED_BASE = r"H:/Meu Drive/RADIO TJRN CONTEÚDO/EDIÇÃO/BOLETINS/2026"
DRIVE_MAILING_BASE = r"H:/Meu Drive/RADIO TJRN CONTEÚDO/1-BOLETINS ENVIADOS/2026"

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

def buscar_ou_criar_pasta_mes(base_path, mes_num, format_type):
    if not os.path.exists(base_path):
        print(f"[AVISO] Pasta base não existe no Drive: {base_path}")
        return None
        
    prefix = f"{mes_num:02d} -"
    for item in os.listdir(base_path):
        if item.startswith(prefix) and os.path.isdir(os.path.join(base_path, item)):
            return os.path.join(base_path, item)
            
    # Criar se não existir
    short_name = MONTH_NAMES_SHORT.get(mes_num, "MES")
    if format_type == "edited":
        # Formato: 05 - MAI - 26
        folder_name = f"{mes_num:02d} - {short_name} - 26"
    else:
        # Formato: 05 - MAI - 2026
        folder_name = f"{mes_num:02d} - {short_name} - 2026"
        
    new_path = os.path.join(base_path, folder_name).replace("\\", "/")
    os.makedirs(new_path, exist_ok=True)
    print(f"Criada pasta de mês no Drive: {new_path}")
    return new_path

def sincronizar():
    print("=== Sincronizando Boletins com o Google Drive ===")
    
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
            
        # Extrair número do mês a partir de "5 - MAIO"
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
                
            # Determinar dia da semana
            ano = 2026
            weekday = obter_dia_semana_pt(ano, mes_num, dia_num)
            
            # Buscar/criar pastas de meses no Drive
            drive_edited_month = buscar_ou_criar_pasta_mes(DRIVE_EDITED_BASE, mes_num, "edited")
            drive_mailing_month = buscar_ou_criar_pasta_mes(DRIVE_MAILING_BASE, mes_num, "mailing")
            
            if not drive_edited_month or not drive_mailing_month:
                continue
                
            # Definir caminhos de dias no Drive
            # Editados: DD MM (ex: "22 05")
            dia_edited_folder = f"{dia_num:02d} {mes_num:02d}"
            drive_edited_day_path = os.path.join(drive_edited_month, dia_edited_folder).replace("\\", "/")
            
            # Mailing: DD MM (ex: "22 05")
            dia_mailing_folder = f"{dia_num:02d} {mes_num:02d}"
            drive_mailing_day_path = os.path.join(drive_mailing_month, dia_mailing_folder).replace("\\", "/")
            
            os.makedirs(drive_edited_day_path, exist_ok=True)
            os.makedirs(drive_mailing_day_path, exist_ok=True)
            
            # 1. Copiar arquivos de edit/ para a pasta do Drive de editados
            local_edit_dir = os.path.join(dia_path, "edit").replace("\\", "/")
            if os.path.exists(local_edit_dir):
                for file in os.listdir(local_edit_dir):
                    if file.endswith(".mp3"):
                        src = os.path.join(local_edit_dir, file).replace("\\", "/")
                        dst = os.path.join(drive_edited_day_path, file).replace("\\", "/")
                        if not os.path.exists(dst):
                            shutil.copy2(src, dst)
                            print(f"  [EDITADO] Copiado para o Drive: {dst}")
                            total_copiados += 1
                            
            # 2. Copiar arquivos de mailing/ para a pasta do Drive de mailing
            local_mailing_dir = os.path.join(dia_path, "mailing").replace("\\", "/")
            if os.path.exists(local_mailing_dir):
                for file in os.listdir(local_mailing_dir):
                    if file.endswith(".mp3"):
                        src = os.path.join(local_mailing_dir, file).replace("\\", "/")
                        dst = os.path.join(drive_mailing_day_path, file).replace("\\", "/")
                        if not os.path.exists(dst):
                            shutil.copy2(src, dst)
                            print(f"  [MAILING] Copiado para o Drive: {dst}")
                            total_copiados += 1
                            
            # 3. Copiar arquivos de texto (.txt) para a pasta do Drive de editados (para registro)
            for file in os.listdir(dia_path):
                if file.endswith(".txt"):
                    src = os.path.join(dia_path, file).replace("\\", "/")
                    dst = os.path.join(drive_edited_day_path, file).replace("\\", "/")
                    if not os.path.exists(dst):
                        shutil.copy2(src, dst)
                        print(f"  [TEXTO] Copiado para o Drive: {dst}")
                        total_copiados += 1
                        
    print(f"\nSincronização concluída. Total de novos arquivos copiados: {total_copiados}")

if __name__ == "__main__":
    sincronizar()
