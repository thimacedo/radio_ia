# Análise Técnica — Rádio IA TJRN
**Data:** Junho de 2026  
**Escopo:** Auditoria completa dos 10 arquivos do sistema (agente_ia, engine, gerar_njud_tts, giro_pipeline, boletins_pipeline, processar_roteiro_completo, gerar_locucao_giro_premium, sincronizar_boletins_drive, best_practices, engine)

---

## 1. BUGS CONFIRMADOS (Precisam de Correção Imediata)

### B1 — `boletins_pipeline.py` linha 31: typo em `load_workbook`
```python
# ERRADO (lança AttributeError)
wb = openpyxl.load_load_workbook(local_xlsx, data_only=True) if ...

# CORRETO
wb = openpyxl.load_workbook(local_xlsx, data_only=True)
```

### B2 — `gerar_locucao_giro_premium.py` linha 127: variável `VOICE` não definida
```python
# ERRADO (lança NameError no main())
print(f"Voz: {VOICE}\n")

# CORRETO — referência deveria ser às duas vozes configuradas
print(f"Vozes: {VOZ_SPEAKER_1} / {VOZ_SPEAKER_2}\n")
```

### B3 — `engine.py` método `assemble_audio`: avanço incorreto da "agulha" da trilha
```python
# ERRADO — após zerar speech_timeline, usa o tamanho zerado para avançar bg_audio
speech_timeline = AudioSegment.empty()
bg_audio = bg_audio[len(speech_timeline):]  # len() == 0 aqui, não avança nada

# CORRETO — salvar o tamanho ANTES de zerar
consumed = len(speech_timeline)
speech_timeline = AudioSegment.empty()
bg_audio = bg_audio[consumed:]
```

### B4 — `agente_ia.py` linha 511: referência errada a `datetime.date`
```python
# ERRADO — datetime é a classe importada do módulo, não o módulo
if isinstance(refer_val, (datetime, datetime.date)):

# CORRETO
import datetime as dt
if isinstance(refer_val, (dt.datetime, dt.date)):
# ou, com o import atual:
from datetime import datetime, date
if isinstance(refer_val, (datetime, date)):
```

### B5 — `giro_pipeline.py` linha `receita_giro`: indentação incorreta de `VoiceStrategy`
```python
# ERRADO (VoiceStrategy fica fora do ProgramRecipe)
    voice_strategy=VoiceStrategy(
    type='intra_file',
    voices=[...]
),

# CORRETO
    voice_strategy=VoiceStrategy(
        type='intra_file',
        voices=[...]
    ),
```

### B6 — `gerar_njud_tts.py`: `shutil` importado dentro de loop
`import shutil` aparece duas vezes dentro do loop de sincronização. Mover para o topo do arquivo.

---

## 2. DÍVIDAS DE CÓDIGO (Code Smells / Duplicações)

### D1 — `MONTH_MAP_SHORT` definido 3× em arquivos diferentes
Está em `agente_ia.py` (função `obter_caminho_mes_njud_5s`), `gerar_njud_tts.py` (bloco de sincronização 5S) e `sincronizar_boletins_drive.py`. Centralizar em `core/models.py` ou `core/best_practices.py`:

```python
# core/best_practices.py
MONTH_MAP_SHORT = {
    1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR", 5: "MAI", 6: "JUN",
    7: "JUL", 8: "AGO", 9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ"
}
MONTH_MAP_FULL = {
    1: "1 - JANEIRO", 2: "2 - FEVEREIRO", 3: "3 - MARÇO", 4: "4 - ABRIL",
    5: "5 - MAIO",    6: "6 - JUNHO",     7: "7 - JULHO",  8: "8 - AGOSTO",
    9: "9 - SETEMBRO",10: "10 - OUTUBRO", 11: "11 - NOVEMBRO", 12: "12 - DEZEMBRO"
}
WEEKDAYS_PT = {0: "SEG", 1: "TER", 2: "QUA", 3: "QUI", 4: "SEX", 5: "SAB", 6: "DOM"}
```

### D2 — `extrair_linhas_fala` e `lines_to_falas` são idênticas em `gerar_njud_tts.py`
Remover `extrair_linhas_fala` e usar apenas `lines_to_falas` (ou vice-versa).

