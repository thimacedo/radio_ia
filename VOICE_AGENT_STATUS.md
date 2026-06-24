# Voice Edit Agent Status

## O que foi implementado

- `voice_agent/api.py`
  - `POST /voice/process`
  - `POST /voice/approve`
  - `GET /voice/status/{job_id}`
  - `POST /voice/reject`
  - Job tracking em memória com `jobs` e `jobs_lock`
  - montagem final em background via thread (suportando multipart/cabeca + off)

- `voice_agent/runner.py`
  - pipeline completo de processamento de áudio humano:
    - conversão/normalização de áudio (mono, 44.1kHz s16 via ffmpeg)
    - transcrição via Whisper local com timestamp no nível de palavra
    - fatiamento automático inteligente (auto-splitter) de múltiplos boletins com base em claquetes (e.g. B1, B2)
    - detecção de issues de repetição, hesitação e retakes (erros com reinício de leitura indicados por marcadores como "repete", "novamente" ou por pausas >0.8s)
    - geração de relatório HTML multipart detalhado
  - suporte a `auto_approve=False`
  - retorno de `awaiting_approval` estruturado com `job_id`, `program`, `clean_path`, `report`, `issues`
  - função `approve_and_mount(...)` para montagem final de áudio único
  - função `approve_and_mount_multipart(...)` para montagem final com Cabeça + Transição + OFF/BG + Encerramento

- `voice_agent/watcher.py`
  - watcher de arquivos em `inputs/`
  - callback dispara `process_file(..., auto_approve=False)`

- `voice_agent/error_detector.py`
  - detecção robusta de erros de leitura de locutores e retakes baseada em N-gramas e pausas.
  - geração de sugestões de cortes precisas em milissegundos para as partes CABEÇA e OFF.
  - inserção da tag `part` (`cabeca` ou `off`) em cada issue identificada para facilitar a triagem.

- `voice_agent/splitter.py`
  - fatiamento automático de blocos de boletins utilizando claquetes sonoras (identificação das marcações B1, B2...).
  - tolerância fonética contra alucinações comuns do Whisper (ex: D2, V2).

- `voice_agent/asset_manager.py`
  - carregamento dinâmico de configurações (`configs/<program>.yaml`) e mapeamento inteligente de vinhetas/trilhas.

- `voice_agent/assembler.py`
  - montagem multipart flexível combinando Vinheta de Abertura, Cabeça limpa, Vinheta de Transição, OFF com trilha sonora de fundo em ducking (-18dB) e Vinheta de Encerramento.

- Configurações por Programa (`configs/`)
  - arquivos YAML criados para `boletins.yaml`, `njud.yaml` e `giro.yaml` mapeando as vinhetas reais localizadas em `assets/vht/`.

- UI e Painel de Controle (`Dashboard.py`)
  - interface interativa na aba "🟢 Aprovação de Áudio" para buscar o status do job e revisar os cortes sugeridos.
  - checkboxes dinâmicos para selecionar os trechos com falhas para remoção antes de autorizar a montagem final.
  - fallbacks manuais e registro de rejeições com motivos.

- Testes Unitários (`tests/test_voice_agent.py`)
  - testes cobrindo transcrição, processador de áudio, detetor de erros e fluxo de aprovação atualizados e passando (100% OK).

- Congelamento das Rotinas com Vozes de IA
  - todas as rotinas legadas de síntese de voz artificial (TTS) no `modules/agente/agente_ia.py` foram congeladas e não disparam mais vozes de IA, redirecionando o sistema para focar inteiramente na edição e processamento de locuções humanas reais.

- Documentação e configuração
  - `README.md` atualizado com seção do Voice Edit Agent
  - `.env.example` atualizado com `VOICE_AGENT_URL`
  - `requirements.txt` updated

## Status das Pendências

Todas as pendências e requisitos foram **integralmente sanados e validados**. O sistema está pronto para produção com locuções humanas.

## Execução recomendada

```bash
uvicorn voice_agent.api:app --host 0.0.0.0 --port 8002
python Dashboard.py
```
