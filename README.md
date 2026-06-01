# Sistema de Automação de Rádio TJRN

Este repositório foi reestruturado em módulos para facilitar a manutenção e expansão das ferramentas de rádio da Rádio Justiça Potiguar.

## 🗂️ Estrutura Modular

O sistema está dividido em 3 grandes domínios:

1.  **[Boletins](./modules/boletins/)**: Processamento de notícias rápidas (1 min) via Excel.
2.  **[Jornal NJUD](./modules/jornal/)**: Programa semanal com bancada multi-speaker.
3.  **[Giro nas Comarcas](./modules/giro/)**: Noticiário das comarcas com integração total de IA.

---

## 🚀 Como Iniciar

Para facilitar a operação diária, utilize o menu central:

```powershell
python Main.py
```

Este menu permite disparar os pipelines de cada módulo, enviar relatórios e monitorar o status.

---

## 🛠️ Tecnologias Utilizadas

*   **IA (LLMs)**: Llama 3.3 (Groq), Gemini 2.0 (Google), GPT-4o (OpenAI).
*   **TTS**: Microsoft Edge Neural Voices (Vozes premium: Francisca e Antonio).
*   **Áudio**: Pydub para mixagem e sound design.
*   **Infra**: Sincronização automática com Google Drive via File Stream.

---

## ⚙️ Configuração (Arquivo .env)

Certifique-se de que todas as chaves estão configuradas na raiz do projeto. O sistema possui fallback automático: se o Groq falhar, ele tentará o OpenRouter, e assim por diante.

---

*Desenvolvido para o Tribunal de Justiça do Rio Grande do Norte — 2026*
