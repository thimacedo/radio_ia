# Operação e Deploy — Rádio IA TJRN

> Guia prático para colocar o sistema em produção e operá-lo diariamente.

---

## 🛠️ Setup Inicial (nova máquina)

### Pré-requisitos

| Dependência | Versão mínima | Como instalar |
|-------------|---------------|---------------|
| Python | 3.10+ | [python.org](https://python.org) — marcar "Add to PATH" |
| FFmpeg | qualquer recente | [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) — adicionar `bin\` ao PATH |
| Google Drive for Desktop | atual | [google.com/drive/download](https://www.google.com/drive/download/) |
| Git | 2.30+ | [git-scm.com](https://git-scm.com) |

### Instalação passo a passo

```powershell
# 1. Clone o repositório
git clone https://github.com/thimacedo/radio_ia.git
cd radio_ia

# 2. Crie o ambiente virtual
python -m venv .venv

# 3. Ative o ambiente
.\.venv\Scripts\Activate.ps1

# 4. Instale as dependências
pip install -r requirements.txt
# Se requirements.txt não existir:
pip install edge-tts pydub openpyxl google-api-python-client google-auth python-dotenv fastapi uvicorn pytest

# 5. Configure o .env
Copy-Item .env.example .env
notepad .env  # editar com suas chaves e paths
```

### Configurar `.env` (essencial)

Edite `.env` e preencha:

```ini
# === CHAVES DE API (obrigatórias para os 3 serviços) ===
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...
GROQ_API_KEY=gsk_...

# === CAMINHOS DO GOOGLE DRIVE (ajustar para sua máquina) ===
DRIVE_ROOT=H:/Meu Drive/RADIO TJRN CONTEÚDO
DRIVE_PRODUCAO=H:/Meu Drive/RADIO TJRN CONTEÚDO/00_PRODUCAO_2026
DRIVE_GIRO_VHT_DIR=H:/Meu Drive/RADIO TJRN CONTEÚDO/PROGRAMAS/PROGRAMA GIRO NAS COMARCAS (10min)/_VHT
DRIVE_NJUD_INPUT_DIR=H:/Meu Drive/RADIO TJRN CONTEÚDO/00_PRODUCAO_2026/02_JORNAIS_NJUD/01_ROTEIROS
DRIVE_NJUD_OUTPUT_DIR=H:/Meu Drive/RADIO TJRN CONTEÚDO/00_PRODUCAO_2026/02_JORNAIS_NJUD/03_AUDIOS_RADIO

# === DRIVE WATCHER (NOVO 25/jun/2026) ===
# Obter IDs via: drive_service.files().get(fileId="ID", fields="id,name").execute()
NJUD_ROTEIROS_FOLDER_ID=
GIRO_ROTEIROS_FOLDER_ID=

# === CACHE DE DOCUMENTOS ===
DOC_CACHE_TTL_S=3600

# === CREDENCIAIS GOOGLE ===
CREDENTIALS_PATH=config/credentials/service_account.json

# === VOICE AGENT ===
VOICE_AGENT_URL=http://127.0.0.1:8002

# === NOTIFICAÇÕES ===
NTFY_TOPIC=radio_tjrn
EMAIL_RECIPIENT=seu_email@gmail.com

# === BOLETINS ===
BOLETINS_WEBAPP_URL=https://script.google.com/macros/s/AKfycbzYXmsNOoHKykBL8qiFCMu2bJKaWwn-qnWHkyu6lSVOb94rOSHUsB0yTyKQw2ptm8FikA/exec
```

### Validar instalação

```powershell
# Ativar venv
.\.venv\Scripts\Activate.ps1

# Rodar testes (deve passar 8)
python -m pytest tests/ -x --tb=short -q

# Verificar import dos módulos principais
python -c "import core.engine, core.db, core.drive_watcher; print('OK')"
```

---

## 🎬 Operação Diária

### Cenário 1: Gravar boletins do dia

**Método A — Dashboard (recomendado):**
1. Duplo clique em `Iniciar_Painel.bat`
2. Clicar em **"Boletins"**
3. Acompanhar log na janela que abre

**Método B — Linha de comando:**
```powershell
.\.venv\Scripts\Activate.ps1
python modules/boletins/boletins_pipeline.py
```

### Cenário 2: Gravar NJUD

```powershell
python modules/jornal/njud_pipeline.py
```

### Cenário 3: Gravar Giro nas Comarcas

```powershell
python modules/giro/giro_pipeline.py
```

### Cenário 4: Rodar agente IA em modo daemon

**Método A — Manual:**
```powershell
python modules/agente/agente_ia.py
```

**Método B — Serviço em background (24/7):**
- Duplo clique em `Iniciar_Agente_IA.bat`
- Ou `executar_agente_silencioso.bat` (sem janela)

**Método C — Windows Task Scheduler (recomendado para produção):**
1. Criar tarefa "Agente Rádio IA"
2. Trigger: na inicialização do sistema
3. Action: `python.exe modules/agente/agente_ia.py`
4. Working dir: pasta do projeto
5. Run whether user is logged on or not

### Cenário 5: Voice Edit Agent (aprovação humana)

```powershell
# Terminal 1: subir serviço
uvicorn voice_agent.api:app --host 0.0.0.0 --port 8002

# Terminal 2: usar via curl ou cliente HTTP
curl -X POST http://127.0.0.1:8002/voice/process \
  -H "Content-Type: application/json" \
  -d '{"program":"boletins","input_path":"caminho.wav","auto_approve":false}'
```

---

## 🧪 Testes

```powershell
# Suite completa
python -m pytest tests/ -x --tb=short -q

# Apenas um arquivo
python -m pytest tests/test_voice_agent.py -v

# Com cobertura (se coverage instalado)
python -m pytest tests/ --cov=core --cov=modules --cov=voice_agent
```

**Saída esperada:** `8 passed`

---

## 🔍 Troubleshooting

### ❌ `ModuleNotFoundError: No module named 'edge_tts'`

```powershell
# venv não está ativado
.\.venv\Scripts\Activate.ps1
pip install edge-tts
```

### ❌ `FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'`

```powershell
# FFmpeg não está no PATH
# Adicionar C:\ffmpeg\bin ao PATH do Windows
# Reiniciar terminal
ffmpeg -version  # deve listar versão
```

### ❌ `KeyError: 'OPENAI_API_KEY'`

`.env` não foi carregado. Verificar:
1. Arquivo `.env` existe na raiz
2. Não tem espaços: `KEY=value` (não `KEY = value`)
3. Está sendo carregado via `python-dotenv` ou `load_dotenv()`

### ❌ `sqlite3.OperationalError: no such table: execucoes`

Banco não foi inicializado. Solução:
```python
from core.db import inicializar_db
inicializar_db()
```

### ❌ `AttributeError: module 'datetime' has no attribute 'utcnow'`

Você está em Python 3.12+. O fix foi aplicado em 25/jun (`bde3ac3`). Atualize:
```powershell
git pull origin resolucao-codespaces
```

### ❌ Boletim não aparece no Google Sheets após gravação

Verificar:
1. `BOLETINS_WEBAPP_URL` está correto no `.env`
2. Apps Script está implantado como Web App
3. Permissão do Web App está como "Anyone" ou conta de serviço

### ❌ Áudio sai sem voz / só BG

- Verificar vinhetas em `assets/vht/` (não podem estar vazias)
- Verificar perfil JSON em `assets/profiles/` aponta para vinhetas corretas
- Rodar `python core/engine.py` para ver validação de assets falhar cedo

### ❌ `Lock file .agente.lock existe` (agente não roda)

Outra instância do agente está rodando, ou travou:
```powershell
# Verificar processos
tasklist /FI "IMAGENAME eq python.exe"

# Se travado, deletar lock manualmente (cuidado!)
del .agente.lock
```

### ❌ Merge/rebase do git dá conflito

Sempre faça merge com a estratégia `-X ours` para preservar seu trabalho local:
```powershell
git fetch origin
git merge -X ours origin/minhas-alteracoes --no-commit --no-ff
# Resolver conflitos manualmente se houver
git add .
git commit -m "merge: integrar remoto preservando local"
```

---

## 📊 Monitoramento

### Logs em tempo real (modo daemon)

```powershell
# PowerShell
Get-Content logs/agente.log -Wait  # se existir

# Ou via Dashboard (Tkinter mostra log em janela)
```

### Banco de execuções

```python
# Ver últimas execuções
import sqlite3
conn = sqlite3.connect("data/execucoes.db")
for row in conn.execute(
    "SELECT * FROM execucoes ORDER BY ts_inicio DESC LIMIT 20"
):
    print(row)
```

### Notificações

- **Ntfy (push):** subscrever o tópico `radio_tjrn` no app Ntfy
- **WhatsApp:** número configurado no `core/notificador_whatsapp.py`

---

## 🚀 Deploy em Produção

### Opção 1: Windows Service (recomendado)

**Criar serviço NSSM:**

```powershell
# Baixar NSSM (https://nssm.cc)
nssm install "Radio IA Agente" "C:\...\radio_ia\.venv\Scripts\python.exe" "modules/agente/agente_ia.py"
nssm set "Radio IA Agente" AppDirectory "C:\...\radio_ia"
nssm set "Radio IA Agente" DisplayName "Rádio IA - Agente de Boletins"
nssm set "Radio IA Agente" Start SERVICE_AUTO_START

# Iniciar
nssm start "Radio IA Agente"
```

### Opção 2: Task Scheduler

Ver **Cenário 4 — Método C** acima.

### Opção 3: Container Docker (em avaliação)

Ver `upgrade/docker-compose-ntfy.yml` e `upgrade/docker-compose-evolution.yml`.

⚠️ Não recomendado para produção ainda — configuração complexa e divergente do setup atual.

---

## 🔐 Segurança Operacional

### ⚠️ Rotação de chaves (pós-merge 25/jun/2026)

**Status:** Chaves antigas (OpenAI, Gemini, Groq) ficaram expostas no histórico do git.
**Risco:** Qualquer pessoa com acesso ao repo público pode ter visto as chaves.

**Ação imediata:**

1. **Rotacionar as 3 chaves:**
   - [OpenAI](https://platform.openai.com/api-keys) → criar nova, deletar antiga
   - [Google AI Studio](https://aistudio.google.com/app/apikey) → criar nova, revogar antiga
   - [Groq Console](https://console.groq.com/keys) → criar nova, revogar antiga

2. **Atualizar `.env` local** com as novas chaves

3. **Atualizar `.env` em qualquer deploy** (servidor, container, etc.)

4. **Verificar uso indevido:**
   - OpenAI: Usage → ver últimas 24h
   - Gemini: AI Studio → Usage
   - Groq: Console → Usage

### Arquivos sensíveis — checklist

- [x] `.env` removido do tracking (commit `e021bbf`)
- [x] `.gitignore` contém `.env`, `config/credentials/`
- [ ] Chaves antigas rotacionadas (pendente)
- [ ] `.env` em deploys atualizado
- [ ] Credenciais do Google Service Account (`config/credentials/*.json`) — verificar se estão fora do repo

---

## 📋 Checklist de Manutenção

### Diário
- [ ] Verificar log do agente (erros?)
- [ ] Conferir boletins do dia no Drive
- [ ] Validar notificações (Ntfy/WhatsApp chegando)

### Semanal
- [ ] Limpar áudios temporários em `modules/*/workspace/`
- [ ] Conferir tamanho de `data/execucoes.db` (se > 100MB, arquivar)
- [ ] Revisar `DEMANDAS_PENDENTES.md` (algum bug crítico novo?)

### Mensal
- [ ] Atualizar `data/pronunciation_rules.json` (siglas novas, nomes)
- [ ] Renovar `requirements.txt` se houve mudança de deps
- [ ] Validar vinhetas (`assets/vht/`) — alguma corrompida?
- [ ] Rodar `pytest` suite completa

### Trimestral
- [ ] Rotação preventiva de chaves de API
- [ ] Revisar `roadmap_upgrades_radio_ia.md` (itens fechados?)
- [ ] Backup da pasta `data/` (planilhas + dicionários)

---

## 📞 Contatos e referências

- **Repositório:** [github.com/thimacedo/radio_ia](https://github.com/thimacedo/radio_ia)
- **Manual do editor:** [`../INSTRUCOES_IMPLANTACAO.md`](../INSTRUCOES_IMPLANTACAO.md)
- **Pendências:** [`../DEMANDAS_PENDENTES.md`](../DEMANDAS_PENDENTES.md)
- **Arquitetura técnica:** [`ARCHITECTURE.md`](ARCHITECTURE.md)
- **Histórico git:** [`SYNC_HISTORY.md`](SYNC_HISTORY.md)
