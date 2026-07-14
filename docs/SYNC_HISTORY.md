# Histórico de Sincronização Git — Rádio IA TJRN

> Registro auditável de merges e eventos relevantes do repositório.
> Última atualização: 25/jun/2026

---

## 📅 25/jun/2026 — Sincronização `origin/minhas-alteracoes` → `resolucao-codespaces`

### Contexto

A branch `origin/minhas-alteracoes` estava **22 commits à frente** do estado local, mas com **divergência não-trivial**: o remoto tinha apenas 6 commits exclusivos, e o local tinha 21 commits exclusivos (mais robustos).

**Resultado:** merge manual com preservação da versão local.

### Diagnóstico Pré-Merge

| Métrica | Valor |
|---------|-------|
| Commits exclusivos no LOCAL | 21 |
| Commits exclusivos no REMOTO | 6 |
| Arquivos divergentes | 86 |
| Linhas inseridas/removidas | +3.092 / -9.890 |
| Arquivos NOVOS no remoto | 9 |
| Arquivos marcados como DELETADOS no remoto | 44 |

**Análise dos 6 arquivos em conflito** (via subagente de análise):

| Arquivo | Linhas local | Linhas remoto | Veredito |
|---------|--------------|---------------|----------|
| `core/gdoc_exporter.py` | 291 (5 fn, 16 try) | 244 (3 fn, 12 try) | LOCAL mais completo |
| `modules/agente/agente_ia.py` | 846 (26 fn, 62 try) | 711 (20 fn, 49 try) | LOCAL mais completo |
| `modules/boletins/boletins_pipeline.py` | 142 | 142 | LOCAL (importa `carregar_env_var`) |
| `modules/boletins/gerar_boletins_tts.py` | 646 (16 fn, 30 try) | 600 (13 fn, 22 try) | LOCAL mais completo |
| `modules/jornal/gerar_njud_tts.py` | 690 (15 fn, 34 try) | 773 (13 fn, 30 try) | LOCAL (mais funções) |
| `voice_agent/runner.py` | 203 (5 fn) | 123 (4 fn) | LOCAL (importa `splitter`) |

**Veredito:** Em 5/6 arquivos, a versão local é mais completa. Apenas `njud_tts.py` tem mais linhas no remoto, mas o local tem mais funções e try/except.

**Arquivos deletados no remoto (verificados no FS):** 10/10 amostrados ainda existem localmente com modificações recentes (jun/21–24). Merge cego apagaria trabalho.

### Estratégia Aplicada

```
1. Backup completo → C:\Users\THIAGO\radio_ia_backup_files (697 arq, 1.6 GB)
2. Branch de segurança → backup-pre-merge-20260625
3. git merge -X ours origin/minhas-alteracoes --no-commit --no-ff
4. Resolução de conflito no cherry-pick do bde3ac3 (runner.py)
5. git rm --cached .env (proteção de credenciais)
6. Validação: pytest 8/8 + imports OK + sem marcadores de conflito
7. Push → origin/resolucao-codespaces (e021bbf)
```

### Commits Resultantes (9)

```
e021bbf chore: remover .env do tracking (proteção de credenciais)
2cca2cc fix: corrigir a obtenção do timestamp para datetime.now (cherry-pick)
b71aef7 merge: integrar origin/minhas-alteracoes preservando versão local
55de62f feat: adicionar suporte ao DriveWatcher e cache de documentos
115c2f3 feat: adicionar suporte a cache na exportação de Google Drive
022d3c8 feat: adicionar script de geração de locução premium para o Giro
5c1227b feat: Enhance PipelineEngine com dry-run mode e asset validation
f1bde12 feat: adicionar arquivo Voice_Edit_Agent_Lacunas.docx
bde3ac3 fix: datetime.now em vez de utcnow (cherry-pick)
```

### Mudanças Incorporadas (do remoto)

| Tipo | Arquivos |
|------|----------|
| **Novos módulos** | `core/db.py` (SQLite execucoes), `core/drive_watcher.py` (watcher reativo) |
| **Documento** | `Voice_Edit_Agent_Lacunas.docx` |
| **Cache mensal** | `modules/boletins/planilha_csv/{JAN-JUN}2026.csv` |
| **Melhorias** | `core/engine.py` (+199/~47), `core/send_report.py` (+91/~45) |
| **Config** | `.env.example` (+16 vars: `NJUD_ROTEIROS_FOLDER_ID`, `GIRO_ROTEIROS_FOLDER_ID`, `DOC_CACHE_TTL_S`, `CREDENTIALS_PATH`, `EMAIL_RECIPIENT`) |
| **Fix crítico** | `voice_agent/runner.py`: `utcnow()` (deprecated Py 3.12) → `now(tz=timezone.utc)` |

