import os
import sys
import pathlib
import shutil
import datetime
import json

# Paths configuration
ROOT_DRIVE = r"H:/Meu Drive/RADIO TJRN CONTEÚDO/PROGRAMAS/PROGRAMA GIRO NAS COMARCAS (10min)"
WORKSPACE = r"e:/NJUD/PROGRAMA GIRO NAS COMARCAS"
REPORTS_DIR = os.path.join(WORKSPACE, "relatorios")
TTS_DIR = os.path.join(WORKSPACE, "tts_txt")

os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(TTS_DIR, exist_ok=True)

def is_mp3_file(fname):
    return fname.lower().endswith('.mp3') and (fname.startswith('GNC') or fname.startswith('GC'))

def extract_info_2025(mp3_name):
    # Expected format: GNC-<num>-<date>.mp3
    parts = mp3_name[:-4].split('-')  # remove .mp3
    if len(parts) >= 3:
        num = parts[1]
        date_str = parts[2]
        try:
            date = datetime.datetime.strptime(date_str, "%Y%m%d").date()
        except ValueError:
            date = date_str
        return num, str(date)
    return None, None

def extract_info_2026(mp3_name):
    # Expected format: GNC-<date>.mp3 (date may be YYYYMMDD or YYYY-MM-DD)
    parts = mp3_name[:-4].split('-')
    if len(parts) >= 2:
        date_part = parts[1]
        for fmt in ("%Y%m%d", "%Y-%m-%d"):
            try:
                date = datetime.datetime.strptime(date_part, fmt).date()
                return str(date)
            except ValueError:
                continue
        return date_part
    return None

def find_roteiro(folder_path):
    for ext in [".docx", ".gdoc", ".txt"]:
        for f in os.listdir(folder_path):
            if f.lower().endswith(ext) and ("pauta" in f.lower() or "roteiro" in f.lower() or "gdoc" in f.lower()):
                return os.path.join(folder_path, f)
    return None

def convert_to_txt(source_path, dest_dir):
    base = pathlib.Path(source_path).stem
    dest_path = os.path.join(dest_dir, f"{base}.txt")
    try:
        with open(source_path, 'rb') as src, open(dest_path, 'wb') as dst:
            shutil.copyfileobj(src, dst)
    except Exception as e:
        print(f"Failed to convert {source_path} to txt: {e}")
    return dest_path

def process_year(year):
    year_path = os.path.join(ROOT_DRIVE, str(year))
    report_lines = []
    missing_2026 = []
    for entry in sorted(os.listdir(year_path)):
        prog_dir = os.path.join(year_path, entry)
        if not os.path.isdir(prog_dir):
            continue
        mp3_files = [f for f in os.listdir(prog_dir) if is_mp3_file(f)]
        roteiro_path = find_roteiro(prog_dir)
        roteiro_ok = bool(roteiro_path)
        audio_ok = bool(mp3_files)
        if year == 2025:
            prog_num = entry
            date = ""
            if audio_ok:
                num, date_extracted = extract_info_2025(mp3_files[0])
                if date_extracted:
                    date = date_extracted
            report_lines.append(f"| {prog_num} | {date} | {'✅' if roteiro_ok else '❌'} | {'✅' if audio_ok else '❌'} |")
        else:
            prog_num = entry
            if audio_ok:
                for mp3 in mp3_files:
                    src = os.path.join(prog_dir, mp3)
                    date_part = extract_info_2026(mp3) or "unknown"
                    new_name = f"GNC-{date_part}.mp3"
                    dest = os.path.join(WORKSPACE, prog_num, new_name)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.copy2(src, dest)
            else:
                missing_2026.append(prog_num)
                if roteiro_path:
                    convert_to_txt(roteiro_path, TTS_DIR)
    if year == 2025:
        report_path = os.path.join(REPORTS_DIR, "relatorio_2025.md")
        header = "| Programa | Data | Roteiro OK | Audio OK |\n|---|---|---|---|\n"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Relatório Giro nas Comarcas – 2025\n\n")
            f.write(header)
            f.writelines(line + "\n" for line in report_lines)
    else:
        prod_path = os.path.join(REPORTS_DIR, "relatorio_2026.md")
        with open(prod_path, "w", encoding="utf-8") as f:
            f.write("# Relatório Produção Giro nas Comarcas – 2026\n\n")
            f.write("## Programas com áudio gerado\n")
            f.write("(arquivos .mp3 copiados para a estrutura de workspace)\n\n")
            f.write("## Programas faltando áudio\n")
            for prog in missing_2026:
                f.write(f"- {prog}\n")

def main():
    print("Iniciando auditoria Giro nas Comarcas...")
    os.makedirs(WORKSPACE, exist_ok=True)
    process_year(2025)
    process_year(2026)
    print("Auditoria concluída. Relatórios em:", REPORTS_DIR)
    print("Arquivos de TTS em:", TTS_DIR)

if __name__ == "__main__":
    main()
