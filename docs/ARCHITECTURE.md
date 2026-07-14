# Arquitetura Técnica — Rádio IA TJRN

> Documento técnico para desenvolvedores e agentes IA que operam no repositório.

---

## 📐 Visão Geral

O sistema segue uma arquitetura em **3 camadas**, organizada pelo padrão 5S:

```
┌─────────────────────────────────────────────────────────┐
│  CAMADA DE APRESENTAÇÃO                                 │
│  Dashboard.py • Voice Edit Agent (HTTP API)             │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  CAMADA DE ORQUESTRAÇÃO                                 │
│  PipelineEngine (core/engine.py)                        │
│  Agente IA (modules/agente/agente_ia.py)                │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  CAMADA DE EXECUÇÃO                                     │
│  Módulos de programa (boletins, jornal, giro, redação) │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  INFRAESTRUTURA                                         │
│  core/* (constantes, LLM factory, notificadores, cache)│
│  Google Drive (entrada/saída) • SQLite (cache local)    │
└─────────────────────────────────────────────────────────┘
```

---

## 🧩 Camada de Apresentação

### `Dashboard.py` (raiz)
Interface gráfica Tkinter para disparo manual de pipelines.

- Mostra status dos pipelines
- Permite disparar Boletins, Giro, NJUD, Redação com 1 clique
- Janela de log integrada

### Voice Edit Agent (`voice_agent/`)
Serviço HTTP (FastAPI) que implementa fluxo de **edição humana**:

```
Cliente → POST /voice/process → análise automática → awaiting_approval
                                                              ↓
                                                       Humano revisa
                                                              ↓
                              POST /voice/approve → montagem final em background
```

**Componentes internos:**

| Módulo | Responsabilidade |
|--------|------------------|
| `voice_agent/api.py` | Endpoints FastAPI |
| `voice_agent/runner.py` | Orquestrador de processamento (`process_file`, `approve_and_mount`) |
| `voice_agent/splitter.py` | Detecção de pausas e segmentação de áudio |
| `voice_agent/assembler.py` | Montagem final com vinhetas e BG |
| `voice_agent/audio_processor.py` | Limpeza/normalização de áudio |
| `voice_agent/error_detector.py` | Detecção de issues (claquetes, ruído, etc.) |
| `voice_agent/transcriber.py` | Transcrição para verificação textual |
| `voice_agent/report_generator.py` | Geração de relatórios de issues |
| `voice_agent/asset_manager.py` | Catálogo de vinhetas |
| `voice_agent/hooks.py` | Integração com o motor (`call_editor_edit_and_approve`) |
| `voice_agent/notifier.py` | Notificações do agente |
| `voice_agent/watcher.py` | Monitoramento de pastas |
| `voice_agent/program_config.py` | Config por programa |

---

## ⚙️ Camada de Orquestração

### `core/engine.py` — `PipelineEngine`

Motor unificado. Executa o ciclo de vida completo de um programa:

1. **Extração** — Download de pauta/planilha do Google Drive/Sheets
2. **Reescrita IA** — Limpa texto via `LLMFactory` (Groq → Gemini → OpenAI)
3. **TTS** — Aplica `aplicar_pronuncia` e sintetiza com `edge-tts`
4. **Mixagem** — Monta áudio final com `pydub` seguindo perfil JSON
5. **Distribuição** — Copia para pasta de publicação no Drive

**Parâmetros:**

```python
PipelineEngine(
    recipe: ProgramRecipe,    # dataclass com config do programa
    dry_run: bool = False,    # simula sem TTS nem upload
    workers: int = 5,         # paralelismo
)
```

**Métodos principais:**
- `validar_assets()` — falha cedo se vinhetas/trilhas faltam
- `run_pipeline()` — executa pipeline completo
- `assemble_audio()` — etapa de mixagem (ver DEMANDAS B3 sobre issue conhecido)

### `modules/agente/agente_ia.py` — Agente IA (daemon)

Loop contínuo que:
- Verifica planilha `data/BOLETINS_2026.xlsx` periodicamente
- Aciona pipeline de boletins para linhas novas
- Marca linhas processadas com `THI ✔`
- Envia notificações (push/WhatsApp) por evento
- Usa **lockfile anti-conflito** (`.agente.lock`) para evitar concorrência

---

## 🎬 Camada de Execução

### Módulos de programa

Cada módulo em `modules/` contém seu próprio pipeline e workspace local.

#### `modules/boletins/` — Notícias da Hora
| Arquivo | Função |
|---------|--------|
| `boletins_pipeline.py` | Pipeline principal (usa PipelineEngine) |
| `gerar_boletins_tts.py` | Versão legada standalone (mantida para compat) |
| `criar_boletim_do_dia.py` | Gera 1 boletim específico sob demanda |
| `sincronizar_boletins_drive.py` | Sincroniza outputs com Drive |
| `planilha_csv/{JAN-JUN}2026.csv` | Cache local das planilhas mensais |

