# Core: Utilitários de Infraestrutura

Componentes compartilhados por todos os módulos do sistema.

## 🛠️ Componentes

*   **`llm_factory.py`**: Fábrica de modelos de linguagem. Suporta Groq, OpenRouter, OpenAI e Gemini com lógica de fallback automático. Garante resiliência contra limites de cota.
*   **`send_report.py`**: Utilitário de notificação que envia relatórios de execução por e-mail (thi.macedo@gmail.com).

## 🔑 Configuração
Todos os utilitários core dependem do arquivo `.env` na raiz do projeto.
