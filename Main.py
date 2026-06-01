import os
import sys
import subprocess
import pathlib

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def run_script(path):
    try:
        subprocess.run([sys.executable, str(path)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n[ERRO] O script falhou com código {e.returncode}")
    except Exception as e:
        print(f"\n[ERRO] Ocorreu um problema ao rodar o script: {e}")
    input("\nPressione Enter para continuar...")

def menu():
    while True:
        clear_screen()
        print("========================================")
        print("   SISTEMA DE AUTOMAÇÃO RÁDIO TJRN")
        print("========================================")
        print("1. [NOTÍCIAS DA HORA]      Gerar Boletins (TTS)")
        print("2. [NOTÍCIAS DO JUDICIÁRIO] Gerar Jornal (NJUD)")
        print("3. [GIRO NAS COMARCAS]    Processar Programa")
        print("4. [RELATÓRIO]            Enviar por E-mail")
        print("----------------------------------------")
        print("0. Sair")
        print("========================================")
        
        choice = input("Selecione uma opção: ").strip()
        
        if choice == '1':
            run_script(pathlib.Path("modules/boletins/gerar_boletins_tts.py"))
        elif choice == '2':
            run_script(pathlib.Path("modules/jornal/gerar_locucao_multi_speaker.py"))
        elif choice == '3':
            run_script(pathlib.Path("modules/giro/giro_pipeline.py"))
        elif choice == '4':
            run_script(pathlib.Path("core/send_report.py"))
        elif choice == '0':
            print("Saindo...")
            break
        else:
            print("Opção inválida!")
            time.sleep(1)

if __name__ == "__main__":
    import time
    menu()
