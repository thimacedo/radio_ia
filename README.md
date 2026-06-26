# 📻 Rádio IA — Tribunal de Justiça do Rio Grande do Norte

Sistema de automação de produção de áudio para os programas da Rádio TJRN. Gera boletins informativos, o jornal NJUD (Notícias do Judiciário) e o Giro nas Comarcas a partir de IA (LLMs) e síntese de voz neural (Edge-TTS).

> **Estado atual:** Sincronizado e validado em **25/jun/2026** (commit `e021bbf`)
> **Branch:** `resolucao-codespaces`
> **Versão:** 2.2 (pós-merge `origin/minhas-alteracoes`)

---

## 🎯 O que o sistema faz

| Programa | Tipo | Descrição |
|----------|------|-----------|
| **Notícias da Hora** (Boletins) | Curtos | Boletins informativos em formato curto, gerados a partir de planilha |
| **Notícias do Judiciário** (NJUD) | Longo | Jornal diário com bancada virtual simulada (multi-speaker) |
| **Giro nas Comarcas** | Longo | Programa semanal com novidades das comarcas potiguares |

**Pipeline unificado:** Extração (Drive) → Reescrita IA → TTS Neural → Mixagem → Distribuição

---

## 🚀 Início Rápido

### Pré-requisitos
- **Python 3.10+** (testado em 3.12)
- **FFmpeg** no PATH (para `pydub`)
- **Google Drive for Desktop** instalado e montado (ex: `H:\Meu Drive\...`)
- **Acesso ao Google Drive da rádio** com permissão de leitura/escrita

### Setup (1ª vez)
```bash
# 1. Clone e configure
git clone https://github.com/thimacedo/radio_ia.git
cd radio_ia

# 2. Crie o ambiente virtual
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows PowerShell
# ou
source .venv/bin/activate   # Linux/Mac

# 3. Instale as dependências
pip install -r requirements.txt
# (ou: python setup_env.py para setup automatizado)

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com suas chaves de API e caminhos do Drive
```

### Execução

**Opção A — Dashboard (recomendado para edição diária):**
```bash
# Duplo clique em: Iniciar_Painel.bat
# ou
python Dashboard.py
```

**Opção B — Linha de comando:**
```bash
python modules/boletins/boletins_pipeline.py    # Boletins
python modules/giro/giro_pipeline.py            # Giro nas Comarcas
python modules/jornal/njud_pipeline.py          # NJUD
python modules/agente/agente_ia.py              # Agente IA (modo daemon)
```

**Opção C — Voice Edit Agent (serviço HTTP):**
```bash
uvicorn voice_agent.api:app --host 0.0.0.0 --port 8002
```

### Testes
```bash
python -m pytest tests/ -x --tb=short -q
# Saída esperada: 8 passed
```

---

## 📚 Documentação

| Documento | Conteúdo |
|-----------|----------|
| **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)** | Arquitetura técnica: módulos, pipeline, integrações, modelo de dados |
| **[`docs/OPERATIONS.md`](docs/OPERATIONS.md)** | Operação: setup detalhado, deploy, .env, troubleshooting |
| **[`docs/SYNC_HISTORY.md`](docs/SYNC_HISTORY.md)** | Histórico de sincronização git (auditoria) |
| **[`docs/INSTRUCOES_MIGRACAO.md`](docs/INSTRUCOES_MIGRACAO.md)** | Guia de migração para nova máquina |
| **[`docs/gemini-code.md`](docs/gemini-code.md)** | Skill do Gemini AI Studio para edição de roteiros |
| **[`GEMINI.md`](GEMINI.md)** | Regras de organização (5S) para agentes IA |
| **[`INSTRUCOES_IMPLANTACAO.md`](INSTRUCOES_IMPLANTACAO.md)** | Manual de operação (editor humano) |
| **[`CHANGELOG.md`](CHANGELOG.md)** | Histórico de mudanças por versão |
| **[`DEMANDAS_PENDENTES.md`](DEMANDAS_PENDENTES.md)** | Bugs, dívidas técnicas e otimizações pendentes |
| **[`melhorias.md`](melhorias.md)** | Lista priorizada de melhorias |
| **[`roadmap_upgrades_radio_ia.md`](roadmap_upgrades_radio_ia.md)** | Roadmap de upgrades (5S, O1-O10) |
| **[`VOICE_AGENT_STATUS.md`](VOICE_AGENT_STATUS.md)** | Status do Voice Edit Agent |

