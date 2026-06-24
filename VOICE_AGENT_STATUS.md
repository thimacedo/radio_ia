# Voice Edit Agent Status

## O que foi implementado

- `voice_agent/api.py`
  - `POST /voice/process`
  - `POST /voice/approve`
  - `GET /voice/status/{job_id}`
  - `POST /voice/reject`
  - Job tracking em memória com `jobs` e `jobs_lock`
  - montagem final em background via thread

- `voice_agent/runner.py`
  - pipeline básico de processamento de áudio:
    - conversão/normalização de áudio
    - transcrição via Whisper local ou fallback
    - detecção de issues de repetição/hésitação
    - geração de relatório HTML
  - suporte a `auto_approve=False`
  - retorno de `awaiting_approval` com `job_id`, `program`, `clean_path`, `report`, `issues`
  - função `approve_and_mount(...)` para gerar MP3 final após aprovação

- `voice_agent/watcher.py`
  - watcher de arquivos em `inputs/`
  - callback padrão dispara `process_file(..., auto_approve=False)`

- `tests/test_voice_agent.py`
  - testes unitários em `unittest`
  - casuística de aprovação pendente

- Documentação e configuração
  - `README.md` atualizado com seção do Voice Edit Agent
  - `.env.example` atualizado com `VOICE_AGENT_URL`
  - `requirements.txt` atualizado com `streamlit` e `python-dotenv`

- `voice_agent/assembler.py`
  - fallback de importação `pydub` para permitir execução/testes em ambientes sem a dependência instalada

## O que falta completar

- **Gerenciamento de assets e manifests**
  - implementar `voice_agent/asset_manager.py` de forma completa
  - definir `configs/<program>.yaml` com assets e regras de montagem por programa
  - popular `assets/` com vinhetas e trilhas reais

- **Montagem de áudio por programa**
  - criar receitas específicas para NJUD, Giro e Boletins
  - tornar `voice_agent/assembler.py` capaz de usar `montagem.estrutura` variada

- **Integração com pipelines existentes**
  - conectar `core/engine.py` e `core/runner.py` ao fluxo de aprovação de voz
  - permitir que `modules/*` produzam `arquivo_clean` e relatório para revisão

- **UI e fluxo de aprovação final**
  - testar a integração do `Dashboard.py` com `VOICE_AGENT_URL`
  - implementar seleção de cortes aprovados na interface
  - garantir a revisão humana do relatório antes da montagem final

- **Cortes e edição automática**
  - gerar sugestões de cortes a partir de `issues`
  - armazenar `cuts` aprovados no job e usar na montagem final

- **Testes de integração e API**
  - adicionar testes de endpoint FastAPI
  - cobrir watcher e fluxo completo de `voice/process` -> `voice/approve`
  - validar com áudio real de locutor

- **Documentação adicional**
  - criar instruções de uso e exemplos de payloads na raiz do projeto
  - documentar processos de implantação e execução da API

## Execução atual recomendada

```bash
uvicorn voice_agent.api:app --host 0.0.0.0 --port 8002
python Dashboard.py
```

## Observações

- O pipeline atual já compila e os testes unitários de base passaram.
- O sistema ainda está em estado de protótipo, com muitas partes de configuração e montagem específicas faltando.
