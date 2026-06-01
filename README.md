# Sistema de Automação de Rádio TJRN

Este repositório contém a suíte completa de ferramentas para automação de roteiros, síntese de voz (TTS) e mixagem de som para a Rádio Justiça Potiguar.

## 🚀 Principais Ferramentas

### 1. Giro nas Comarcas (Programa de 10 min)
Pipeline unificado que transforma pautas brutas em áudios mixados e sincronizados com o Google Drive.
*   **`giro_pipeline.py`**: O orquestrador central.
*   **`llm_factory.py`**: Motor de inteligência artificial com fallback automático entre múltiplos provedores (Groq, OpenRouter, OpenAI, Gemini).
*   **`gerar_locucao_giro_premium.py`**: Motor de locução com `edge-tts` (vozes neurais premium) e mixagem de vinhetas.

### 2. Boletins Diários (1 Minuto)
Processamento em lote a partir de planilhas de controle.
*   **`gerar_boletins_tts.py`**: Gera locuções rápidas com trilha e vinhetas.
*   **`sincronizar_boletins_drive.py`**: Organiza os boletins gerados no Drive.

### 3. Utilitários
*   **`send_report.py`**: Envia relatórios de execução por e-mail.
*   **`patch_vinhetas.py`**: Corrige vinhetas em arquivos MP3 existentes.

## ⚙️ Configuração (Arquivo .env)
Certifique-se de configurar as seguintes chaves no seu arquivo `.env`:
```env
# LLMs
OPENAI_API_KEY=...
GROQ_API_KEY=...
OPENROUTER_API_KEY=...
GEMINI_API_KEY=...

# Notificações
EMAIL_USER=...
EMAIL_PASS=...
```

## 📂 Fluxo de Trabalho do Giro
1. Coloque os roteiros ou pautas em `E:\NJUD\PROGRAMA GIRO NAS COMARCAS\tts_txt\`.
2. Execute `python giro_pipeline.py`.
3. Os áudios finais serão salvos localmente e copiados para `H:\Meu Drive\...\PROGRAMA GIRO NAS COMARCAS (10min)\`.
