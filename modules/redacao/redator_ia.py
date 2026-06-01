import os
import sys
import pathlib

# Ajuste de path para importar do core
current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.append(str(project_root))

from core.llm_factory import LLMFactory

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def run_redator():
    llm = LLMFactory()
    
    templates_dir = current_dir / "templates"
    inputs_dir = current_dir / "inputs"
    outputs_dir = current_dir / "outputs"
    
    for d in [templates_dir, inputs_dir, outputs_dir]:
        d.mkdir(parents=True, exist_ok=True)
        
    clear_screen()
    print("========================================")
    print("        REDAÇÃO IA - TJRN")
    print("========================================")
    print("Escolha o tipo de programa para gerar:")
    print("1. Boletim (Notícias da Hora)")
    print("2. NJUD (Notícias do Judiciário)")
    print("3. Giro nas Comarcas")
    print("----------------------------------------")
    print("0. Voltar")
    print("========================================")
    
    choice = input("Opção: ").strip()
    
    if choice == '0':
        return
        
    template_file = ""
    program_name = ""
    if choice == '1':
        template_file = "template_boletim.txt"
        program_name = "Boletim"
    elif choice == '2':
        template_file = "template_njud.txt"
        program_name = "NJUD"
    elif choice == '3':
        template_file = "template_giro.txt"
        program_name = "Giro"
    else:
        print("Opção inválida.")
        return
        
    template_path = templates_dir / template_file
    if not template_path.exists():
        print(f"[ERRO] Template não encontrado: {template_path}")
        return
        
    system_prompt = template_path.read_text(encoding="utf-8")
    
    # Coletar todo o material base
    input_files = list(inputs_dir.glob("*.txt"))
    if not input_files:
        print(f"\n[AVISO] Nenhum arquivo .txt encontrado em {inputs_dir}.")
        print("Por favor, coloque os textos base/notícias nessa pasta e tente novamente.")
        return
        
    print(f"\n[Lendo fontes de dados em {inputs_dir}]")
    source_material = ""
    for f in input_files:
        print(f"  - {f.name}")
        source_material += f"--- CONTEÚDO DE: {f.name} ---\n"
        source_material += f.read_text(encoding="utf-8", errors="replace")
        source_material += "\n\n"
        
    print(f"\n[Gerando roteiro via IA para {program_name} (Aguarde...)]")
    
    try:
        user_prompt = f"Aqui está o material base para a criação do programa:\n\n{source_material}"
        final_script = llm.ask(system_prompt, user_prompt)
        
        output_name = f"Roteiro_{program_name}_Gerado.txt"
        output_path = outputs_dir / output_name
        output_path.write_text(final_script, encoding="utf-8")
        
        print(f"\n[SUCESSO] Roteiro gerado e salvo em: {output_path}")
        print("Lembre-se de revisar o roteiro e movê-lo para a pasta de processamento do programa desejado.")
        
        # Limpar inputs se o usuário quiser? (Opcional, melhor deixar manual para não perder dados)
    except Exception as e:
        print(f"\n[ERRO] Falha ao gerar roteiro: {e}")

if __name__ == "__main__":
    run_redator()
