# Registro de Demandas Pendentes — Rádio IA TJRN
**Data de Consolidação:** 25 de Junho de 2026
**Status Geral:** 6 Bugs Críticos + 13 Dívidas Técnicas + 5 Otimizações de Impacto Alto + 1 Demanda Crítica de Segurança Pendentes
**Prioridade:** 🔴 CRÍTICA (Bugs + Segurança) → 🟡 ALTA (Refactor) → 🟢 MÉDIA (Otimizações)

---

## 🚨 NOVA DEMANDA CRÍTICA DE SEGURANÇA (25/jun/2026)

### S1 — Rotação das API Keys Expostas no Histórico Git
**Severidade:** 🔴 CRÍTICA — Credenciais reais podem ter sido expostas
**Data:** 25/jun/2026
**Origem:** Achado durante merge de sincronização (ver `docs/SYNC_HISTORY.md`)

**Problema:**
O arquivo `.env` estava **tracked no git** desde o commit `ee308c7` (data antiga), contendo 3 chaves de API reais:
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `GROQ_API_KEY`

Em 25/jun/2026, foi aplicado `git rm --cached .env` (commit `e021bbf`), removendo o arquivo do tracking. **PORÉM**, as chaves permanecem acessíveis no histórico de commits antigos — qualquer pessoa com acesso ao repositório público pode vê-las.

**Ação necessária (manual, fora do escopo de automação):**

1. **Rotacionar as 3 chaves:**
   - OpenAI: https://platform.openai.com/api-keys → criar nova, revogar antiga
   - Google AI Studio: https://aistudio.google.com/app/apikey → criar nova, revogar antiga
   - Groq: https://console.groq.com/keys → criar nova, revogar antiga

2. **Atualizar `.env` local** com as novas chaves (preservado em `E:\RÁDIO_IA\.env`)

3. **Atualizar `.env` em qualquer deploy** (servidor, container, etc.)

4. **Verificar uso indevido** nos 3 serviços:
   - OpenAI: Usage → últimas 24h
   - Gemini: AI Studio → Usage
   - Groq: Console → Usage

5. **(Opcional, recomendado)** Reescrever histórico:
   ```bash
   pip install git-filter-repo
   git filter-repo --invert-paths --path .env
   git push origin --force --all
   ```
   ⚠️ Invalida clones existentes — comunicar à equipe antes.

**Status:** ⏳ PENDENTE

---

---

## 📋 RESUMO EXECUTIVO

O sistema está **produção-viável com locuções humanas**, mas **frágil em casos de regressão técnica**. As demandas listadas abaixo devem ser resolvidas em ordem de criticidade para evitar:
- ❌ Crashes silenciosos em runtime
- ❌ Duplicação de código que dificulta manutenção
- ❌ Caminhos hardcoded que quebram em outro servidor
- ❌ Falta de observabilidade para diagnóstico de problemas em produção

---

## 🔴 BUGS CRÍTICOS (Precisam de Correção Imediata)

### B1 — `boletins_pipeline.py` linha 31: Typo em `load_workbook`
**Severidade:** 🔴 CRÍTICA — Causa `AttributeError` em tempo de execução  
**Arquivo:** `modules/boletins/gerar_boletins_tts.py` (ou `boletins_pipeline.py` dependendo da versão)  
**Problema:**
```python
# ERRADO
wb = openpyxl.load_load_workbook(local_xlsx, data_only=True)
```
**Solução:**
```python
# CORRETO
wb = openpyxl.load_workbook(local_xlsx, data_only=True)
```
**Impacto:** Qualquer execução do pipeline de boletins falha com `AttributeError: module 'openpyxl' has no attribute 'load_load_workbook'`  
**Status:** ⏳ PENDENTE

---

