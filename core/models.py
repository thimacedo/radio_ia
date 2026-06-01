from dataclasses import dataclass
from typing import Callable, Dict, List, Optional
import pathlib

@dataclass
class VoiceStrategy:
    """
    Define como as vozes serão distribuídas.
    type: 'intra_file' (alterna dentro do mesmo arquivo, ex: Jornal, Giro) 
          'inter_file' (alterna entre arquivos diferentes de um lote, ex: Boletins)
    voices: Lista de IDs das vozes neurais (ex: ['pt-BR-FranciscaNeural', 'pt-BR-AntonioNeural'])
    """
    type: str 
    voices: List[str]

@dataclass
class AssemblyRecipe:
    """
    Receita de edição e montagem de áudio.
    """
    intro_vht: Optional[pathlib.Path] = None
    outro_vht: Optional[pathlib.Path] = None
    transition_vht: Optional[pathlib.Path] = None
    bg_music: Optional[pathlib.Path] = None
    bg_volume_reduction_db: int = 15

@dataclass
class ProgramRecipe:
    """
    Definição completa de um programa de rádio para o pipeline unificado.
    """
    name: str
    drive_input_dir: pathlib.Path
    drive_output_dir: pathlib.Path
    local_work_dir: pathlib.Path
    system_prompt: str
    voice_strategy: VoiceStrategy
    assembly: AssemblyRecipe
    pre_process_hook: Optional[Callable[[str], str]] = None
    parse_hook: Optional[Callable[[str], list]] = None
