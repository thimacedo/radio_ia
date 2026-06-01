import tkinter as tk
from tkinter import ttk
import os
import sys
import pathlib

# ---------------------------------------------------------------------------
# Funções de Execução
# ---------------------------------------------------------------------------
def run_script(script_relative_path, title):
    """
    Executa o script em uma nova janela de terminal para que o usuário 
    possa ver os logs de processamento em tempo real e interagir.
    """
    script_path = pathlib.Path(script_relative_path).resolve()
    
    if not script_path.exists():
        from tkinter import messagebox
        messagebox.showerror("Erro", f"Script não encontrado:\n{script_path}")
        return

    import subprocess
    python_exe = sys.executable
    
    # O uso de aspas externas extras é necessário no cmd.exe /c quando há caminhos com espaço
    cmd = f'cmd.exe /c ""{python_exe}" "{script_path}" & pause"'
    
    # CREATE_NEW_CONSOLE força o Windows a abrir uma nova janela preta 100% iterativa
    subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)

# ---------------------------------------------------------------------------
# Interface Gráfica (Dashboard)
# ---------------------------------------------------------------------------
def main():
    root = tk.Tk()
    root.title("Painel de Automação — Rádio TJRN")
    root.geometry("450x550")
    root.resizable(False, False)
    
    # Estilo
    style = ttk.Style()
    style.theme_use('clam') # Tema mais limpo e moderno nativo do Tkinter
    
    style.configure('TButton', font=('Segoe UI', 11), padding=10)
    style.configure('TLabel', font=('Segoe UI', 10))
    style.configure('Header.TLabel', font=('Segoe UI', 16, 'bold'))
    style.configure('SubHeader.TLabel', font=('Segoe UI', 10, 'italic'), foreground="#555555")

    # Frame Principal
    main_frame = ttk.Frame(root, padding="20 20 20 20")
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Cabeçalho
    lbl_title = ttk.Label(main_frame, text="Rádio Justiça Potiguar", style='Header.TLabel', anchor="center")
    lbl_title.pack(fill=tk.X, pady=(0, 5))
    
    lbl_subtitle = ttk.Label(main_frame, text="Painel Central de Automação (IA & TTS)", style='SubHeader.TLabel', anchor="center")
    lbl_subtitle.pack(fill=tk.X, pady=(0, 20))

    # Botões dos Módulos
    btn_frame = ttk.LabelFrame(main_frame, text=" Módulos de Produção ", padding="15 15 15 15")
    btn_frame.pack(fill=tk.BOTH, expand=True, pady=10)

    # 1. Boletins
    btn_boletins = ttk.Button(
        btn_frame, 
        text="🎙️ Notícias da Hora (Boletins)", 
        command=lambda: run_script("modules/boletins/gerar_boletins_tts.py", "Noticias da Hora")
    )
    btn_boletins.pack(fill=tk.X, pady=5)

    # 2. NJUD
    btn_njud = ttk.Button(
        btn_frame, 
        text="📰 Notícias do Judiciário (NJUD)", 
        command=lambda: run_script("modules/jornal/njud_pipeline.py", "NJUD")
    )
    btn_njud.pack(fill=tk.X, pady=5)

    # 3. Giro
    btn_giro = ttk.Button(
        btn_frame, 
        text="🗺️ Giro nas Comarcas", 
        command=lambda: run_script("modules/giro/giro_pipeline.py", "Giro nas Comarcas")
    )
    btn_giro.pack(fill=tk.X, pady=5)

    ttk.Separator(btn_frame, orient='horizontal').pack(fill=tk.X, pady=15)

    # 4. Redação
    btn_redacao = ttk.Button(
        btn_frame, 
        text="✍️ Redação IA (Escrever Roteiros)", 
        command=lambda: run_script("modules/redacao/redator_ia.py", "Redacao IA")
    )
    btn_redacao.pack(fill=tk.X, pady=5)

    # 5. Relatório
    btn_report = ttk.Button(
        btn_frame, 
        text="📧 Enviar Relatório Diário", 
        command=lambda: run_script("core/send_report.py", "Relatorio")
    )
    btn_report.pack(fill=tk.X, pady=5)

    # Rodapé
    footer_frame = ttk.Frame(main_frame)
    footer_frame.pack(fill=tk.X, pady=(20, 0))
    
    lbl_footer = ttk.Label(footer_frame, text="TJRN © 2026 - v2.0 Modular", font=('Segoe UI', 8), foreground="#888888", anchor="center")
    lbl_footer.pack(fill=tk.X)

    # Loop da Janela
    root.mainloop()

if __name__ == "__main__":
    main()
