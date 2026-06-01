# Módulo: Giro nas Comarcas

Pipeline automatizado para o programa Giro nas Comarcas, integrando IA para reescrita e síntese de voz premium.

## 🚀 Pipeline Central
*   **`giro_pipeline.py`**: O orquestrador único. Ele:
    1.  Transforma pautas em roteiros (via LLM).
    2.  Aplica regras de radiojornalismo (extenso, siglas).
    3.  Gera o áudio premium (Edge-TTS).
    4.  Sincroniza com o Google Drive (`H:`).

## 🛠️ Ferramentas de Apoio
*   **`converter_giroscomarcas_seguro.py`**: Formata o texto bruto.
*   **`rewrite_giro_tts.py`**: Motor de reescrita via OpenAI/Groq/OpenRouter.
*   **`gerar_locucao_giro_premium.py`**: Motor de áudio e mixagem.

## 📂 Pastas
*   `tts_txt/`: Entrada de arquivos.
*   `tts_txt_revisado/`: Roteiros processados por IA.
*   `tts_mp3_premium/`: Saída local dos áudios.
