# Módulo: Redação IA

Este módulo é responsável por **escrever** roteiros do zero, a partir de notícias externas brutas (matérias de sites, notas de assessorias) utilizando modelos de Inteligência Artificial.

## 🗂️ Estrutura

*   `templates/`: Contém os "modelos" ou "receitas de bolo" para a IA saber o formato de cada programa (Boletim, NJUD, Giro).
*   `inputs/`: Onde você deve colocar os arquivos `.txt` com as notícias originais brutas que servirão de base para a redação.
*   `outputs/`: Onde os roteiros prontos serão salvos.
*   `redator_ia.py`: O script que executa a magia.

## 🚀 Como Funciona

1. O redator pega **todo o conteúdo** da pasta `inputs/`.
2. Junta esse material e envia para a IA junto com o **template** do programa escolhido.
3. A IA retorna o roteiro estruturado (com divisões de voz e marcações) pronto para ser enviado para a pasta de processamento do respectivo programa.
