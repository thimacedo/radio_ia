# Sistema de Automação de Locução e Edição — Rádio TJRN / NJUD

Este repositório contém a suíte de scripts e ferramentas em Python desenvolvida para a **Rádio Web Justiça Potiguar (TJRN)**, automatizando a síntese de voz (TTS) e o sound design de boletins informativos e do programa semanal **NJUD (Notícias do Judiciário)**.

---

## 🛠️ Requisitos e Instalação

### Instalação Rápida (Windows)
Se você está configurando o sistema em uma nova máquina Windows, utilize o script automatizado do PowerShell na raiz do projeto:

1. Abra o PowerShell na pasta do projeto.
2. Execute:
   ```powershell
   ./configurar_e_rodar.ps1
   ```
   *Ele validará o Python, instalará as dependências (`edge-tts`, `pydub`) e verificará se o FFmpeg está configurado corretamente no PATH.*

### Instalação Manual
Caso prefira configurar manualmente:

1. **Python 3.10+** (certifique-se de marcar "Add Python to PATH" durante a instalação).
2. **FFmpeg** instalado (necessário para manipulação de áudio com `pydub`). Baixe a versão estática e adicione o diretório `bin/` nas Variáveis de Ambiente do Windows.
3. Instale as bibliotecas Python:
   ```bash
   pip install edge-tts pydub openpyxl pandas
   ```

---

## 📂 Visão Geral do Código e Estrutura

### 1. Sistema de Boletins Diários (Rádio TJRN - 1 Minuto)
Focado no processamento em lote de boletins rápidos a partir de uma planilha de controle do Google Sheets.

* **`gerar_boletins_tts.py`**: O pipeline principal. Ele baixa a planilha de controle, identifica boletins pendentes (sem `✔` nas colunas de Locutor/Editor), obtém o roteiro via link do Google Doc, divide-o em `CABEÇA` e `OFF`, gera locuções em velocidades ajustadas (OFF a `+4%` de velocidade para dinâmica jornalística), realiza a mixagem com trilha de fundo a 20% de volume (`-14 dB`) e adiciona as vinhetas. No final, atualiza a planilha com `✔` e gera os CSVs correspondentes.
* **`sincronizar_boletins_drive.py`**: Copia os áudios gerados (versões **Mailing** e **Editada**) e os roteiros estruturados em texto para os respectivos diretórios organizados no Google Drive montado (`H:`).
* **`criar_boletim_do_dia.py`**: Cria pastas locais vazias para um dia específico (ex: `python criar_boletim_do_dia.py --data 30-05`).

### 2. Sistema do Programa Completo (NJUD - 5 Minutos)
Focado na formatação e locução do programa semanal NJUD com alternância de duas vozes.

* **`processar_com_gemini.py`**: Envia os roteiros brutos para a API do Gemini para tratamento de linguagem e formatação técnica (Speaker 1 / Speaker 2). Possui fallback automático entre 12 modelos da API para evitar bloqueios por limite de requisições.
* **`processar_roteiro_completo.py`**: Alternativa offline à IA. Usa expressões regulares e dicionários locais para formatar o roteiro e escrever números, siglas, sites e valores monetários por extenso.
* **`agente_njud.py` / `gerar_locucao_multi_speaker.py`**: Consome os roteiros tratados e gera a locução alternada (vocal feminina `pt-BR-FranciscaNeural` e masculina `pt-BR-AntonioNeural`), gerando o MP3 final encapsulado por vinhetas.
* **`patch_vinhetas.py`**: Utilitário para corrigir vinhetas de abertura e encerramento de arquivos MP3 gerados em lote de forma limpa e sem distorcer o conteúdo da locução.

---

## ⚙️ Integração com o Google Drive

O sistema integra-se de forma direta com o Google Drive para Desktop (montado por padrão na unidade `H:`). Os caminhos mapeados são:
* **Planilha de Controle:** `H:\Meu Drive\RADIO TJRN CONTEÚDO\0-BOLETINS\BOLETINS_2026.xlsx`
* **Roteiros Originais:** `H:\Meu Drive\RADIO TJRN CONTEÚDO\NOT JUDICIARIO (5 MIN)\NJUD 2026\`
* **Destino de Áudios Editados:** `H:\Meu Drive\RADIO TJRN CONTEÚDO\EDIÇÃO\BOLETINS\2026\`
* **Destino de Áudios Mailing:** `H:\Meu Drive\RADIO TJRN CONTEÚDO\1-BOLETINS ENVIADOS\2026\`

---

## 🔍 Regras de Controle de Metas

* **Cálculo de Dias Úteis:** A planilha calcula a meta mensal multiplicando a quantidade de dias úteis reais do mês (ex: 20 dias úteis para maio, descontando feriados) por 10 (meta diária).
* **Fórmula do Dashboard:** O dashboard na aba `DASHBOARD GERAL` deve utilizar referências dinâmicas às células F3 (Textos) e G3 (Áudios) das abas mensais (ex: `=MAI2026!F3`), evitando valores digitados manualmente (hardcoded) para que o progresso seja sempre exibido em tempo real.
