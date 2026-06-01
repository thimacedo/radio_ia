# Core: Utilitários e Motor de Infraestrutura

Este módulo contém a infraestrutura central compartilhada por todos os programas da Rádio TJRN. A arquitetura foi refatorada para utilizar um **Pipeline Unificado**, onde os comportamentos específicos de cada programa são injetados via "Receitas" (`ProgramRecipe`).

## 🧠 Arquitetura do Pipeline (`engine.py` & `models.py`)

Todos os programas (Boletins, NJUD, Giro) compartilham o mesmo ciclo de vida de 5 etapas, implementado pela classe `PipelineEngine`:

1.  **Extração e Adaptação:** O motor recebe o roteiro ou pauta bruta do Drive e aplica *hooks* de pré-processamento específicos do programa (ex: transformar tópicos em roteiro estruturado).
2.  **Processamento IA (Reescrita):** O texto é enviado ao `LLMFactory`, que aplica o *System Prompt* (a receita de edição jornalística) específico do programa, garantindo regras de extenso, linguagem simples e siglas.
3.  **Gravação (TTS):** Síntese de voz neural via `edge-tts`. A estratégia de vozes (`VoiceStrategy`) define se a alternância de locutores ocorre **dentro do mesmo arquivo** (ex: Jornal NJUD, Giro) ou **entre arquivos diferentes** num lote (ex: Boletins Diários).
4.  **Edição e Montagem:** O `Pydub` monta o áudio final baseado na `AssemblyRecipe` do programa, inserindo vinhetas de abertura/passagem/encerramento e trilha sonora de fundo (`bg_music`).
5.  **Distribuição:** O arquivo MP3 final é exportado de volta para a pasta designada no Google Drive (`drive_output_dir`).

## 🛠️ Outros Componentes

*   **`llm_factory.py`**: Fábrica de modelos de linguagem (Groq, OpenRouter, OpenAI, Gemini) com lógica de fallback automático contra limites de cota.
*   **`send_report.py`**: Sistema de notificação por e-mail ao final dos processamentos.

## 🔑 Configuração
Todos os utilitários core dependem do arquivo `.env` na raiz do projeto.