### D3 — Caminhos hardcoded espalhados por 5 arquivos
`r"H:\Meu Drive\RADIO TJRN CONTEÚDO\..."` aparece em `agente_ia.py`, `gerar_njud_tts.py`, `boletins_pipeline.py`, `sincronizar_boletins_drive.py` e `giro_pipeline.py`. Usar `.env` + `carregar_env_var()` que já existe em `best_practices.py`:
```ini
# .env
DRIVE_ROOT=H:/Meu Drive/RADIO TJRN CONTEÚDO
DRIVE_PRODUCAO=H:/Meu Drive/RADIO TJRN CONTEÚDO/00_PRODUCAO_2026
```

### D4 — `obter_caminho_mes_njud` usa if/elif em cascata frágil
Substituir pela tabela `MONTH_MAP_FULL` com busca regex direta.

### D5 — `executar_pipelines()` em `agente_ia.py`: código de subprocesso triplicado
Os três blocos `subprocess.run(...)` são cópias quase idênticas. Extrair para helper:
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
    registrar_log_5s(f"Pipeline {nome} {'concluído' if ok else 'falhou (código ' + str(res.returncode) + ')'}.")
    return ok
```

---

## 3. SUGESTÕES DE OTIMIZAÇÃO

### O1 — Spider/Watcher de Pendências no Drive (HIGH IMPACT)
Atualmente o agente só roda uma vez por dia via Agendador de Tarefas. Uma abordagem de "spider" reativo eliminaria atrasos:

```python
# core/drive_watcher.py
import time
from googleapiclient.discovery import build

class DriveSpider:
    """
    Monitora uma pasta do Drive e dispara callbacks quando novos
    documentos aparecem. Usa pageToken para só ver deltas (eficiente).
    """
    def __init__(self, drive_service, folder_id: str, callback, poll_interval: int = 120):
        self.service = drive_service
        self.folder_id = folder_id
        self.callback = callback
        self.poll_interval = poll_interval
        self._token = self._get_start_token()

    def _get_start_token(self) -> str:
        resp = self.service.changes().getStartPageToken().execute()
        return resp.get("startPageToken")

    def _poll(self):
        """Retorna lista de arquivos novos/modificados desde o último poll."""
        novos = []
        token = self._token
        while token:
            resp = self.service.changes().list(
                pageToken=token,
                spaces="drive",
                fields="newStartPageToken, nextPageToken, changes(fileId, file(name, mimeType, parents))"
            ).execute()
            for change in resp.get("changes", []):
                f = change.get("file", {})
                parents = f.get("parents", [])
                if self.folder_id in parents:
                    novos.append(f)
            token = resp.get("nextPageToken")
            self._token = resp.get("newStartPageToken", self._token)
        return novos

    def run_forever(self):
        print(f"[Spider] Monitorando pasta {self.folder_id} a cada {self.poll_interval}s...")
        while True:
            novos = self._poll()
            if novos:
                print(f"[Spider] {len(novos)} novo(s) arquivo(s) detectado(s)!")
                self.callback(novos)
            time.sleep(self.poll_interval)
```

**Uso no agente:**
```python
spider = DriveSpider(
    drive_service=drive_service,
    folder_id="ID_PASTA_ROTEIROS_GIRO",
    callback=lambda files: asyncio.run(processar_novos_roteiros(files)),
    poll_interval=120  # 2 minutos
)
spider.run_forever()
```
Isso faz o sistema ser **reativo**: um novo roteiro adicionado no Drive é processado em até 2 minutos, sem esperar o ciclo diário.

---

### O2 — Cache Local de Roteiros (evitar downloads repetidos)
O sistema baixa o mesmo Google Doc toda vez que o agente roda. Adicionar um cache em SQLite:

```python
# core/doc_cache.py
import sqlite3, hashlib, time, pathlib