**Como funciona:**
- Planilha `data/BOLETINS_2026.xlsx` controla roteiros
- Coluna `EDITOR = RAD` → ignora (manual)
- Coluna `LOCUTOR` é sobrescrita com voz usada (`LIV ✔`, `LEO ✔`, etc.)
- Fila de 4 vozes em rotação round-robin
- Webhook `BOLETINS_WEBAPP_URL` dispara sync pós-processamento

#### `modules/jornal/` — NJUD (Notícias do Judiciário)
| Arquivo | Função |
|---------|--------|
| `njud_pipeline.py` | Pipeline principal |
| `gerar_njud_tts.py` | Versão legada (NEVER redefine `MONTH_MAP` — importa de `core.constants`) |
| `processar_roteiro_completo.py` | Pipeline end-to-end alternativo |
| `agente_njud.py` | Agente específico para NJUD |
| `processar_com_gemini.py` | Reescrita via Gemini |
| `gerar_locucao_multi_speaker.py` | TTS multi-speaker (bancada virtual) |
| `gerar_locucao_completo.py` | Locução completa |

**Diferencial:** Suporta multi-speaker (2 vozes para diálogo de bancada).

#### `modules/giro/` — Giro nas Comarcas
| Arquivo | Função |
|---------|--------|
| `giro_pipeline.py` | Pipeline principal |
| `audit_giro_nas_comarcas.py` | Auditoria de execuções |
| `rewrite_giro_tts.py` | Reescrita jornalística |
| `generate_tts_giro.py` | Geração de TTS |
| `converter_giroscomarcas_seguro.py` | Conversão segura de arquivos |
| `clean_tts_by_audio.py` | Limpeza de áudio |

**Diferencial:** Locução premium (voz mais natural) e auditoria dedicada.

#### `modules/redacao/redator_ia.py`
Redator IA isolado (uso geral, sem pipeline específico).

#### `modules/migracao/` (legado)
Scripts de migração de dados antigos — manter em archive após migração.

---

## 🔧 Infraestrutura (`core/`)

### Constantes e Configuração

| Arquivo | Função |
|---------|--------|
| `core/constants.py` | Constantes de data/calendário (centralizadas) |
| `core/best_practices.py` | Helpers: `retry_async`, `aplicar_pronuncia`, `carregar_env_var` |
| `core/llm_factory.py` | Factory de LLMs com fallback automático |
| `core/models.py` | Dataclasses (`ProgramRecipe`, `VoiceStrategy`, `AssemblyRecipe`) |
| `core/voice_queue.py` | Fila de rotação de vozes neurais |
| `core/format_tts_roteiros.py` | Formatação de roteiros para TTS |

### Cache e Persistência

| Arquivo | Função |
|---------|--------|
| `core/db.py` | **SQLite de execuções** (`data/execucoes.db`) — observabilidade |
| `core/doc_cache.py` | Cache de Google Docs (TTL configurável) |
| `core/gdoc_exporter.py` | Exportador de Google Docs com cache |

**`core/db.py` (NOVO no merge 25/jun):**
```python
from core.db import inicializar_db, registrar_inicio, registrar_fim

exec_id = registrar_inicio("boletins_2026")
try:
    # ... executar pipeline ...
    registrar_fim(exec_id, "sucesso", duracao_audio_s=120.5)
except Exception as e:
    registrar_fim(exec_id, "erro", erro_msg=str(e))
```

Tabela `execucoes`:
- `id`, `ts_inicio`, `ts_fim`, `pipeline`, `status`
- `duracao_audio_s`, `erro_msg`

### Integração Google Drive

| Arquivo | Função |
|---------|--------|
| `core/drive_watcher.py` | **Watcher reativo (NOVO no merge 25/jun)** via `changes.list()` API |
| `core/gdoc_exporter.py` | Export de Google Docs para texto |
| `core/send_report.py` | Envio de relatórios por e-mail |
| `modules/boletins/sincronizar_boletins_drive.py` | Sync de outputs para Drive |

**`core/drive_watcher.py` (NOVO no merge 25/jun):**

Monitora pastas do Google Drive de forma reativa (vs polling burro).

```python
from core.drive_watcher import DriveWatcher

watcher = DriveWatcher(
    service=drive_service,                       # cliente googleapiclient
    watched_folders={
        "FOLDER_ID_NJUD":  on_new_njud,          # callback por pasta
        "FOLDER_ID_GIRO":  on_new_giro,
    },
    poll_s=120,                                  # verifica a cada 2min
    page_size=100,
)
watcher.run_forever()   # bloqueia
# ou
watcher.run_background()  # thread daemon
```

**Vantagem vs polling de arquivo:**
- Detecta mudanças em **tempo real** sem ler File Stream
- Usa `pageToken` da API — não perde mudanças
- Callbacks por pasta — modular

### Notificações

| Arquivo | Função |
|---------|--------|
| `core/notificador_push.py` | Push via Ntfy (pub/sub HTTP auto-hospedável) |
| `core/notificador_whatsapp.py` | WhatsApp via CallMeBot ou Evolution API |
| `core/notificador.py` (legacy/upgrade) | Alternativa em avaliação |