### B2 — `gerar_locucao_giro_premium.py` linha 127: Variável `VOICE` Não Definida
**Severidade:** 🔴 CRÍTICA — Causa `NameError` em tempo de execução  
**Arquivo:** `modules/giro/gerar_locucao_giro_premium.py`  
**Problema:**
```python
# ERRADO
print(f"Voz: {VOICE}\n")  # VOICE não foi definida em nenhum lugar
```
**Solução:**
```python
# CORRETO — referenciar as vozes configuradas
print(f"Vozes: {VOZ_SPEAKER_1} / {VOZ_SPEAKER_2}\n")
# ou
print(f"Vozes: {VOICES_INTRA_FILE}\n")
```
**Impacto:** O script falha no `main()` ao tentar imprimir informações de voz  
**Status:** ⏳ PENDENTE

---

### B3 — `engine.py` método `assemble_audio`: Avanço Incorreto da "Agulha" da Trilha
**Severidade:** 🔴 CRÍTICA — Causa áudio de fundo (BG) fora de sincronia  
**Arquivo:** `core/engine.py` (procurar método `assemble_audio`)  
**Problema:**
```python
# ERRADO — após zerar speech_timeline, usa o tamanho zerado para avançar bg_audio
speech_timeline = AudioSegment.empty()
bg_audio = bg_audio[len(speech_timeline):]  # len() == 0 aqui, não avança nada
# Resultado: trilha de fundo recomeça a cada fala
```
**Solução:**
```python
# CORRETO — salvar o tamanho ANTES de zerar
consumed = len(speech_timeline)
speech_timeline = AudioSegment.empty()
bg_audio = bg_audio[consumed:]
```
**Impacto:** A trilha sonora de fundo não avança sincronamente com a fala; você ouve a mesma trilha do início repetida ou cortada abruptamente  
**Status:** ⏳ PENDENTE

---

### B4 — `agente_ia.py` linha 511: Referência Errada a `datetime.date`
**Severidade:** 🔴 CRÍTICA — Causa `TypeError` ao validar data de roteiro  
**Arquivo:** `modules/agente/agente_ia.py`  
**Problema:**
```python
# ERRADO — datetime é a classe importada do módulo, não o módulo
if isinstance(refer_val, (datetime, datetime.date)):
    # TypeError: isinstance() arg 2 must be a type or tuple of types
```
**Solução Opção 1:**
```python
# Garantir que ambos são tipos, não módulos
import datetime as dt
if isinstance(refer_val, (dt.datetime, dt.date)):
```
**Solução Opção 2:**
```python
from datetime import datetime, date
if isinstance(refer_val, (datetime, date)):
```
**Impacto:** Qualquer tentativa de validar uma data de roteiro causa crash com `TypeError`  
**Status:** ⏳ PENDENTE

---

### B5 — `giro_pipeline.py`: Indentação Incorreta de `VoiceStrategy`
**Severidade:** 🔴 CRÍTICA — Causa `SyntaxError` ou definição incorreta de receita  
**Arquivo:** `modules/giro/giro_pipeline.py` (procurar definição de `receita_giro`)  
**Problema:**
```python
# ERRADO — VoiceStrategy fora do ProgramRecipe
receita_giro = ProgramRecipe(
    name="Giro nas Comarcas",
    ...
)
voice_strategy=VoiceStrategy(  # ← MAU ALINHAMENTO
    type='intra_file',
    voices=[...]
)
```
**Solução:**
```python
# CORRETO
receita_giro = ProgramRecipe(
    name="Giro nas Comarcas",
    ...
    voice_strategy=VoiceStrategy(
        type='intra_file',
        voices=[...]
    ),
)
```
**Impacto:** Python não consegue fazer o parse ou a estratégia de voz não é atribuída à receita  
**Status:** ⏳ PENDENTE

---

### B6 — `gerar_njud_tts.py`: `import shutil` Dentro de Loop
**Severidade:** 🟡 ALTA — Impacto de performance; não causa crash  
**Arquivo:** `modules/jornal/gerar_njud_tts.py`  
**Problema:**
```python
# ERRADO — import dentro de um loop (ex: for mes in meses)
for mes in range(1, 7):
    import shutil  # ← Executado 6 vezes desnecessariamente
    shutil.copytree(...)
```
**Solução:**
```python
# CORRETO — mover import para o topo do arquivo
import shutil

for mes in range(1, 7):
    shutil.copytree(...)
```
**Impacto:** Pequena perda de performance (lookup de módulo repetido); não quebra funcionalidade  
**Status:** ⏳ PENDENTE

