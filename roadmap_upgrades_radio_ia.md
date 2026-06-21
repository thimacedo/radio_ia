# Roadmap de Upgrades — Rádio IA TJRN
**Versão:** 2.0 → 3.0  
**Data:** Junho de 2026  
**Base analisada:** agente_ia, engine, gerar_njud_tts, giro_pipeline, boletins_pipeline, processar_roteiro_completo, gerar_locucao_giro_premium, sincronizar_boletins_drive, best_practices

> Os upgrades estão organizados em 4 fases cronológicas. Cada item indica o(s) arquivo(s) afetado(s), o esforço estimado e o ganho concreto esperado.

---

## FASE 1 — Fundação Sólida (1–2 semanas)
*Prerequisito para tudo mais: consolidar o core e eliminar as duplicações que hoje travam a evolução.*

---

### U1.1 — Centralizar constantes compartilhadas em `core/constants.py`
**Arquivos afetados:** `agente_ia.py`, `gerar_njud_tts.py`, `sincronizar_boletins_drive.py`, `giro_pipeline.py`, `boletins_pipeline.py`  
**Esforço:** 1h

`MONTH_MAP`, `MONTH_MAP_SHORT` e `WEEKDAYS_PT` estão duplicados em 3–5 arquivos. Criar um módulo único:

```python
# core/constants.py
MONTH_MAP_SHORT = {1: "JAN", 2: "FEV", ..., 12: "DEZ"}
MONTH_MAP_FULL  = {1: "1 - JANEIRO", 2: "2 - FEVEREIRO", ..., 12: "12 - DEZEMBRO"}
WEEKDAYS_PT     = {0: "SEG", 1: "TER", ..., 6: "DOM"}

def folder_name_5s(mes_num: int, ano_short: str = "26") -> str:
    """Retorna o nome padronizado da pasta no formato 5S: '06 - JUN - 26'"""
    return f"{mes_num:02d} - {MONTH_MAP_SHORT[mes_num]} - {ano_short}"

def obter_dia_semana(ano: int, mes: int, dia: int) -> str:
    from datetime import datetime
    return WEEKDAYS_PT[datetime(ano, mes, dia).weekday()]
```

**Ganho:** Qualquer alteração de padrão de nomenclatura de pastas passa a ser feita em 1 lugar.

---

### U1.2 — Migrar todos os caminhos hardcoded para `.env`
**Arquivos afetados:** todos os 7 módulos  
**Esforço:** 2h

Hoje `H:\Meu Drive\RADIO TJRN CONTEÚDO\...` aparece ~25 vezes espalhado. A função `carregar_env_var()` já existe em `best_practices.py` mas é subutilizada.

```ini
# .env — novas chaves propostas
DRIVE_ROOT=H:/Meu Drive/RADIO TJRN CONTEÚDO
DRIVE_PRODUCAO=${DRIVE_ROOT}/00_PRODUCAO_2026
DRIVE_BOLETINS=${DRIVE_PRODUCAO}/01_BOLETINS_DIARIOS
DRIVE_NJUD_TRAD=${DRIVE_ROOT}/NOT JUDICIARIO (5 MIN)/NJUD 2026
DRIVE_NJUD_5S=${DRIVE_PRODUCAO}/02_JORNAIS_NJUD
DRIVE_GIRO=${DRIVE_ROOT}/PROGRAMAS/PROGRAMA GIRO NAS COMARCAS (10min)
DRIVE_LOG=${DRIVE_PRODUCAO}/LOG_ACOES_5S.md
CREDENTIALS_PATH=config/credentials/service_account.json
NJUD_ROTEIROS_FOLDER_ID=1UHYp4SCterbUJF27MHj3bOh6ju1OBzIG
SPREADSHEET_ID_BOLETINS=1b1xnzvA00H1JC9uTvd6c-PBwQjEzGRs6t_raXG_ztsU
SPREADSHEET_ID_NJUD=1HegL-SudxPLI4Y6wsj1nnJocXHOvi-6inGqQld1lYec
SPREADSHEET_ID_GIRO=1Xbftz33ZEE4oc66ppgI5Sjy0T99WTUrN9gCJ85ZLDSo
```

