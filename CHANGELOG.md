# CHANGELOG — Rádio IA TJRN
**Data:** 21 de Junho de 2026
**Versão:** 2.x → 2.1

---

## Mudanças Implementadas

### ✅ CORE — `core/constants.py` (NOVO)
**Arquivo criado:** `core/constants.py`

Centraliza todas as constantes de data/calendário do sistema num único módulo:
- `MONTH_MAP_SHORT` — nomes curtos (JAN, FEV, ...)
- `MONTH_MAP_FULL` — nomes completos (1 - JANEIRO, 2 - FEVEREIRO, ...)
- `WEEKDAYS_PT` — dias da semana em português (SEG, TER, ...)
- `ANO_PRODUCAO` — ano atual (2026, 2027, ...) — automático
- `ANO_SHORT` — sufixo de 2 dígitos ("26", "27", ...) — automático
- `folder_name_5s(mes_num, ano_short)` — nome padronizado de pasta 5S
- `obter_dia_semana_pt(ano, mes, dia)` — dia da semana em PT
- `obter_mes_por_nome(nome)` — resolve nome/número → número do mês
- `extrair_mes_num_de_caminho(caminho)` — extrai mês de strings variadas

**Impacto:** Qualquer mudança de formato de pasta ou nome de mês agora é feita em 1 lugar.

---

### ✅ D1 — MONTH_MAP Duplicado Removido
**Arquivo:** `modules/jornal/gerar_njud_tts.py`

**Antes:**
- `MONTH_MAP` definido 3× no mesmo arquivo (linhas 19, 451-455, 590-594)
- `from core.best_practices import MONTH_MAP_SHORT` (incompleto)

**Depois:**
- `from core.constants import MONTH_MAP_SHORT, MONTH_MAP_FULL, ANO_SHORT, extrair_mes_num_de_caminho`
- Referências internas `MONTH_MAP` substituídas por `MONTH_MAP_FULL`

---

### ✅ D2 — Código Morto Removido
**Arquivo:** `modules/jornal/gerar_njud_tts.py`

**Antes:**
```python
def extrair_linhas_fala(texto_revisado):
    return lines_to_falas(texto_revisado.splitlines())

def lines_to_falas(linhas):
    ...  # implementação real
```
`extrair_linhas_fala` era wrapper inútil — mantido apenas por compatibilidade.

**Depois:** `extrair_linhas_fala` removido; apenas `lines_to_falas` permanece.

---

### ✅ D3 — Caminhos Padronizados via .env
**Arquivos afetados:** `modules/giro/gerar_locucao_giro_premium.py`

**Antes:**
```python
VHT_DIR = Path(r"H:\Meu Drive\...\GIRO (10min)\_VHT")
```
(Hardcoded — quebrado em outra máquina)

**Depois:**
```python
from core.best_practices import carregar_env_var
VHT_DIR = Path(carregar_env_var("DRIVE_GIRO_VHT_DIR", _fallback))
```
Adicionar ao `.env`:
```ini
DRIVE_GIRO_VHT_DIR=H:/Meu Drive/RADIO TJRN CONTEÚDO/PROGRAMAS/PROGRAMA GIRO NAS COMARCAS (10min)/_VHT
```

---

### ✅ D4 — If/Elif Cascata Substituído por Lookup Table
**Arquivo:** `modules/jornal/gerar_njud_tts.py`

**Antes:**
```python
def obter_caminho_mes(refer_val):
    if not refer_val: return "6 - JUNHO"
    if "JUNHO" in refer_str.upper(): return "6 - JUNHO"
    elif "MAIO" in refer_str.upper(): return "5 - MAIO"
    elif "ABRIL" in refer_str.upper(): return "4 - ABRIL"
    elif "MARÇO" in refer_str.upper(): return "3 - MARÇO"
    elif "FEVEREIRO" in refer_str.upper(): return "2 - FEVEREIRO"
    elif "JANEIRO" in refer_str.upper(): return "1 - JANEIRO"
    ...
```
(8 condições encadeadas — frágil a mudanças)

**Depois:**
```python
def obter_caminho_mes(refer_val):
    if not refer_val:
        return MONTH_MAP_FULL.get(6, "6 - JUNHO")
    if isinstance(refer_val, datetime.datetime):
        return MONTH_MAP_FULL.get(refer_val.month, "6 - JUNHO")
    # Usa regex + MONTH_MAP_FULL como lookup table
    ...
```

---

### ✅ O9 — Lockfile Anti-Conflito
**Arquivo:** `modules/agente/agente_ia.py`

**Problema:** Se o ciclo demorar mais que `--interval`, duas instâncias rodam simultaneamente e corrompem `temp_boletins_agente.xlsx`.

**Solução:** Lockfile com verificação de processo:

```python
LOCK_FILE = os.path.join(current_dir, ".agente.lock")

def adquirir_lock() -> bool:
    if LOCK_FILE.exists():
        pid = int(read_pid())
        if processo_vivo(pid):  # via ctypes no Windows
            return False  # outra instância ativa
    write_pid(os.getpid())
    return True
```

**Resultado:** Se uma instância já roda, a segunda aborta com mensagem clara em vez de corromper dados.

---

### ✅ Importação Unificada de Constantes
**Arquivos:** `modules/agente/agente_ia.py`, `modules/jornal/gerar_njud_tts.py`

**Antes:**
```python
try:
    from core.best_practices import carregar_env_var, MONTH_MAP_SHORT, MONTH_MAP_FULL, WEEKDAYS_PT
except ImportError:
    ...  # fallback redundante copiado 3×
```

**Depois:**
```python
try:
    from core.best_practices import carregar_env_var
    from core.constants import MONTH_MAP_SHORT, MONTH_MAP_FULL, WEEKDAYS_PT, ANO_SHORT, folder_name_5s
except ImportError:
    ...  # fallback mínimo apenas
```

`folder_name_5s` usado em `obter_caminho_mes_njud_5s()` para gerar o nome 5S da pasta de forma automática.

---

### ✅ O10 — Notificações Push e WhatsApp (Ntfy + WA)
**Arquivos:** `core/notificador.py`, `core/notificador_whatsapp.py`

**Implementação:**
- Sistema unificado de notificações para o Agente de IA.
- **Push (Ntfy):** Pub/sub HTTP auto-hospedável, sem dependência de terceiros.
- **WhatsApp:** Integração flexível via CallMeBot (simples) ou Evolution API (enterprise).
- **Semântica:** Métodos padronizados (`notificar_inicio`, `notificar_sucesso`, `notificar_erro`, `notificar_relatorio_diario`, `notificar_drive_offline`).

**Impacto:** Rastreabilidade imediata de execução sem precisar consultar logs ou Drive.

---

## Próximos Passos Sugeridos (Roadmap)

| #  | Item                          | Prioridade | Esforço |
|----|-------------------------------|-----------|---------|
| O3 | Pipelines em paralelo (asyncio) | Alta      | 2h      |
| O2 | Cache SQLite de Google Docs    | Alta      | 1h      |
| O5 | Validação de assets na inicialização | Média | 1h      |
| O6 | Relatório diário por Telegram  | Média     | 2h      |
| U1.4 | Migrar NJUD para PipelineEngine | Alta   | 6h      |
| U2.1 | SQLite de execuções (histórico) | Média  | 3h      |
| U3.1 | DriveWatcher reativo           | Alta      | 4h      |

---

*Gerado automaticamente — 21/06/2026*