class DocCache:
    def __init__(self, db_path="data/doc_cache.db"):
        self.con = sqlite3.connect(db_path)
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                doc_id TEXT PRIMARY KEY,
                conteudo TEXT,
                ts REAL
            )
        """)

    def get(self, doc_id: str, max_age_s: int = 3600) -> str | None:
        row = self.con.execute(
            "SELECT conteudo, ts FROM cache WHERE doc_id=?", (doc_id,)
        ).fetchone()
        if row and (time.time() - row[1]) < max_age_s:
            return row[0]
        return None

    def set(self, doc_id: str, conteudo: str):
        self.con.execute(
            "INSERT OR REPLACE INTO cache VALUES (?,?,?)",
            (doc_id, conteudo, time.time())
        )
        self.con.commit()
```

---

### O3 — Paralelismo nos pipelines (asyncio.gather com Semaphore)
Hoje `executar_pipelines()` roda Boletins → NJUD → Giro em série com `subprocess.run` (blocante). Como são programas independentes, podem rodar em paralelo:

```python
import asyncio, subprocess, sys

async def _run_pipeline_async(nome: str, script: str) -> bool:
    proc = await asyncio.create_subprocess_exec(
        sys.executable, script,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    ok = proc.returncode == 0
    registrar_log_5s(f"Pipeline {nome} {'OK' if ok else 'FALHOU'}.")
    return ok

async def executar_pipelines_paralelo():
    scripts = {
        "Boletins": os.path.join(project_root, "modules/boletins/gerar_boletins_tts.py"),
        "NJUD":     os.path.join(project_root, "modules/jornal/gerar_njud_tts.py"),
        "Giro":     os.path.join(project_root, "modules/giro/giro_pipeline.py"),
    }
    tasks = [_run_pipeline_async(nome, path) for nome, path in scripts.items()]
    resultados = await asyncio.gather(*tasks, return_exceptions=True)
    return all(r is True for r in resultados)
```
**Ganho estimado:** redução de ~60-70% no tempo total de produção diária.

---

### O4 — Fila de Retentativas para TTS com backoff exponencial
O `gerar_njud_tts.py` tem um `gerar_tts_com_retry` local. O `engine.py` usa o decorator `@retry_async` do `best_practices.py`. Padronizar: usar **apenas** o decorator do core em todos os módulos, passando `exceptions=(Exception,)` e `retries=5` para o edge-tts (que falha frequentemente em rajadas).

---

### O5 — Validação do roteiro ANTES de chamar o LLM (short-circuit)
Atualmente qualquer arquivo `.txt` vai para o LLM mesmo que esteja vazio ou corrompido. Adicionar um guard em `engine.py`:

```python
def process_text(self, raw_content: str) -> str:
    if not raw_content or len(raw_content.strip()) < 50:
        raise ValueError(f"Roteiro muito curto ou vazio ({len(raw_content)} chars). Abortando.")
    # ... resto do método
```

---

### O6 — Relatório de produção diária por e-mail/Telegram
O `core/send_report.py` existe mas não é invocado no fluxo principal. Criar um sumário consolidado ao final do `run_agent_once()`:

```python
def gerar_relatorio_diario(boletins_ok, njud_ok, giro_ok):
    data = datetime.now().strftime("%d/%m/%Y")
    linhas = [
        f"# Relatório Rádio TJRN — {data}",
        f"- Boletins: {'✅' if boletins_ok else '❌'}",
        f"- Jornal NJUD: {'✅' if njud_ok else '❌'}",
        f"- Giro nas Comarcas: {'✅' if giro_ok else '❌'}",
    ]
    return "\n".join(linhas)
```

---

### O7 — Migrar `sincronizar_boletins_drive.py` para usar `pathlib` e `shutil`
O arquivo usa `os.path.join(...).replace("\\", "/")` em 20+ locais. Com `pathlib.Path` isso some:

```python
from pathlib import Path
DRIVE_RADIO_BASE = Path(r"H:/Meu Drive/RADIO TJRN CONTEÚDO/00_PRODUCAO_2026/01_BOLETINS_DIARIOS/03_AUDIOS_RADIO")
drive_radio_day = DRIVE_RADIO_BASE / f"{mes_num:02d} - {short}" / dia_folder_name
drive_radio_day.mkdir(parents=True, exist_ok=True)
shutil.copy2(src, drive_radio_day / file)
```

---

### O8 — Adicionar `--dry-run` ao agente
Permite testar todo o fluxo de detecção de pendências e correção de planilha sem executar TTS ou fazer upload. Essencial para debug:

```python
parser.add_argument("--dry-run", action="store_true",
    help="Simula execução completa sem gravar arquivos nem chamar APIs de TTS/LLM.")
```

---

### O9 — Mecanismo de Lock para evitar execuções sobrepostas (Daemon Mode)
Se o ciclo diário demorar mais do que o `--interval`, duas instâncias podem rodar ao mesmo tempo. Adicionar um lockfile:

```python
import fcntl  # Linux; no Windows usar msvcrt.locking ou um arquivo .lock simples

LOCK_FILE = pathlib.Path(current_dir) / "agente_ia.lock"

def adquirir_lock() -> bool:
    if LOCK_FILE.exists():
        print("[AVISO] Outra instância do agente está em execução. Abortando.")
        return False
    LOCK_FILE.write_text(str(os.getpid()))
    return True

def liberar_lock():
    LOCK_FILE.unlink(missing_ok=True)
```

---

## 4. ARQUITETURA — MELHORIAS ESTRUTURAIS

### A1 — Unificar `gerar_locucao_giro_premium.py` ao `giro_pipeline.py`
O `gerar_locucao_giro_premium.py` reimplementa parse de roteiro e síntese TTS que o `engine.py` já faz. O módulo parece ser um predecessor do motor unificado que nunca foi removido. Verificar se ainda é usado; se não, mover para `archive/`.

### A2 — `gerar_njud_tts.py` ainda não usa `PipelineEngine`
É o único módulo que não migrou para a nova arquitetura unificada. O esforço de migração geraria:
- Eliminação de ~350 linhas de código duplicado (TTS, mixagem, distribuição)  
- Aproveitamento automático do `@retry_async` e `aplicar_pronuncia`
- Parse hook já implementável com `separar_secoes()` + `lines_to_falas()`

### A3 — Credenciais em `archive/` é um risco
```python
# agente_ia.py linha 43
CREDENTIALS_PATH = os.path.join(project_root, "archive", "gen-lang-client-...json")
```
A pasta `archive/` é descrita como "arquivo morto". Mover as credenciais para `config/credentials/` e adicionar ao `.gitignore`.

### A4 — `giro_pipeline.py`: gravação de `.gdoc` mock desnecessária
O workaround atual escreve um JSON fake no disco para o `gdoc_exporter` ler. O `export_gdoc_to_txt` deveria aceitar um `doc_id` diretamente:
```python
# Interface sugerida para gdoc_exporter.py
def export_gdoc_by_id(doc_id: str) -> str:
    service = _build_drive_service(CREDENTIALS_PATH)
    # ... download direto
```

---

## 5. RESUMO PRIORIZADO

| # | Item | Tipo | Impacto | Esforço |
|---|------|------|---------|---------|
| B1 | Typo `load_load_workbook` | Bug crítico | Boletins quebram | 1 linha |
| B3 | Agulha BG não avança | Bug de áudio | Trilha dessincroniza | 3 linhas |
| B2 | `VOICE` não definida | Bug crítico | Giro Premium trava | 1 linha |
| B4 | `datetime.date` incorreto | Bug silencioso | Datas não reconhecidas | 2 linhas |
| D1 | `MONTH_MAP` triplicado | Code smell | Manutenibilidade | 30 min |
| D5 | Subprocessos triplicados | Code smell | Manutenibilidade | 20 min |
| O3 | Pipelines em paralelo | Otimização | -60% tempo total | 2h |
| O1 | Spider reativo no Drive | Feature | Produção em tempo real | 4h |
| O2 | Cache de Google Docs | Otimização | -N chamadas API/dia | 1h |
| A2 | Migrar NJUD ao PipelineEngine | Refactor | -350 linhas duplicadas | 6h |
| A3 | Mover credenciais de `archive/` | Segurança | Risco de exposição | 10 min |
| O9 | Lockfile no Daemon | Resiliência | Evita race condition | 30 min |
