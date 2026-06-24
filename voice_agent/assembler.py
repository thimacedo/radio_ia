"""Assembler: aplica cortes aprovados, mistura assets e exporta o arquivo final.

API principal:
- assemble(program_config, clean_wav_path, cuts, output_path) -> output_path
"""

from typing import List, Dict
from pathlib import Path


def assemble(program_config: Dict, clean_wav_path: str, cuts: List[Dict], output_path: str) -> str:
    """Monte arquivo final a partir do clean wav e regras do programa.

    cuts: lista de {start_ms, end_ms}
    program_config: dict carregado do YAML do programa (assets, montagem)
    """
    # TODO: usar pydub para aplicar cortes, carregar assets e mixar
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    # Por enquanto, apenas copia o clean_wav para saída com novo nome
    from shutil import copyfile
    copyfile(clean_wav_path, output_path)
    return output_path


if __name__ == "__main__":
    print("Assembler stub")