**Ganho:** Trocar de servidor ou reorganizar o Drive exige editar apenas 1 arquivo.

---

### U1.3 — Migrar credenciais de `archive/` para `config/credentials/`
**Arquivos afetados:** `agente_ia.py` (linha 43), `gdoc_exporter.py`  
**Esforço:** 15min

```
archive/gen-lang-client-...json  →  config/credentials/service_account.json
```
Adicionar ao `.gitignore`:
```
config/credentials/
*.json.key
```
**Ganho:** Elimina risco de commit acidental de chave privada num diretório de "arquivo morto".

---

### U1.4 — Finalizar migração do NJUD para `PipelineEngine`
**Arquivos afetados:** `gerar_njud_tts.py`, `engine.py`, `models.py`  
**Esforço:** 6–8h  
**Maior refactor da Fase 1.**

`gerar_njud_tts.py` tem ~796 linhas e reimplementa TTS, mixagem e distribuição que o `engine.py` já faz. O único diferencial real é a montagem estruturada por seções (`ESCALADA → ABERTURA → NOTA1..4 → ENCERRAMENTO`).

Plano:
1. Adicionar ao `AssemblyRecipe` um campo `section_order: list[str]` para definir a sequência das seções.
2. Criar um `njud_parse_hook` que usa o `separar_secoes()` já existente em `gerar_njud_tts.py`.
3. Mover a lógica de mixagem estruturada para um método `assemble_audio_sectioned()` no engine.
4. Reduzir `gerar_njud_tts.py` para ~80 linhas (apenas a receita + fetch da planilha).

```python
# modules/jornal/njud_pipeline.py — resultado final
receita_njud = ProgramRecipe(
    name="Notícias do Judiciário (NJUD)",
    system_prompt=SYSTEM_PROMPT,
    voice_strategy=VoiceStrategy(type='intra_file', voices=["pt-BR-FranciscaNeural", "pt-BR-AntonioNeural"]),
    assembly=AssemblyRecipe(
        profile_path=project_root / "assets" / "profiles" / "njud_profile.json",
        section_order=["ESCALADA", "ABERTURA", "NOTA1", "NOTA2", "NOTA3", "NOTA4", "ENCERRAMENTO"]
    ),
    parse_hook=njud_parse_hook
)
```

**Ganho:** -~450 linhas de código duplicado. Qualquer melhoria no engine (retry, pronuncia, distribuição) passa a valer automaticamente para o NJUD.

---

### U1.5 — Aposentar `gerar_locucao_giro_premium.py`
**Arquivos afetados:** `gerar_locucao_giro_premium.py`, `giro_pipeline.py`  
**Esforço:** 30min

O arquivo reimplementa parse + TTS que o `giro_pipeline.py` (via `PipelineEngine`) já faz. Verificar se ainda é invocado em algum lugar. Se não, mover para `archive/` e documentar no `GEMINI.md`.

**Ganho:** Elimina ambiguidade sobre qual pipeline usar para o Giro.

---

## FASE 2 — Robustez e Observabilidade (2–4 semanas)
*O sistema passa a operar com resiliência de produção: sem travamentos silenciosos, com métricas e alertas.*

---

### U2.1 — Sistema de observabilidade: banco SQLite de execuções
**Arquivo novo:** `core/db.py`  
**Esforço:** 3h

Hoje o único rastro de execução é o `agente_ia.log` (append de texto plano) e o `agente_status.json` (sobrescrito a cada run). Não há histórico consultável.