---

## 🟡 DÍVIDAS TÉCNICAS (Refactor de Médio Prazo)

### D1 — `MONTH_MAP` Duplicado em 5 Arquivos
**Severidade:** 🟡 ALTA — Dificulta manutenção; risco de inconsistência  
**Localização:** `agente_ia.py`, `gerar_njud_tts.py`, `sincronizar_boletins_drive.py`, `giro_pipeline.py`, `boletins_pipeline.py`  
**Problema:**
```python
# ERRADO — mesmo mapa definido em múltiplos arquivos
MONTH_MAP_SHORT = {1: "JAN", 2: "FEV", ..., 12: "DEZ"}
MONTH_MAP_FULL = {1: "1 - JANEIRO", 2: "2 - FEVEREIRO", ..., 12: "12 - DEZEMBRO"}
```
**Solução:** Centralizar em `core/constants.py` (✅ JÁ REALIZADO no CHANGELOG.md v2.1)  
**Ação:** Atualizar todos os 5 arquivos para fazer `from core.constants import MONTH_MAP_SHORT, MONTH_MAP_FULL`  
**Benefício:** Mudança de padrão de nomenclatura passa a ser 1-lugar  
**Status:** ⏳ PENDENTE (Implementação parcial no CHANGELOG; falta aplicação nos 5 arquivos)

---

### D2 — `extrair_linhas_fala` e `lines_to_falas` São Idênticas
**Severidade:** 🟡 ALTA — Duplicação de 10 linhas  
**Arquivo:** `modules/jornal/gerar_njud_tts.py`  
**Problema:**
```python
# ERRADO — duas funções que fazem a mesma coisa
def extrair_linhas_fala(texto_revisado):
    return lines_to_falas(texto_revisado.splitlines())

def lines_to_falas(linhas):
    ...  # implementação real
```
**Solução:** Remover `extrair_linhas_fala`, usar apenas `lines_to_falas` em todos os call-sites  
**Esforço:** 15 minutos  
**Status:** ⏳ PENDENTE

---

### D3 — Caminhos Hardcoded Espalhados em 5 Arquivos
**Severidade:** 🟡 ALTA — Quebra em outro servidor; dificulta deployment  
**Localizações:** `agente_ia.py`, `gerar_njud_tts.py`, `boletins_pipeline.py`, `sincronizar_boletins_drive.py`, `giro_pipeline.py`  
**Exemplo:**
```python
# ERRADO
VHT_DIR = Path(r"H:\Meu Drive\RADIO TJRN CONTEÚDO\PROGRAMAS\PROGRAMA GIRO NAS COMARCAS (10min)\_VHT")
```
**Solução:** Usar `.env` + `carregar_env_var()`
```ini
# .env
DRIVE_ROOT=H:/Meu Drive/RADIO TJRN CONTEÚDO
DRIVE_GIRO_VHT_DIR=${DRIVE_ROOT}/PROGRAMAS/PROGRAMA GIRO NAS COMARCAS (10min)/_VHT
```
```python
from core.best_practices import carregar_env_var
VHT_DIR = Path(carregar_env_var("DRIVE_GIRO_VHT_DIR"))
```
**Impacto:** Qualquer mudança de servidor exige editar apenas `.env`, não 5 arquivos  
**Status:** ⏳ PENDENTE

---