### Mudanças Preservadas (do local)

Apesar de o remoto marcar como "deletados", os seguintes arquivos críticos foram **preservados**:

- `voice_agent/splitter.py` (12.754 B)
- `voice_agent/assembler.py` (7.574 B)
- `upgrade/notificador_whatsapp.py` (15.672 B)
- `upgrade/notificador.py` (12.090 B)
- `core/notificador_push.py` (7.803 B)
- `core/notificador_whatsapp.py` (12.509 B)
- `roadmap_upgrades_radio_ia.md` (25.214 B)
- `test_runner_real.py` (656 B)
- `config.yaml` (461 B)
- `modules/migracao/migrar_drive_g.py` (5.169 B)
- E mais 34 arquivos da lista original (44 total)

### Validação Pós-Merge

| Check | Resultado |
|-------|-----------|
| Marcadores `<<<<<<<` / `=======` / `>>>>>>>` | ✅ nenhum |
| Sintaxe Python (8 arquivos modificados) | ✅ todos OK |
| `pytest tests/` | ✅ 8 passed |
| `import core.db` | ✅ OK |
| `import core.drive_watcher` | ✅ OK |
| `import core.engine` | ✅ OK |
| `import voice_agent.runner` | ✅ OK |
| `git status` | ✅ working tree clean |
| Local HEAD == Remote HEAD | ✅ `e021bbf` |

---

## 🔒 Segurança

### Achado Crítico: `.env` exposto no histórico

**Antes do merge (25/jun):**
- O arquivo `.env` estava **tracked** no git desde o commit `ee308c7` (data antiga)
- Continha 3 chaves de API REAIS:
  - `OPENAI_API_KEY`
  - `GEMINI_API_KEY`
  - `GROQ_API_KEY`
- O `.gitignore` listava `.env` mas só protege arquivos NOVOS (não remove os já tracked)

**Mitigação aplicada (commit `e021bbf`):**
- `git rm --cached .env` — remove do tracking mas preserva arquivo local
- Backup do `.env` em `C:\Users\THIAGO\radio_ia_backup_files\dotenv_pre_untrack.bak`
- Próximos commits não incluirão `.env` automaticamente

**Limitação:** O `.env` antigo permanece acessível no histórico de commits. Para removê-lo completamente, seria necessário `git filter-repo` (operação destrutiva que reescreve todos os commits).

**⚠️ AÇÃO NECESSÁRIA (manual, fora do escopo do agente):**

1. **Rotacionar as 3 chaves de API:**
   - OpenAI: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
   - Google AI Studio: [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
   - Groq: [console.groq.com/keys](https://console.groq.com/keys)

2. **Atualizar `.env` local** com as novas chaves

3. **Atualizar `.env` em qualquer deploy** ativo

4. **Verificar uso indevido** nos 3 serviços (logs de uso)

5. **(Opcional, recomendado)** Reescrever histórico com `git filter-repo`:
   ```bash
   pip install git-filter-repo
   git filter-repo --invert-paths --path .env
   git push origin --force --all
   ```
   ⚠️ Isso invalida clones existentes — comunicar à equipe antes.

### Backups Realizados

| Local | Conteúdo | Tamanho |
|-------|----------|---------|
| `C:\Users\THIAGO\radio_ia_backup_files\` | 697 arquivos críticos + git log/status | 1.6 GB |
| `C:\Users\THIAGO\radio_ia_backup_files\dotenv_pre_untrack.bak` | `.env` antes de remover tracking | 2.089 B |

### Branch de Segurança

```
branch: backup-pre-merge-20260625
base:   origin/resolucao-codespaces (pré-merge)
commit: 32fd22c feat: Add SQLite database for document caching
```

Para restaurar este estado:
```bash
git checkout backup-pre-merge-20260625
```

---

## 📚 Lições Aprendidas

1. **Merge com `-X theirs` é perigoso** quando há trabalho local substancial. Preferir `-X ours` quando local é mais completo, ou merge manual com análise prévia.

2. **Sempre investigar divergência ANTES de merge.** O `git merge-tree` (ou `git diff --stat HEAD..FETCH_HEAD`) revela a extensão real do problema.

3. **Verificar filesystem local** antes de aceitar deleções do remoto. Arquivos "deletados no git" podem estar presentes e modificados no working tree.

4. **`.gitignore` não limpa tracked files.** Remover arquivo do tracking exige `git rm --cached` + commit.

5. **Credenciais NUNCA devem ser commitadas**, mas se foram no passado, rotacionar é mais importante que limpar histórico (limpar histórico não desfaz uso já feito).

---

## 📋 Eventos Anteriores

*(Nenhum registrado antes de 25/jun/2026. Este é o primeiro evento documentado.)*
