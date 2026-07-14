# -*- coding: utf-8 -*-
"""
Script de Configuração e Implantação do Repositório - Estúdio Rádio IA (TJRN / NJUD)
----------------------------------------------------------------------------------
Este script automatiza a preparação do ambiente virtual, instalação de dependências
e configuração do arquivo .env para que o sistema funcione em qualquer máquina de edição.
"""

import os
import shutil
import subprocess
import sys

def main():
    print("=====================================================================")
    print("   ESTÚDIO RÁDIO IA - TJRN / NJUD: INSTALAÇÃO E CONFIGURAÇÃO LOCAL   ")
    print("=====================================================================")
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Copiar .env.example para .env se não existir
    env_path = os.path.join(project_root, ".env")
    env_example_path = os.path.join(project_root, ".env.example")
    
    if not os.path.exists(env_path):
        if os.path.exists(env_example_path):
            print("\n[CONFIG] Arquivo '.env' não encontrado. Criando a partir de '.env.example'...")
            shutil.copy2(env_example_path, env_path)
            print("[OK] Arquivo '.env' criado com sucesso. IMPORTANTE: Edite-o com suas chaves de API.")
        else:
            print("\n[ALERTA] Arquivo '.env.example' não encontrado. Por favor, crie o '.env' manualmente.")
    else:
        print("\n[CONFIG] Arquivo '.env' já existe. Mantendo configurações existentes.")

    # 2. Criar ambiente virtual python (venv)
    venv_dir = os.path.join(project_root, "venv")
    if not os.path.exists(venv_dir):
        print("\n[VENV] Criando ambiente virtual Python (venv) no diretório 'venv'...")
        try:
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            print("[OK] Ambiente virtual criado com sucesso.")
        except Exception as e:
            print(f"[ERRO] Falha ao criar ambiente virtual: {e}")
            sys.exit(1)
    else:
        print("\n[VENV] Ambiente virtual 'venv' já existe. Pulando criação.")

    # 3. Detectar executável do pip no venv
    if os.name == 'nt':  # Windows
        pip_path = os.path.join(venv_dir, "Scripts", "pip.exe")
        python_path = os.path.join(venv_dir, "Scripts", "python.exe")
    else:  # Unix
        pip_path = os.path.join(venv_dir, "bin", "pip")
        python_path = os.path.join(venv_dir, "bin", "python")

    # 4. Instalar dependências do requirements.txt
    requirements_path = os.path.join(project_root, "requirements.txt")
    if os.path.exists(requirements_path):
        print("\n[PIP] Instalando dependências a partir do 'requirements.txt'...")
        try:
            subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
            print("[OK] Dependências instaladas com sucesso.")
        except Exception as e:
            print(f"[ERRO] Falha ao instalar dependências: {e}")
            sys.exit(1)
    else:
        print("\n[ERRO] Arquivo 'requirements.txt' não encontrado. Não foi possível instalar as dependências.")
        sys.exit(1)

    print("\n=====================================================================")
    print("                    IMPLANTAÇÃO CONCLUÍDA COM SUCESSO!                ")
    print("=====================================================================")
    print(f"1. As dependências foram instaladas no ambiente virtual em:\n   {venv_dir}")
    print("2. IMPORTANTE: Abra o arquivo '.env' e configure suas chaves de API.")
    print("3. Para executar os agentes, ative o ambiente virtual e execute o pipeline:")
    print("   No Windows (PowerShell):")
    print("     .\\venv\\Scripts\\Activate.ps1")
    print("     python modules\\boletins\\gerar_boletins_tts.py")
    print("=====================================================================\n")

if __name__ == "__main__":
    main()