### D4 — `obter_caminho_mes_njud` Usa If/Elif Cascata Frágil
**Severidade:** 🟡 ALTA — Difícil de manter; propensa a erros de typo  
**Arquivo:** `modules/jornal/gerar_njud_tts.py`  
**Problema:**
```python
# ERRADO — 8 condições encadeadas
def obter_caminho_mes(refer_val):
    if not refer_val: return "6 - JUNHO"
    refer_str = str(refer_val).upper()
    if "JUNHO" in refer_str: return "6 - JUNHO"
    elif "MAIO" in refer_str: return "5 - MAIO"
    elif "ABRIL" in refer_str: return "4 - ABRIL"
    ... (5 mais)
```
**Solução:** Substituir pela tabela lookup `MONTH_MAP_FULL` do `core/constants.py`  
```python
def obter_caminho_mes(refer_val):
    if not refer_val:
        return MONTH_MAP_FULL.get(6, "6 - JUNHO")
    mes_num = extrair_mes_num_de_caminho(str(refer_val))  # usar função do core
    return MONTH_MAP_FULL.get(mes_num, MONTH_MAP_FULL[6])
```
**Benefício:** Reduz de 8 condições para 2-3 linhas; fácil de atualizar  
**Status:** ⏳ PENDENTE

---

### D5 — `executar_pipelines()` em `agente_ia.py`: Subprocess Triplicado
**Severidade:** 🟡 MÉDIA — Duplicação de 12 linhas × 3 = 36 linhas  
**Arquivo:** `modules/agente/agente_ia.py` (procurar função `executar_pipelines()`)  
**Problema:**
```python
# ERRADO — 3 blocos quase idênticos para boletins, njud, giro
res = subprocess.run(
    [sys.executable, "modules/boletins/gerar_boletins_tts.py"],
    capture_output=True, text=True, encoding='utf-8', errors='ignore'
)
print(f"----- Boletins Output -----\n{res.stdout}")
if res.stderr: print(f"----- Boletins Errors -----\n{res.stderr}")
...
# (repetir 2× mais para njud e giro)
```
**Solução:** Extrair para helper genérico
```python
def _run_pipeline(nome: str, script_path: str) -> bool:
    res = subprocess.run(
        [sys.executable, script_path],
        capture_output=True, text=True, encoding='utf-8', errors='ignore'
    )
    print(f"----- {nome} Output -----\n{res.stdout}")
    if res.stderr:
        print(f"----- {nome} Errors -----\n{res.stderr}")
    ok = res.returncode == 0
    registrar_log_5s(f"Pipeline {nome} {'concluído' if ok else 'falhou'}.")
    return ok

def executar_pipelines():
    ok_boletins = _run_pipeline("Boletins", "modules/boletins/gerar_boletins_tts.py")
    ok_njud = _run_pipeline("NJUD", "modules/jornal/njud_pipeline.py")
    ok_giro = _run_pipeline("Giro", "modules/giro/giro_pipeline.py")
    return ok_boletins and ok_njud and ok_giro
```
**Benefício:** Reduz 36 linhas para 15; correções se aplicam em 1 lugar  
**Status:** ⏳ PENDENTE

---

### D6 — `NJUD_ROTEIROS_FOLDER_ID` e `SPREADSHEET_ID_*` Hardcoded
**Severidade:** 🟡 ALTA — Quebra ao trocar de Google Workspace  
**Localização:** Múltiplos arquivos (`agente_ia.py`, `gerar_njud_tts.py`, etc.)  
**Solução:** Adicionar ao `.env`:
```ini
NJUD_ROTEIROS_FOLDER_ID=1UHYp4SCterbUJF27MHj3bOh6ju1OBzIG
SPREADSHEET_ID_BOLETINS=1b1xnzvA00H1JC9uTvd6c-PBwQjEzGRs6t_raXG_ztsU
SPREADSHEET_ID_NJUD=1HegL-SudxPLI4Y6wsj1nnJocXHOvi-6inGqQld1lYec
SPREADSHEET_ID_GIRO=1Xbftz33ZEE4oc66ppgI5Sjy0T99WTUrN9gCJ85ZLDSo
```
**Esforço:** 30 minutos para identificar todos os call-sites  
**Status:** ⏳ PENDENTE

---

### D7 — Credenciais `service_account.json` em `archive/`
**Severidade:** 🟡 ALTA — Risco de commit acidental da chave privada  
**Arquivo:** `archive/gen-lang-client-...json`  
**Solução:** Mover para `config/credentials/service_account.json` e adicionar ao `.gitignore`
```gitignore
config/credentials/
*.json.key
```
**Referência em código:** `config/credentials/service_account.json` (padrão)  
**Status:** ⏳ PENDENTE

