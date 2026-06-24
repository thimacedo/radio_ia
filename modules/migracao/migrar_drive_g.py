# -*- coding: utf-8 -*-
"""
Script para varrer o Drive G:, identificar os arquivos da rádio e gerar
um catálogo ou executar a migração para o Drive H:.
"""

import os
import csv
import argparse
import shutil
import sys
from pathlib import Path
from tqdm import tqdm

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from regras_classificacao import identificar_programa_e_destino
from core.notificador_push import NotificadorPush

DRIVE_G_ROOT = "G:\\Meu Drive"
DRIVE_H_ROOT = "H:\\Meu Drive"
PASTA_ORGANIZACAO_G = os.path.join(DRIVE_G_ROOT, "Arquivos_Pessoais_Para_Verificacao")
CATALOGO_CSV = os.path.join(os.path.dirname(__file__), "catalogo_migracao.csv")

def varrer_e_catalogar():
    """Varre o Drive G e cria um arquivo CSV com as propostas de destino."""
    print(f"Iniciando varredura em {DRIVE_G_ROOT}...")
    
    arquivos_encontrados = []
    
    # Adicionamos algumas pastas seguras para não demorar demais buscando em node_modules ou afins
    for root, dirs, files in os.walk(DRIVE_G_ROOT):
        # Evita a pasta de organização, se ela já existir
        if "Arquivos_Pessoais_Para_Verificacao" in root:
            continue
            
        for file in files:
            caminho_completo = os.path.join(root, file)
            is_radio, programa, subcaminho_destino = identificar_programa_e_destino(caminho_completo)
            
            if not subcaminho_destino:
                continue

            destino_final = subcaminho_destino
            if is_radio:
                destino_final = os.path.join(DRIVE_H_ROOT, subcaminho_destino)
                # Mantém a hierarquia de ano/mês (ex: /02_PRODUCAO/GIRO/06 - JUN - 26) extraindo do arquivo original?
                # Vamos simplificar: coloca na raiz do destino. A organização 5S vai varrer e organizar lá depois!
                
            arquivos_encontrados.append({
                "Caminho Original": caminho_completo,
                "É da Rádio?": "SIM" if is_radio else "NÃO",
                "Programa Identificado": programa if programa else "-",
                "Destino Proposto": destino_final
            })

    print(f"Varredura concluída. {len(arquivos_encontrados)} arquivos encontrados (filtrados).")
    
    with open(CATALOGO_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Caminho Original", "É da Rádio?", "Programa Identificado", "Destino Proposto"])
        writer.writeheader()
        writer.writerows(arquivos_encontrados)
        
    print(f"Catálogo gerado em: {CATALOGO_CSV}")
    return arquivos_encontrados

def executar_migracao():
    """Lê o catálogo gerado e efetua a movimentação física dos arquivos."""
    if not os.path.exists(CATALOGO_CSV):
        print("Catálogo não encontrado! Execute com --dry-run primeiro.")
        return

    print("Iniciando migração baseada no catálogo...")
    with open(CATALOGO_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        linhas = list(reader)

    sucessos = 0
    erros = 0

    for linha in tqdm(linhas, desc="Movendo arquivos"):
        origem = linha["Caminho Original"]
        destino_dir = linha["Destino Proposto"]
        
        if not os.path.exists(origem):
            continue
            
        try:
            os.makedirs(destino_dir, exist_ok=True)
            nome_arquivo = os.path.basename(origem)
            caminho_destino = os.path.join(destino_dir, nome_arquivo)
            
            # Se o arquivo já existir no destino, pode dar erro no move, então vamos tratar
            if not os.path.exists(caminho_destino):
                shutil.move(origem, caminho_destino)
                sucessos += 1
            else:
                erros += 1
                print(f"Arquivo já existe no destino: {caminho_destino}")
        except Exception as e:
            erros += 1
            print(f"Erro ao mover {origem}: {e}")

    print(f"Migração concluída! Sucessos: {sucessos}, Erros/Ignorados: {erros}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ferramenta de migração do Drive G: para H:")
    parser.add_argument("--dry-run", action="store_true", help="Apenas varre e gera o catálogo CSV.")
    parser.add_argument("--execute", action="store_true", help="Executa a migração lendo o CSV.")
    
    args = parser.parse_args()
    
    if args.execute:
        confirm = input("CUIDADO: Isso moverá arquivos do Drive G:. Você revisou o catálogo? (s/n): ")
        if confirm.lower() == 's':
            executar_migracao()
            NotificadorPush().enviar(titulo="Migração do Drive G concluída", mensagem="Os arquivos foram migrados e organizados conforme o catálogo.", tags=["white_check_mark"], prioridade="default")
        else:
            print("Operação cancelada.")
    else:
        varrer_e_catalogar()
        NotificadorPush().enviar(titulo="Catálogo do Drive G gerado", mensagem="Varredura concluída. Verifique o arquivo catalogo_migracao.csv", tags=["mag"], prioridade="default")