```python
# core/db.py
import sqlite3, time, pathlib

DB_PATH = pathlib.Path("data/producao.db")

def init_db():
    con = sqlite3.connect(DB_PATH)
    con.executescript("""
        CREATE TABLE IF NOT EXISTS execucoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_inicio REAL, ts_fim REAL,
            pipeline TEXT,          -- 'boletins' | 'njud' | 'giro'
            arquivo TEXT,
            status TEXT,            -- 'ok' | 'erro' | 'skip'
            duracao_audio_s REAL,
            erro_msg TEXT
        );
        CREATE TABLE IF NOT EXISTS planilha_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL,
            tipo TEXT,              -- 'correcao_tag' | 'marcacao_audio'
            planilha TEXT,
            aba TEXT,
            linha INTEGER,
            detalhe TEXT
        );
    """)
    con.commit()
    return con
```

O Dashboard em `Dashboard.py` passa a consultar essa tabela para exibir histórico, taxa de sucesso por programa e tempo médio de produção por edição.

**Ganho:** Auditoria completa. Possibilidade de detectar padrões de falha (ex: NJUD falha toda segunda-feira às 08h por timeout da API).

---

### U2.2 — Lockfile para o daemon (evitar execuções sobrepostas)
**Arquivo afetado:** `agente_ia.py`  
**Esforço:** 30min

Se o ciclo diário demorar mais que o `--interval`, duas instâncias sobrepõem e corrompem os arquivos temporários de planilha.

```python
# agente_ia.py
import atexit

LOCK_FILE = pathlib.Path(current_dir) / ".agente.lock"

def adquirir_lock() -> bool:
    if LOCK_FILE.exists():
        pid = LOCK_FILE.read_text().strip()
        # Verificar se o processo ainda existe
        try:
            os.kill(int(pid), 0)
            print(f"[LOCK] Agente já em execução (PID {pid}). Abortando.")
            return False
        except (ProcessLookupError, ValueError):
            pass  # Processo morreu, lock é órfão — sobrescrever
    LOCK_FILE.write_text(str(os.getpid()))
    atexit.register(lambda: LOCK_FILE.unlink(missing_ok=True))
    return True
```

**Ganho:** Impossibilita corrupção de `temp_boletins_agente.xlsx` por duas instâncias simultâneas.

---

### U2.3 — Relatório de produção diária (e-mail / Telegram)
**Arquivos afetados:** `agente_ia.py`, `core/send_report.py` (já existe mas não é invocado)  
**Esforço:** 2h

`core/send_report.py` existe mas não é chamado em `run_agent_once()`. Ativar com sumário consolidado:

```python
# Ao final de run_agent_once():
relatorio = {
    "data": datetime.now().strftime("%d/%m/%Y"),
    "boletins": {"status": "OK" if boletins_ok else "FALHOU", "count": n_boletins},
    "njud":     {"status": "OK" if njud_ok else "FALHOU",     "count": n_njud},
    "giro":     {"status": "OK" if giro_ok else "FALHOU",     "count": n_giro},
    "conflitos_corrigidos": conflitos_corrigidos,
    "duracao_total_s": round(time.time() - ts_inicio),
}
send_report(relatorio)
```

**Configuração sugerida:** Telegram Bot é mais simples e confiável que SMTP no Windows.  
Adicionar ao `.env`: `TELEGRAM_BOT_TOKEN=...` e `TELEGRAM_CHAT_ID=...`

**Ganho:** Equipe recebe confirmação diária de produção sem precisar verificar manualmente o Drive ou o log.

---

### U2.4 — `--dry-run` no agente e nos pipelines individuais
**Arquivos afetados:** `agente_ia.py`, `giro_pipeline.py`, `boletins_pipeline.py`, `njud_pipeline.py`  
**Esforço:** 2h

```python
parser.add_argument("--dry-run", action="store_true",
    help="Simula detecção de pendências e correção de planilha sem gravar áudio nem fazer upload.")
```

No engine, quando `dry_run=True`:
- Imprime o roteiro revisado mas não chama `edge_tts`
- Não copia arquivos para o Drive
- Não faz upload de planilhas

**Ganho:** Permite testar o fluxo completo depois de refactors sem risco de produzir áudios errados ou sobrescrever planilhas.

---

### U2.5 — Validação de integridade de assets na inicialização
**Arquivo afetado:** `engine.py`, `agente_ia.py`  
**Esforço:** 1h