**Métodos padronizados:**
- `notificar_inicio(evento)`
- `notificar_sucesso(evento)`
- `notificar_erro(evento, erro)`
- `notificar_relatorio_diario(relatorio)`
- `notificar_drive_offline()`

---

## 📦 Modelo de Dados

### `ProgramRecipe` (dataclass)

Define como executar um programa:

```python
@dataclass
class ProgramRecipe:
    name: str                        # ex: "boletins"
    source: SourceConfig             # de onde vem a pauta
    llm: LLMConfig                   # qual LLM usar
    tts: TTSConfig                   # voz e parâmetros TTS
    assembly: AssemblyRecipe         # perfil de mixagem
    local_work_dir: Path             # workspace local
    drive_output_dir: str            # pasta de publicação
```

### Planilha de Boletins

`data/BOLETINS_2026.xlsx`:

| Coluna | Uso |
|--------|-----|
| `DATA` | Data do boletim |
| `TIPO` | Tipo (ABERTURA, NOTA, etc.) |
| `TEXTO` | Roteiro bruto |
| `LOCUTOR` | Voz usada (sobrescrito pelo sistema) |
| `EDITOR` | `RAD` = ignorar / `THI ✔` = processado por IA |
| `STATUS` | Status de processamento |

### SQLite — `data/execucoes.db`

Tabela única `execucoes` (ver `core/db.py`).

---

## 🔌 Integrações Externas

### Google Drive

**2 modos de operação:**

1. **File Stream local** (modo principal)
   - Drive montado em `H:\Meu Drive\...`
   - Paths no `.env` como `DRIVE_ROOT=H:/Meu Drive/...`
   - Simples e rápido

2. **API REST** (modo reativo, novo)
   - `core/drive_watcher.py` monitora mudanças via `changes.list()`
   - Dispara callbacks em tempo real
   - Útil para automação event-driven

### LLMs (fallback chain)

```python
LLMFactory()  # ordem de tentativa:
# 1. Groq (Llama 3.3) — rápido, gratuito
# 2. Gemini (Google) — bom custo-benefício
# 3. OpenAI (GPT-4o) — fallback pago
```

Configurável via `.env`:
- `GROQ_API_KEY`
- `GEMINI_API_KEY`
- `OPENAI_API_KEY`

### TTS (Edge Neural Voices)

- **Microsoft Edge-TTS** (`edge-tts` lib)
- Vozes customizadas: Francisca, Antonio (pt-BR)
- Fila rotativa definida em `core/voice_queue.py`
- Fonetização customizada em `data/pronunciation_rules.json`

---

## 🧪 Testes

```
tests/
├── test_system.py        # 5 testes: constantes, fila, fonetização
└── test_voice_agent.py   # 3 testes: voice agent
```

**Rodar:**
```bash
python -m pytest tests/ -x --tb=short -q
# Esperado: 8 passed
```

---

## 📁 Estrutura Completa de Diretórios

```
radio_ia/
├── .env                          # NÃO versionado (chaves + paths)
├── .env.example                  # template versionado
├── .gitignore
├── README.md                     # este arquivo (visão geral)
├── GEMINI.md                     # regras 5S para agentes IA
├── INSTRUCOES_IMPLANTACAO.md     # manual do editor humano
├── CHANGELOG.md                  # histórico de versões
├── DEMANDAS_PENDENTES.md         # bugs/dívidas/otimizações
├── melhorias.md                  # melhorias priorizadas
├── roadmap_upgrades_radio_ia.md  # roadmap 5S
├── VOICE_AGENT_STATUS.md         # status do voice agent
│
├── Dashboard.py                  # GUI de operação
├── Iniciar_Painel.bat            # atalho Windows
├── Iniciar_Agente_IA.bat         # atalho agente daemon
├── configurar_e_rodar.ps1        # setup automatizado
├── executar_agente_silencioso.bat
├── setup_env.py                  # cria venv + requirements
├── requirements.txt              # dependências (a criar se ausente)
├── check_whisper_claquetes.py
├── test_runner_real.py           # teste manual do runner
│
├── core/                         # motor central
├── modules/                      # programas
├── voice_agent/                  # serviço de edição humana
├── assets/
│   ├── vht/                      # vinhetas e trilhas
│   └── profiles/                 # perfis JSON de mixagem
├── data/                         # planilhas, cache, dicionários
├── docs/                         # documentação
├── tests/                        # testes automatizados
├── archive/                      # arquivo morto (legado)
└── upgrade/                      # alternativas em avaliação
```

---

## 🔗 Referências Cruzadas

- **Operação humana:** [`INSTRUCOES_IMPLANTACAO.md`](../INSTRUCOES_IMPLANTACAO.md)
- **Setup técnico:** [`docs/OPERATIONS.md`](OPERATIONS.md)
- **Regras 5S para agentes:** [`GEMINI.md`](../GEMINI.md)
- **Pendências:** [`DEMANDAS_PENDENTES.md`](../DEMANDAS_PENDENTES.md)
- **Roadmap:** [`roadmap_upgrades_radio_ia.md`](../roadmap_upgrades_radio_ia.md)
- **Sincronização git:** [`docs/SYNC_HISTORY.md`](SYNC_HISTORY.md)
