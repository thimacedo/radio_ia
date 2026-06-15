# Sistema de Automação de Rádio TJRN

Este repositório foi organizado usando a metodologia 5S para facilitar a manutenção e expansão das ferramentas de rádio da Justiça Potiguar.

## 🗂️ Arquitetura do Projeto (Padrão 5S)

*   **`core/`**: Motor central de processamento (`engine.py`, `llm_factory.py`, conectores). Lógica compartilhada entre todos os programas.
*   **`modules/`**: Domínios específicos de cada programa. Cada módulo possui seus próprios scripts e uma pasta local `workspace/` para processamento de arquivos.
*   **`assets/vht/`**: Repositório central padronizado para todas as vinhetas e trilhas (BG) utilizadas nas montagens de áudio.
*   **`archive/`**: Arquivo morto seguro para scripts legados, testes antigos e histórico de anos anteriores (ex: 2025).

### 🎙️ Módulos de Programas

1.  **[Notícias da Hora](./modules/boletins/)**: Boletins informativos em formato curto.
2.  **[Notícias do Judiciário (NJUD)](./modules/jornal/)**: Jornal diário com bancada virtual simulada.
3.  **[Giro nas Comarcas](./modules/giro/)**: Programa semanal com novidades das comarcas potiguares.

---

## 🚀 Como Iniciar

Para facilitar a operação diária, o sistema conta com uma Interface Gráfica (Dashboard). 

Basta dar um duplo clique no arquivo:
**`Iniciar_Painel.bat`**

Ou, via terminal:
```powershell
python Dashboard.py
```

O painel permite disparar os pipelines de cada módulo (Giro, Boletins, NJUD, Redação) com um clique. Uma janela de terminal segura será aberta para exibir o progresso do processamento escolhido.

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