Hoje, se uma vinheta de abertura estiver faltando, o sistema produz o jornal inteiro **sem a abertura** — sem avisar ninguém até o operador ouvir o arquivo final.

```python
# engine.py — adicionar ao __init__
def _validar_assets(self):
    if not self.recipe.assembly.profile_path:
        return
    profile = json.loads(self.recipe.assembly.profile_path.read_text())
    faltando = []
    for nome, caminho in profile.get("assets", {}).items():
        if not os.path.exists(caminho):
            faltando.append(f"  • [{nome}] → {caminho}")
    if faltando:
        msg = "Assets ausentes:\n" + "\n".join(faltando)
        raise FileNotFoundError(msg)
```

**Ganho:** Falha rápida e explícita antes de gastar tempo de TTS/LLM.

---

### U2.6 — Cache de Google Docs (evitar downloads repetidos)
**Arquivo novo:** `core/doc_cache.py`  
**Esforço:** 1h

O agente baixa o mesmo roteiro toda vez que roda (se o NJUD tiver pendências acumuladas). Um cache SQLite com TTL de 1h resolve:

```python
class DocCache:
    def get(self, doc_id: str, max_age_s=3600) -> str | None: ...
    def set(self, doc_id: str, conteudo: str): ...
    def invalidate(self, doc_id: str): ...  # chamar após edição confirmada
```

**Ganho:** Elimina chamadas redundantes à API do Google em execuções repetidas no mesmo dia.

---

## FASE 3 — Automação Proativa (1–2 meses)
*O sistema para de depender do Agendador de Tarefas e passa a reagir a eventos reais.*

---

### U3.1 — Spider/Watcher reativo no Google Drive
**Arquivo novo:** `core/drive_watcher.py`  
**Esforço:** 4–6h  
**Upgrade mais impactante da fase.**

Hoje o sistema roda uma vez por dia e processa o que acumulou. Com o watcher, um novo roteiro adicionado ao Drive é processado em até 2 minutos.

A API do Google Drive tem suporte nativo a `changes.list()` com `pageToken` — retorna **apenas** os arquivos novos/modificados desde o último poll, sem reescanear a pasta inteira.

```python
# core/drive_watcher.py
class DriveWatcher:
    """
    Poll leve na API de Changes do Drive.
    Usa pageToken para só ver deltas — não reescaneia tudo.
    """
    def __init__(self, service, watched_folders: dict[str, callable], poll_s=120):
        """
        watched_folders: dict de {folder_id: callback_async}
        O callback recebe (service, file_metadata) e decide o que fazer.
        """
        self.service = service
        self.watched = watched_folders
        self.poll_s = poll_s
        self._token = self._start_token()

    def _start_token(self) -> str:
        return self.service.changes().getStartPageToken().execute()["startPageToken"]

    def _poll(self) -> list[dict]:
        novos, token = [], self._token
        while token:
            r = self.service.changes().list(
                pageToken=token,
                spaces="drive",
                fields="newStartPageToken,nextPageToken,changes(fileId,removed,file(id,name,mimeType,parents))"
            ).execute()
            for c in r.get("changes", []):
                if not c.get("removed"):
                    f = c.get("file", {})
                    for folder_id in self.watched:
                        if folder_id in f.get("parents", []):
                            novos.append((folder_id, f))
            token = r.get("nextPageToken")
            self._token = r.get("newStartPageToken", self._token)
        return novos

    async def run_forever(self):
        import asyncio
        print(f"[DriveWatcher] Monitorando {len(self.watched)} pasta(s) a cada {self.poll_s}s...")
        while True:
            for folder_id, arquivo in self._poll():
                callback = self.watched[folder_id]
                await callback(self.service, arquivo)
            await asyncio.sleep(self.poll_s)
```

**Uso no agente:**
```python
watcher = DriveWatcher(
    service=drive_service,
    watched_folders={
        FOLDER_ID_GIRO_ROTEIROS: processar_novo_giro,
        FOLDER_ID_NJUD_ROTEIROS: processar_novo_njud,
    },
    poll_s=120
)
asyncio.run(watcher.run_forever())
```

