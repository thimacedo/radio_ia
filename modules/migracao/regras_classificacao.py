# -*- coding: utf-8 -*-
"""
Regras de classificação para identificar a quais programas da rádio pertencem os arquivos no G:.
"""

from typing import Tuple, Optional
import os

EXTENSOES_AUDIO = {".mp3", ".wav", ".m4a"}
EXTENSOES_ROTEIRO = {".docx", ".gdoc", ".txt", ".rtf"}

PROGRAMAS = {
    "GIRO": {
        "keywords": ["giro", "giros"],
        "pasta_producao": "02_PRODUCAO/GIRO",
        "pasta_roteiro": "01_ROTEIROS/GIRO"
    },
    "NJUD": {
        "keywords": ["njud", "jornal", "jornais"],
        "pasta_producao": "02_PRODUCAO/NJUD",
        "pasta_roteiro": "01_ROTEIROS/NJUD"
    },
    "BOLETIM": {
        "keywords": ["boletim", "boletins"],
        "pasta_producao": "02_PRODUCAO/BOLETINS",
        "pasta_roteiro": "01_ROTEIROS/BOLETINS"
    },
    "LEVEMENTE": {
        "keywords": ["levemente"],
        "pasta_producao": "02_PRODUCAO/LEVEMENTE",
        "pasta_roteiro": "01_ROTEIROS/LEVEMENTE"
    },
    "MEMORIA": {
        "keywords": ["memoria", "memória", "memória da justiça", "memoria da justica"],
        "pasta_producao": "02_PRODUCAO/MEMORIA",
        "pasta_roteiro": "01_ROTEIROS/MEMORIA"
    }
}

PASTAS_A_IGNORAR = [
    "Casamento", "TCC", "Documentos", "Sayo", "Google AI Studio", 
    "Gemini Gems", "Opal", "Casa", "ILUMINA FISIO", "ensaios", "NA"
]

def categorizar_pessoal(extensao: str) -> str:
    extensao = extensao.lower()
    if extensao in {".jpg", ".jpeg", ".png", ".gif", ".psd", ".ai", ".mp4", ".mov", ".avi"}:
        return "Imagens_e_Videos"
    elif extensao in {".pdf", ".docx", ".doc", ".txt", ".rtf", ".gdoc", ".xlsx", ".xls", ".gsheet", ".csv"}:
        return "Documentos_e_Planilhas"
    elif extensao in {".mp3", ".wav", ".m4a", ".ogg"}:
        return "Audios_Diversos"
    else:
        return "Outros"

def identificar_programa_e_destino(caminho_arquivo: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Analisa um arquivo e retorna:
    (is_radio, nome_programa, subcaminho_destino)
    """
    nome_arquivo = os.path.basename(caminho_arquivo).lower()
    caminho_lower = caminho_arquivo.lower()
    extensao = os.path.splitext(nome_arquivo)[1]

    # Verifica se deve ignorar baseado em pastas
    for pasta_ignore in PASTAS_A_IGNORAR:
        if f"\\{pasta_ignore.lower()}\\" in f"\\{caminho_lower}\\":
            # None significa que o arquivo não será movido nem listado para migração
            return False, None, None

    # Verifica palavras-chave na hierarquia do caminho e no nome do arquivo
    for programa, regras in PROGRAMAS.items():
        for keyword in regras["keywords"]:
            if keyword in caminho_lower:
                # É da rádio.
                if extensao in EXTENSOES_AUDIO:
                    return True, programa, regras["pasta_producao"]
                elif extensao in EXTENSOES_ROTEIRO:
                    return True, programa, regras["pasta_roteiro"]

    # Se não identificou mas tem um formato de roteiro/audio na raiz ou noutra pasta,
    # verificamos padrões de data ("14 01", "2026") que costumam ser da rádio
    import re
    if re.search(r'\d{2}\s\d{2}', caminho_lower) or re.search(r'2026', caminho_lower):
        # Pode ser da rádio mas não sabemos o programa exato
        if extensao in EXTENSOES_AUDIO:
            return True, "DESCONHECIDO", "02_PRODUCAO/DESCONHECIDOS"
        elif extensao in EXTENSOES_ROTEIRO:
            return True, "DESCONHECIDO", "01_ROTEIROS/DESCONHECIDOS"

    # Se chegou aqui, é um arquivo pessoal ou não classificado que deve ser organizado
    pasta_tema = categorizar_pessoal(extensao)
    caminho_pessoal = f"G:\\Meu Drive\\Arquivos_Pessoais_Para_Verificacao\\{pasta_tema}"
    
    return False, None, caminho_pessoal
