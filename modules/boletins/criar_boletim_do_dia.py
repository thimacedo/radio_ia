import os
import sys
import argparse
from datetime import datetime

# Ajuste de path para importar do core
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from core.constants import MONTH_MAP_FULL
except ImportError:
    MONTH_MAP_FULL = {
        1: "1 - JANEIRO", 2: "2 - FEVEREIRO", 3: "3 - MARÇO", 4: "4 - ABRIL",
        5: "5 - MAIO",    6: "6 - JUNHO",     7: "7 - JULHO",  8: "8 - AGOSTO",
        9: "9 - SETEMBRO",10: "10 - OUTUBRO", 11: "11 - NOVEMBRO", 12: "12 - DEZEMBRO"
    }

def criar_pastas(workspace_dir, data_alvo):
    try:
        # Obter dia e mês
        dia = str(data_alvo.day).zfill(2)
        mes_num = data_alvo.month
        mes_nome = MONTH_MAP_FULL.get(mes_num)
        
        if not mes_nome:
            print(f"[ERRO] Mês inválido: {mes_num}")
            return False
            
        # Definir caminhos
        boletins_dir = os.path.join(workspace_dir, "boletins")
        mes_dir = os.path.join(boletins_dir, mes_nome)
        dia_dir = os.path.join(mes_dir, dia)
        
        path_edit = os.path.join(dia_dir, "edit")
        path_mailing = os.path.join(dia_dir, "mailing")
        
        # Criar diretórios
        os.makedirs(path_edit, exist_ok=True)
        os.makedirs(path_mailing, exist_ok=True)
        
        print(f"=== ESTRUTURA DE BOLETINS CRIADA ===")
        print(f"Data: {dia}/{mes_num}")
        print(f"Pasta Edit: {path_edit}")
        print(f"Pasta Mailing: {path_mailing}")
        return True
    except Exception as e:
        print(f"[ERRO] Falha ao criar a estrutura de pastas: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Cria a estrutura de pastas de boletins do dia.")
    parser.add_argument(
        "--data", 
        help="Data específica no formato DD-MM (ex: 30-05). Se omitida, usa o dia atual."
    )
    parser.add_argument(
        "--workspace",
        default=os.path.dirname(os.path.abspath(__file__)),
        help="Caminho do workspace do projeto."
    )
    args = parser.parse_args()
    
    workspace = args.workspace.replace("\\", "/")
    
    if args.data:
        try:
            # Tentar fazer o parse do formato DD-MM
            data_parsed = datetime.strptime(args.data, "%d-%m")
            # Assumir o ano atual para o objeto datetime
            ano_atual = datetime.now().year
            data_alvo = data_parsed.replace(year=ano_atual)
        except ValueError:
            try:
                # Tentar fazer o parse do formato DD-MM-YYYY
                data_alvo = datetime.strptime(args.data, "%d-%m-%Y")
            except ValueError:
                print("[ERRO] Formato de data inválido. Use DD-MM ou DD-MM-YYYY.")
                sys.exit(1)
    else:
        data_alvo = datetime.now()
        
    sucesso = criar_pastas(workspace, data_alvo)
    if not sucesso:
        sys.exit(1)

if __name__ == "__main__":
    main()
