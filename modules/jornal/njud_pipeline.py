import os
import sys
import re
import asyncio
import pathlib

# Ajuste de path para importar do core
current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.append(str(project_root))

from core.models import ProgramRecipe, VoiceStrategy, AssemblyRecipe
from core.engine import PipelineEngine

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
NJUD_INPUT_DIR = pathlib.Path(r"H:\Meu Drive\RADIO TJRN CONTEÚDO\NOT JUDICIARIO (5 MIN)\NJUD 2026\Roteiros TXT Original")
NJUD_OUTPUT_DIR = pathlib.Path(r"H:\Meu Drive\RADIO TJRN CONTEÚDO\NOT JUDICIARIO (5 MIN)\NJUD 2026\Audio")
LOCAL_WORK_DIR = project_root / "modules" / "jornal" / "workspace"

VHT_DIR = project_root / "assets" / "vht" # Vinhetas do NJUD estão com as do boletim
# Assumindo que NJUD 1806 28-01.mp3 é um exemplo ou BG. 
# Para manter genérico, vamos mapear o BG do boletim ou deixar None e editar depois se necessário.

SYSTEM_PROMPT = """Você é um especialista em edição de roteiros de radiojornalismo. O objetivo é processar boletins informativos e entregá-los formatados para síntese de voz, aplicando diretrizes de redação.

REGRAS:
1. Sem formatação Markdown.
2. Identificar o cabeçalho no padrão: NJUD [NÚMERO] [DIA-MÊS].
3. Reter exclusivamente os blocos: Cabeça (Abertura), Escalada (Destaques) e Encerramento. Ignorar os textos integrais das reportagens (indicados como OFF ou NOTA).
4. Substituir as marcações originais de locutores por:
Speaker 1: [texto da fala]
Speaker 2: [texto da fala]
5. Na Escalada (leitura dos destaques), alternar as vozes sucessivamente, iniciando obrigatoriamente com o Speaker 1.
6. Remover nomes próprios de apresentadores, repórteres e locutores.
7. Escrever números, valores, porcentagens, datas e horas por extenso.
8. Escrever siglas letra por letra separadas por espaço (ex: t j r n).
9. Sites de forma literal (ex: t j r n ponto jus ponto b r).
10. Linguagem simples e direta.
"""

def njud_parse_hook(content: str) -> list:
    """Extrai as falas separadas por locutor, compatível com o formato gerado pelo LLM."""
    blocks = []
    
    # Extrai o cabeçalho se houver (para logging, ignoramos no áudio)
    
    for linha in content.splitlines():
        linha = linha.strip()
        if not linha:
            continue
            
        # Captura "Speaker 1:" ou "Speaker 2:" e remove colchetes de tags de expressão se houver
        match = re.match(r'^(Speaker\s*[12]):\s*(?:\[.*?\])?\s*(.*)$', linha, re.IGNORECASE)
        if match:
            speaker = match.group(1).lower().replace(" ", "")
            texto = match.group(2).strip()
            
            if texto:
                # O motor espera [("LOC", ("speakerX", texto))] se is_intra
                blocks.append(("LOC", (speaker, texto)))
                
    return blocks

# ---------------------------------------------------------------------------
# Receita do Programa
# ---------------------------------------------------------------------------
receita_njud = ProgramRecipe(
    name="Notícias do Judiciário (NJUD)",
    drive_input_dir=NJUD_INPUT_DIR,
    drive_output_dir=NJUD_OUTPUT_DIR,
    local_work_dir=LOCAL_WORK_DIR,
    system_prompt=SYSTEM_PROMPT,
    voice_strategy=VoiceStrategy(
        type='intra_file',
        voices=["pt-BR-FranciscaNeural", "pt-BR-AntonioNeural"]
    ),
    assembly=AssemblyRecipe(
        # Por enquanto sem vinhetas automáticas mapeadas para o NJUD, 
        # a edição antiga do NJUD multi_speaker apenas gerava o áudio.
        # Caso existam vinhetas, basta descomentar e apontar:
        # intro_vht=VHT_DIR / "ABERTURA.mp3",
        # outro_vht=VHT_DIR / "ENCERRAMENTO.mp3"
    ),
    parse_hook=njud_parse_hook
)

if __name__ == "__main__":
    motor = PipelineEngine(receita_njud)
    
    # O NJUD tem uma estrutura de pastas de meses no drive (ex: 3 - MARÇO, 4 - ABRIL)
    # Como o drive_input_dir é H:\...\Roteiros TXT Original, vamos iterar por lá
    async def run_njud():
        if not NJUD_INPUT_DIR.exists():
            print(f"[ERRO] Diretório de entrada não encontrado: {NJUD_INPUT_DIR}")
            return
            
        months = [d for d in NJUD_INPUT_DIR.iterdir() if d.is_dir()]
        for month_dir in months:
            month_name = month_dir.name
            files = [f for f in month_dir.glob("*.txt")]
            for idx, f in enumerate(files):
                # Copia para o txt_dir local para o motor processar
                local_f = motor.txt_dir / f.name
                if not local_f.exists():
                    local_f.write_text(f.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
                
                await motor.run_file(local_f, file_idx=idx, subfolder=month_name)
                
    asyncio.run(run_njud())