---

### D8 — Falta de Validação de Assets na Inicialização
**Severidade:** 🟡 ALTA — Falhas silenciosas em vinhetas faltantes  
**Impacto:** Se uma vinheta de encerramento (`encerramento.wav`) é deletada do Drive, o script falha silenciosamente no final da montagem sem mensagem clara  
**Solução:** Adicionar validação no `engine.py` ou `agente_ia.py` no início:
```python
def validar_assets():
    required = [
        Path(carregar_env_var("VHT_ABERTURA")),
        Path(carregar_env_var("VHT_TRANSICAO")),
        Path(carregar_env_var("VHT_ENCERRAMENTO")),
    ]
    for asset_path in required:
        if not asset_path.exists():
            raise FileNotFoundError(f"Asset crítico faltando: {asset_path}")
    print("✅ Todos os assets validados.")
```
**Status:** ⏳ PENDENTE

---

### D9 — Sem Histórico Consultável de Execuções
**Severidade:** 🟡 ALTA — Impossível debugar problemas passados  
**Impacto:** Único rastro é `agente_ia.log` (texto) + `agente_status.json` (sobrescrito a cada run)  
**Solução Parcial:** Usar `core/db.py` (já proposto no roadmap) para registrar em SQLite:
```python
CREATE TABLE execucoes (
    id INTEGER PRIMARY KEY,
    ts_inicio REAL, ts_fim REAL,
    pipeline TEXT,  -- 'boletins' | 'njud' | 'giro'
    status TEXT,    -- 'ok' | 'erro' | 'skip'
    duracao_audio_s REAL,
    erro_msg TEXT
);
```
**Benefício:** Dashboard em `Dashboard.py` pode exibir histórico + taxa de sucesso  
**Status:** ⏳ PENDENTE (Proposto; não implementado)

---

### D10 — Sem Lockfile para Execuções Simultâneas
**Severidade:** 🟡 ALTA — Risco de corrupção de `temp_boletins_agente.xlsx`  
**Cenário:** Se ciclo diário demorar >24h, agendador tenta rodar novamente enquanto a primeira execução ainda está em progresso  
**Solução:** Adicionar lockfile em `agente_ia.py`:
```python
import atexit, os

LOCK_FILE = pathlib.Path(current_dir) / ".agente.lock"

def adquirir_lock() -> bool:
    if LOCK_FILE.exists():
        pid = LOCK_FILE.read_text().strip()
        try:
            os.kill(int(pid), 0)  # Verificar se processo existe
            print(f"[LOCK] Agente já em execução (PID {pid}). Abortando.")
            return False
        except (ProcessLookupError, ValueError):
            pass  # Processo morreu, sobrescrever lock
    LOCK_FILE.write_text(str(os.getpid()))
    atexit.register(lambda: LOCK_FILE.unlink(missing_ok=True))
    return True

# No início de run_agent_once():
if not adquirir_lock():
    sys.exit(1)
```
**Status:** ⏳ PENDENTE

---

### D11 — Relatório de Produção Não Enviado
**Severidade:** 🟡 MÉDIA — Função existe mas não é chamada  
**Arquivo:** `core/send_report.py` (existe mas não é invocado em `agente_ia.py`)  
**Solução:** Adicionar ao final de `run_agent_once()`:
```python
from core.send_report import send_report

relatorio = {
    "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
    "boletins": {"status": "OK" if ok_boletins else "FALHOU", "count": n_boletins},
    "njud": {"status": "OK" if ok_njud else "FALHOU", "count": n_njud},
    "giro": {"status": "OK" if ok_giro else "FALHOU", "count": n_giro},
    "duracao_total_s": round(time.time() - ts_inicio),
}
send_report(relatorio)  # Envia via email/Telegram
```
**Pré-requisito:** Configurar no `.env`: `TELEGRAM_BOT_TOKEN=...` e `TELEGRAM_CHAT_ID=...`  
**Status:** ⏳ PENDENTE

---

