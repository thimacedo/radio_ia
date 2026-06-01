# Módulo: Boletins Diários

Este módulo é responsável pelo processamento dos boletins curtos (aprox. 1 minuto) a partir de planilhas Excel.

## 🛠️ Scripts

*   **`gerar_boletins_tts.py`**: Lê a planilha `BOLETINS_2026_ATUALIZADO.xlsx`, gera o áudio TTS (Edge-TTS), adiciona trilha de fundo e mixa a abertura/encerramento.
*   **`criar_boletim_do_dia.py`**: Utilitário para criar uma estrutura de diretório para o dia atual.
*   **`sincronizar_boletins_drive.py`**: Sincroniza os arquivos gerados com a pasta correspondente no Google Drive.

## 📂 Dados de Entrada
*   Planilha Excel em `E:\NJUD\boletins\planilha_csv` (ou diretório configurado).
*   Vinhetas em `E:\NJUD\boletins\VHT`.