**Ganho:** Produção em tempo quase real. Elimina o atraso de 24h entre o roteiro ser postado e o áudio ser gerado.

---

### U3.2 — Pipelines em paralelo (asyncio em vez de subprocess serial)
**Arquivo afetado:** `agente_ia.py` (função `executar_pipelines`)  
**Esforço:** 2h

Hoje: `Boletins` → `NJUD` → `Giro` em série. Os três são independentes.

```python
async def executar_pipelines_paralelo() -> dict[str, bool]:
    scripts = {
        "Boletins": project_root / "modules/boletins/boletins_pipeline.py",
        "NJUD":     project_root / "modules/jornal/njud_pipeline.py",
        "Giro":     project_root / "modules/giro/giro_pipeline.py",
    }

    async def _run(nome, path):
        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        out, err = await proc.communicate()
        ok = proc.returncode == 0
        registrar_log_5s(f"Pipeline {nome}: {'OK' if ok else 'FALHOU (código ' + str(proc.returncode) + ')'}")
        return nome, ok

    resultados = await asyncio.gather(*[_run(n, p) for n, p in scripts.items()])
    return dict(resultados)
```

**Ganho estimado:** redução de 60–70% no tempo total de execução diária (ex: de ~45min → ~15min).

---

### U3.3 — Fila de produção persistente (SQLite)
**Arquivo novo:** `core/queue.py`  
**Esforço:** 4h

Hoje, se o agente travar no meio da execução (queda de rede, Windows Update, timeout de TTS), os itens que estavam sendo processados se perdem silenciosamente. Na próxima execução, o sistema detecta como "já processado" se o arquivo de saída existe parcialmente, ou reprocessa do zero.

Solução: uma fila de tarefas persistente.

```python
# core/queue.py
class FilaProducao:
    STATUS = ("pendente", "processando", "concluido", "erro")

    def enfileirar(self, pipeline: str, nome: str, metadados: dict): ...
    def pegar_proxima(self, pipeline: str) -> dict | None: ...
    def marcar_concluida(self, task_id: int): ...
    def marcar_erro(self, task_id: int, msg: str): ...
    def listar_pendentes(self, pipeline: str) -> list[dict]: ...
    def recolocar_processando(self):
        """Ao iniciar, itens em 'processando' voltam para 'pendente' (recuperação de crash)."""
```

**Ganho:** Resiliência total a crashes. O agente recomeça do ponto exato onde parou.

---

### U3.4 — `processar_roteiro_completo.py` integrado ao engine como pre_process_hook
**Arquivos afetados:** `processar_roteiro_completo.py`, `engine.py`, `njud_pipeline.py`  
**Esforço:** 2h

`processar_roteiro_completo.py` (conversão de números, ordinais, siglas, datas) é chamado de forma independente e manual. Já existe o campo `pre_process_hook` em `ProgramRecipe` para isso.

```python
# njud_pipeline.py
from processar_roteiro_completo import limpar_texto_locutor

def njud_pre_process(raw: str) -> str:
    """Aplica limpeza determinística ANTES de enviar ao LLM."""
    return limpar_texto_locutor(raw)  # números, datas, siglas, ordinais

receita_njud = ProgramRecipe(
    ...
    pre_process_hook=njud_pre_process,
    ...
)
```

**Ganho:** O LLM recebe texto já normalizado, reduzindo erros de pronunciação residuais e consumo de tokens.

---

### U3.5 — `gdoc_exporter` aceita `doc_id` diretamente (eliminar mock de .gdoc)
**Arquivos afetados:** `core/gdoc_exporter.py`, `giro_pipeline.py`  
**Esforço:** 1h

Hoje `giro_pipeline.py` escreve um JSON fake em disco para simular um `.gdoc`:
```python
temp_gdoc = txt_dir / f"{safe_name}.gdoc"
temp_gdoc.write_text(f'{{"doc_id": "{doc_id}"}}', encoding="utf-8")
texto = export_gdoc_to_txt(temp_gdoc)
temp_gdoc.unlink()
```