### D12 — Sem Modo `--dry-run` nos Pipelines
**Severidade:** 🟡 MÉDIA — Impossível testar sem gerar áudio real  
**Solução:** Adicionar flag em todos os pipelines:
```python
parser.add_argument("--dry-run", action="store_true",
    help="Simula execução sem gravar áudio nem fazer upload.")
```
No engine, quando `dry_run=True`:
- ❌ Não chama `edge_tts` (não gasta cota)
- ❌ Não copia para Drive
- ✅ Imprime roteiro processado
**Benefício:** Permite validar refactors sem risco  
**Status:** ⏳ PENDENTE

---

### D13 — Sem Opção `--workers N` para Paralelismo
**Severidade:** 🟡 MÉDIA — Boletins rodam sequencial (lento)  
**Solução:** Adicionar pool de workers ao `voice_queue.py`:
```python
parser.add_argument("--workers", type=int, default=1,
    help="Número de workers paralelos para TTS.")

# No pipeline:
queue = VoiceQueue(max_workers=args.workers)
```
**Benefício:** 4 boletins em paralelo = ~4× mais rápido  
**Status:** ⏳ PENDENTE

---

## 🟢 OTIMIZAÇÕES DE IMPACTO ALTO (Nice-to-Have, Médio Prazo)

### O1 — Spider/Watcher Reativo no Drive
**Impacto:** Reduzir latência de detecção de novo roteiro de 24h para ~2 min  
**Ideia:** Implementar `core/drive_watcher.py` que faz polling em `NJUD_ROTEIROS_FOLDER_ID` a cada 2 minutos  
**Complexidade:** Média (3-4h)  
**Referência:** Ver seção "O1" em `melhorias.md`  
**Status:** ⏳ PENDENTE

---

### O2 — Cache Local de Documentos (Evitar Downloads Repetidos)
**Impacto:** Reduzir tempo de load de roteiros já processados em 50%  
**Ideia:** SQLite em `data/doc_cache.db` com hash MD5 do doc  
**Complexidade:** Média (3-4h)  
**Referência:** Ver seção "O2" em `melhorias.md`  
**Status:** ⏳ PENDENTE

---

### O3 — Migração Completa do NJUD para `PipelineEngine`
**Impacto:** Reduzir `gerar_njud_tts.py` de 796 para ~80 linhas  
**Ideia:** Usar `section_order` em `AssemblyRecipe` para definir sequência de seções  
**Complexidade:** Alta (6-8h) — é o maior refactor da Fase 1  
**Referência:** Ver seção "U1.4" em `roadmap_upgrades_radio_ia.md`  
**Status:** ⏳ PENDENTE

---

### O4 — Banco de Dados de Observabilidade
**Impacto:** Permitir diagnosticar padrões de falha (ex: NJUD falha toda segunda às 08h)  
**Ideia:** Implementar `core/db.py` com tabela `execucoes` conforme proposto em `melhorias.md` seção "U2.1"  
**Complexidade:** Média (3h)  
**Status:** ⏳ PENDENTE

---

### O5 — Aposentar `gerar_locucao_giro_premium.py`
**Impacto:** Eliminar ambiguidade sobre qual pipeline usar para o Giro  
**Ideia:** Verificar se arquivo ainda é invocado; se não, mover para `archive/`  
**Complexidade:** Baixa (30 min)  
**Status:** ⏳ PENDENTE

---

## 📅 CRONOGRAMA SUGERIDO

### Semana 1 (CRÍTICA — Bugs)
- ✅ B1: Corrigir typo `load_load_workbook` → `load_workbook`
- ✅ B2: Corrigir referência a `VOICE` indefinida
- ✅ B3: Corrigir avanço de trilha de fundo em `engine.py`
- ✅ B4: Corrigir referência a `datetime.date` em `agente_ia.py`
- ✅ B5: Corrigir indentação de `VoiceStrategy` em `giro_pipeline.py`
- ✅ B6: Mover `import shutil` para topo de arquivo

**Tempo Estimado:** 1-2 horas  
**Valor:** Sistema deixa de crashar em casos recorrentes

---

