# Módulo: Jornal NJUD (Notícias do Judiciário)

Este módulo processa o programa semanal NJUD, utilizando múltiplas vozes neurais para simular uma bancada de jornalismo.

## 🛠️ Scripts

*   **`gerar_locucao_multi_speaker.py`**: Script principal que gera locuções alternadas entre Speaker 1 (Feminino) e Speaker 2 (Masculino).
*   **`processar_com_gemini.py`**: Envia o roteiro bruto para o Google Gemini para formatação técnica.
*   **`processar_roteiro_completo.py`**: Processador local (regex) para conversão de texto para locução.
*   **`agente_njud.py`**: Assistente de orquestração para o jornal.

## 🎙️ Padrão de Vozes
*   **Francisca (Premium)**: Speaker 1
*   **Antonio (Premium)**: Speaker 2
