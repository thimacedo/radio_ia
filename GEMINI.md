# Regras de Organização do Projeto (Padrão 5S)

1. **Raiz Limpa**: Manter na raiz apenas o .env, .gitignore, README.md e os arquivos iniciadores do Dashboard.
2. **Arquitetura**: O motor fica em core/, os assets em assets/vht/, o arquivo morto em archive/ e as lógicas de programas em modules/.
3. **Arquivos Temporários**: Testes devem ser feitos em scratch dentro do archive/ e deletados quando não mais úteis.
4. **Workspaces Locais**: Cada módulo (ex: modules/giro) deve ter sua pasta workspace/ para converter os textos e áudios, sem espalhar lixo pelo projeto.
5. **Preservação de Arquivos (Regra Inegociável)**: O agente está proibido de excluir qualquer arquivo ou diretório que ele mesmo não tenha criado. Roteiros (.gdoc, .docx, .txt) e áudios (.mp3, .wav) originais são documentos de comprovação contratual e devem ser integralmente respeitados e preservados no workspace e no Google Drive.

---

## Módulos Centrais (`core/`)

| Arquivo              | Responsabilidade                              |
|----------------------|-----------------------------------------------|
| `constants.py`       | Constantes de data/calendário (MONTH_MAP, etc.) — **usar em vez de definir localmente** |
| `best_practices.py`  | Helpers reutilizáveis (`retry_async`, `aplicar_pronuncia`, `carregar_env_var`) |
| `engine.py`          | Motor unificado de pipeline de áudio          |
| `models.py`          | Dataclasses (ProgramRecipe, VoiceStrategy, AssemblyRecipe) |
| `llm_factory.py`     | Factory de LLMs com fallback automático       |

**Regra:** Nunca definir `MONTH_MAP`, `WEEKDAYS_PT` ou `ANO_PRODUCAO` dentro de módulos individuais. Importar de `core.constants`.