### Semana 2 (ALTA — Refactor Fundação)
- ✅ D1: Centralizar `MONTH_MAP*` em `core/constants.py` (JÁ FEITO; falta aplicar em 5 arquivos)
- ✅ D2: Remover `extrair_linhas_fala` duplicada
- ✅ D3: Migrar caminhos hardcoded para `.env`
- ✅ D4: Substituir if/elif por lookup table em `obter_caminho_mes`
- ✅ D6: Mover `SPREADSHEET_ID_*` e `FOLDER_ID` para `.env`
- ✅ D7: Mover credenciais para `config/credentials/`

**Tempo Estimado:** 3-4 horas  
**Valor:** Deployment e manutenção ficam ~80% mais simples

---

### Semana 3 (MÉDIA — Observabilidade)
- ✅ D5: Extrair `_run_pipeline()` helper em `agente_ia.py`
- ✅ D8: Validar assets na inicialização
- ✅ D10: Adicionar lockfile para evitar execuções sobrepostas
- ✅ D11: Ativar `send_report()` com relatório diário
- ✅ D12: Adicionar `--dry-run` aos pipelines

**Tempo Estimado:** 3-4 horas  
**Valor:** Sistema passa a ser observável e testável

---

### Semana 4+ (ALTA/MÉDIA — Refactors Maiores)
- ⏳ O1: Implementar Drive Watcher (2 min latência)
- ⏳ O2: Cache local de documentos (50% mais rápido)
- ⏳ O3: Migrar NJUD para `PipelineEngine` (maior refactor)
- ⏳ O4: Banco de observabilidade
- ⏳ O5: Aposentar `gerar_locucao_giro_premium.py`

**Tempo Estimado:** 15-20 horas  
**Valor:** Sistema passa a ser reativo, escalável e diagnosticável

---

## ✅ JÁ IMPLEMENTADO

### Confirmado no CHANGELOG.md v2.1
- ✅ `core/constants.py` criado com `MONTH_MAP_SHORT`, `MONTH_MAP_FULL`, `WEEKDAYS_PT`, funções auxiliares
- ✅ `gerar_njud_tts.py` já faz `from core.constants import ...`
- ✅ Código morto removido em `gerar_njud_tts.py`
- ✅ `edge_tts` falha com graceful fallback (não é mais bloqueante)

### Confirmado no VOICE_AGENT_STATUS.md
- ✅ Voice Edit Agent implementado (API completa)
- ✅ Aprovação de áudio humano funcional
- ✅ Dashboard com aba de aprovação
- ✅ Testes unitários (100% OK)
- ✅ Congelamento de síntese IA (redirecionando para locuções humanas)

---

## 📝 NOTAS ADICIONAIS

**Por que essas demandas ficaram pendentes?**

O projeto atingiu um patamar de "produção viável" com locuções humanas (Voice Edit Agent), mas há débito técnico acumulado dos estágios anteriores (síntese IA). O sistema é operável **em condições ideais** (sem mudança de servidor, sem bugs simultâneos), mas frágil em **edge cases** (novo servidor, caminhos faltantes, crashes silenciosos).

As demandas listadas são de **reparação e prevenção**, não de novas features. Resolvê-las não agrega funcionalidade, mas reduz drasticamente o custo de manutenção e risco operacional.

**Quem deve resolver?**

- **Bugs (B1–B6):** Qualquer desenvolvedor com 1-2h
- **Dívidas técnicas (D1–D13):** Desenvolvedor sênior com conhecimento de arquitetura (1-2 dias)
- **Otimizações (O1–O5):** Desenvolvedor sênior com visão de escalabilidade (3-5 dias)

---

**Próximos Passos Recomendados:**

1. **Hoje:** Executar os 6 bugs críticos em ~1h
2. **Esta Semana:** Refactor de fundação (D1–D7) em 3-4h
3. **Próxima Semana:** Observabilidade (D8–D13) em 3-4h
4. **Mês que vem:** Otimizações maiores (O1–O5) conforme prioridades de negócio

---

**Documento Mantido Por:** Consolidação de 24 de Junho de 2026  
**Próxima Revisão:** Após resolução de 50% das demandas