Adicionar uma função direta:
```python
# core/gdoc_exporter.py
def export_gdoc_by_id(doc_id: str) -> str:
    service = _build_drive_service(CREDENTIALS_PATH)
    request = service.files().export_media(fileId=doc_id, mimeType="text/plain")
    fh = io.BytesIO()
    MediaIoBaseDownload(fh, request).next_chunk()  # simplificado
    return fh.getvalue().decode("utf-8", errors="replace")
```

**Ganho:** Elimina I/O de disco desnecessário e o workaround confuso de arquivo mock.

---

## FASE 4 — Evolução do Produto (2–4 meses)
*Funcionalidades que elevam o sistema de uma automação interna para uma plataforma de produção radiofônica.*

---

### U4.1 — Painel de Controle: histórico e métricas de produção
**Arquivo afetado:** `Dashboard.py`  
**Esforço:** 6–8h  
**Dependência:** U2.1 (banco SQLite de execuções)

O Dashboard atual exibe apenas status em tempo real (progresso % e step atual). Adicionar uma aba "Histórico" que consulta a tabela `execucoes` do SQLite:

- Gráfico de barras: edições produzidas por dia (últimos 30 dias), separadas por programa
- Taxa de sucesso por pipeline
- Tempo médio de produção por edição (minutos)
- Lista das últimas 10 falhas com mensagem de erro
- Botão "Reprocessar" para um item com status `erro`

**Ganho:** Visibilidade total sobre a saúde do sistema. Decisões de manutenção baseadas em dados.

---

### U4.2 — Dicionário de pronúncia editável pelo Dashboard
**Arquivos afetados:** `Dashboard.py`, `data/pronunciation_rules.json`, `best_practices.py`  
**Esforço:** 3h

Hoje o `data/pronunciation_rules.json` só pode ser editado manualmente no arquivo. Adicionar uma aba "Pronúncia" ao Dashboard com:
- Tabela editável: Sigla / Pronúncia fonética / Programa (todos | NJUD | Giro | Boletins)
- Campo de teste: "Digite uma frase e veja como ficará após a fonetização"
- Botão "Salvar" que persiste no JSON

**Ganho:** A equipe editorial pode corrigir pronúncias sem precisar de acesso técnico ao código.

---

### U4.3 — Sistema de vozes com múltiplos perfis configuráveis
**Arquivos afetados:** `core/voice_queue.py`, `core/models.py`, `Dashboard.py`  
**Esforço:** 4h

Hoje as vozes são fixas por programa (Francisca + Antonio para Boletins, etc.). Criar um sistema de perfis:

```json
// assets/profiles/voices.json
{
  "perfis": {
    "bancada_padrao": {
      "speaker1": "pt-BR-FranciscaNeural",
      "speaker2": "pt-BR-AntonioNeural"
    },
    "bancada_alternativa": {
      "speaker1": "pt-BR-ElzaNeural",
      "speaker2": "pt-BR-ThalitaNeural"
    },
    "voz_unica_feminina": {
      "speaker1": "pt-BR-FranciscaNeural"
    }
  }
}
```

O Dashboard permite alternar o perfil de vozes de cada programa sem redeployar.

**Ganho:** Flexibilidade para datas comemorativas, férias de locutores virtuais "titulares", testes de qualidade.

---

### U4.4 — Revisão automática de qualidade de áudio pós-produção
**Arquivo novo:** `core/qa_audio.py`  
**Esforço:** 4h

Após o `engine.py` gerar o MP3 final, executar verificações automáticas:

```python
from pydub import AudioSegment

def qa_audio(mp3_path: str, recipe_name: str) -> dict:
    audio = AudioSegment.from_mp3(mp3_path)
    duracao_s = len(audio) / 1000
    loudness_lufs = audio.dBFS
    
    alertas = []
    
    # Duração esperada por programa
    limites = {
        "Boletins": (60, 180),           # 1–3 min
        "NJUD": (240, 420),              # 4–7 min
        "Giro nas Comarcas": (480, 720), # 8–12 min
    }
    
    mi, ma = limites.get(recipe_name, (30, 900))
    if duracao_s < mi:
        alertas.append(f"Duração muito curta: {duracao_s:.0f}s (mín: {mi}s)")
    if duracao_s > ma:
        alertas.append(f"Duração muito longa: {duracao_s:.0f}s (máx: {ma}s)")
    if loudness_lufs < -35:
        alertas.append(f"Áudio muito baixo: {loudness_lufs:.1f} dBFS")
    if loudness_lufs > -5:
        alertas.append(f"Áudio possivelmente clipado: {loudness_lufs:.1f} dBFS")
        
    return {"duracao_s": duracao_s, "loudness_dBFS": loudness_lufs, "alertas": alertas}
```

Se houver alertas, registrar no banco (U2.1) e incluir no relatório diário (U2.3).

**Ganho:** Detecta automaticamente edições truncadas (falha de TTS no meio), áudio mudo (asset corrompido), ou jornais anormalmente longos (roteiro duplicado no Google Doc).

---

### U4.5 — Suporte a múltiplos anos sem alteração de código
**Arquivos afetados:** `agente_ia.py`, `sincronizar_boletins_drive.py`, `giro_pipeline.py`  
**Esforço:** 2h

Hoje o ano `2026` está hardcoded em nomes de pastas, filtros de planilha (`if "2026" not in sheet_name`) e sufixos de pasta (`"26"`). Em janeiro de 2027 o sistema precisará ser editado manualmente.

```python
# core/constants.py
import datetime

ANO_PRODUCAO = datetime.datetime.now().year
ANO_SHORT    = str(ANO_PRODUCAO)[-2:]  # "26", "27", ...
```

Substituir todas as ocorrências de `"2026"`, `"26"` e `2026` nas comparações de filtro por essas constantes.

**Ganho:** Sistema vira o ano automaticamente sem intervenção manual.

---

### U4.6 — Interface de aprovação manual antes da distribuição
**Arquivos afetados:** `Dashboard.py`, `engine.py`  
**Esforço:** 8h

Para programas críticos (NJUD), adicionar um modo `pending_approval` onde o áudio é gerado localmente mas fica aguardando aprovação no Dashboard antes de ser copiado para o Drive.

```
[Produzir] → [Aguardando aprovação] → [▶ Preview] → [✔ Aprovar / ✗ Rejeitar]
               ↑ estado no SQLite         ↑ player no Dashboard    ↑ botões
```

Ao aprovar: `engine.distribute()` é chamado e a planilha é marcada com `✔`.  
Ao rejeitar: arquivo vai para `workspace/4_rejeitados/` com nota do operador.

**Ganho:** Controle editorial humano no loop, especialmente útil para edições de grande repercussão ou quando a IA faz uma reescrita questionável.

---

## Visão Geral do Roadmap

```
FASE 1 (1–2 sem)     FASE 2 (2–4 sem)      FASE 3 (1–2 meses)    FASE 4 (2–4 meses)
─────────────────    ──────────────────    ──────────────────     ──────────────────
U1.1 Constantes      U2.1 SQLite           U3.1 DriveWatcher★     U4.1 Dashboard hist.
U1.2 .env            U2.2 Lockfile         U3.2 Paralelo★         U4.2 Dicion. pronúncia
U1.3 Credenciais     U2.3 Relatório        U3.3 Fila persistente  U4.3 Perfis de vozes
U1.4 NJUD engine★   U2.4 --dry-run        U3.4 pre_process_hook  U4.4 QA de áudio
U1.5 Aposentar Giro  U2.5 Validar assets   U3.5 gdoc_exporter     U4.5 Suporte mult. anos
Premium              U2.6 Cache Docs                              U4.6 Aprovação manual

★ = upgrades de maior impacto da fase
```

**Prioridade absoluta antes de qualquer fase:** corrigir os 6 bugs da análise técnica (B1–B6), especialmente B1 (typo `load_load_workbook`) e B3 (agulha BG não avança).
