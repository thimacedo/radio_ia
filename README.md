# Sistema de Automação de Rádio TJRN

Este repositório foi reestruturado em módulos para facilitar a manutenção e expansão das ferramentas de rádio da Rádio Justiça Potiguar.

## 🗂️ Estrutura Modular

O sistema está dividido em 3 grandes domínios:

1.  **[Notícias da Hora](./modules/boletins/)**: Boletins que trazem as últimas notícias do Poder Judiciário.
2.  **[Notícias do Judiciário (NJUD)](./modules/jornal/)**: Jornal diário que traz os destaques entre as últimas notícias do Poder Judiciário.
3.  **[Giro nas Comarcas](./modules/giro/)**: Um giro pelas comarcas de todo o Rio Grande do Norte para acompanhar as novidades, mudanças, eventos e fatos relevantes da Justiça Potiguar. Programa semanal.

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
