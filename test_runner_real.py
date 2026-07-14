import os
import sys
import json
from voice_agent.runner import process_file

def main():
    input_path = r"H:\Meu Drive\RADIO TJRN CONTEÚDO\00_PRODUCAO_2026\01_BOLETINS_DIARIOS\01_ROTEIROS\06 - JUN - 26\18 06 - QUI\18 JUN B1-B6.mp3"
    
    print(f"Iniciando processamento do arquivo: {input_path}")
    
    if not os.path.exists(input_path):
        print("Arquivo não encontrado!")
        return

    result = process_file(input_path, auto_approve=False)
    
    print("\nResultado do Processamento:")
    # Print pretty JSON so it's easy to read
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