---

## 🏗️ Arquitetura (visão geral)

```
radio_ia/
├── core/              # Motor central (PipelineEngine, LLMFactory, constantes)
├── modules/           # Pipelines de cada programa
│   ├── boletins/      # Notícias da Hora
│   ├── jornal/        # NJUD
│   ├── giro/          # Giro nas Comarcas
│   ├── agente/        # Agente IA (modo daemon)
│   └── redacao/       # Redator IA
├── voice_agent/       # Voice Edit Agent (serviço HTTP + edição humana)
├── assets/
│   ├── vht/           # Vinhetas e trilhas
│   └── profiles/      # Perfis de mixagem (JSON)
├── data/              # Planilhas, dicionários de pronúncia, SQLite cache
├── archive/           # Arquivo morto (scripts legados)
├── upgrade/           # Alternativas em avaliação (docker-compose)
├── docs/              # Documentação
├── tests/             # Testes automatizados (pytest)
└── Dashboard.py       # Interface gráfica de operação
```

Para detalhes de cada módulo, veja [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## 🛠️ Tecnologias

| Camada | Tecnologia |
|--------|------------|
| **IA (LLMs)** | Llama 3.3 (Groq), Gemini 2.0 (Google), GPT-4o (OpenAI) — fallback automático |
| **TTS** | Microsoft Edge Neural Voices (Francisca, Antonio, e vozes customizadas) |
| **Áudio** | `pydub` para mixagem, `edge-tts` para síntese |
| **Storage** | Google Drive (File Stream local + API para mudanças) |
| **Cache** | SQLite local (data/execucoes.db, data/doc_cache.db) |
| **HTTP** | FastAPI + uvicorn (voice_agent) |
| **Notificações** | Ntfy (push) + WhatsApp (CallMeBot / Evolution API) |

---

## 🔒 Segurança

⚠️ **IMPORTANTE:** O arquivo `.env` contém chaves de API reais (OpenAI, Gemini, Groq) e credenciais do Google. Ele **NÃO está versionado** desde 25/jun/2026 (commit `e021bbf`).

**⚠️ Ação recomendada após a sincronização de 25/jun:**
As chaves que estavam no histórico do git antes desse commit precisam ser **rotacionadas**:
1. Gere novas chaves em: OpenAI, Google AI Studio, Groq
2. Atualize o `.env` local
3. Atualize o `.env` em qualquer deploy
4. Verifique os 3 serviços por uso indevido

Veja [`docs/SYNC_HISTORY.md`](docs/SYNC_HISTORY.md#segurança) para detalhes.

---

## 🟢 Voice Edit Agent (recurso destaque)

Serviço HTTP que detecta problemas na locução limpa (`clean.wav`) e aguarda aprovação humana antes da montagem final.

**Endpoints:**
- `POST /voice/process` — processa arquivo, retorna `awaiting_approval` se houver issues
- `POST /voice/approve` — inicia montagem final em background
- `POST /voice/reject` — rejeita com motivo
- `GET /voice/status/{job_id}` — consulta status do job

**Execução:**
```bash
uvicorn voice_agent.api:app --host 0.0.0.0 --port 8002
```

Configurar `VOICE_AGENT_URL=http://127.0.0.1:8002` no `.env`.

---

## 📊 Status do projeto

- ✅ **Pipeline unificado** (`PipelineEngine` em `core/engine.py`)
- ✅ **Fila de 4 vozes neurais** com rotação automática
- ✅ **Fonetização** configurável via `data/pronunciation_rules.json`
- ✅ **Sincronização com Google Drive** via File Stream + API
- ✅ **Notificações push/WhatsApp** (Ntfy + CallMeBot)
- ✅ **Voice Edit Agent** com aprovação humana
- ✅ **Cache de documentos Google** (SQLite)
- ✅ **Testes automatizados** (8 passing)

**Pendências conhecidas:** ver [`DEMANDAS_PENDENTES.md`](DEMANDAS_PENDENTES.md)

---

## 📜 Licença e crédito

*Desenvolvido para o Tribunal de Justiça do Rio Grande do Norte — 2026*

Repositório: [github.com/thimacedo/radio_ia](https://github.com/thimacedo/radio_ia)
