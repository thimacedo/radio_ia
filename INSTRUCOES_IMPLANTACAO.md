# Manual de Operação e Implantação - Estúdio Rádio IA (TJRN / NJUD)

Este documento serve como guia completo de instruções tanto para o **usuário humano (editor)** quanto para **agentes de Inteligência Artificial** que operem ou deem manutenção neste repositório na máquina de destino.

---

## 1. Guia para o Usuário Humano (Editor da Rádio)

### A. Preparação da Máquina
Ao baixar este repositório na nova máquina de edição, você precisa configurar o ambiente de execução local:
1. Abra o terminal (PowerShell ou Command Prompt) na pasta raiz do projeto.
2. Execute o script de configuração automática:
   ```powershell
   python setup_env.py
   ```
   *Este script cria uma pasta de ambiente virtual isolada (`venv`), instala as dependências necessárias e cria o arquivo de configuração `.env` na raiz.*
3. Abra o arquivo `.env` gerado na raiz e configure:
   - Suas chaves de API (ex: `GEMINI_API_KEY`, `GROQ_API_KEY`).
   - O caminho mapeado para o Google Drive na máquina local (variável `DRIVE_ROOT_PATH`, padrão `H:/Meu Drive/RADIO TJRN CONTEÚDO`).

### B. Execução dos Pipelines
Sempre que for iniciar uma rodada de gravação, abra o terminal no repositório e ative o ambiente virtual:
```powershell
# Ativar ambiente
.\venv\Scripts\Activate.ps1

# Executar Gravação de Boletins (Fila de 4 Vozes Neurais)
python modules/boletins/gerar_boletins_tts.py

# Executar Gravação do Giro nas Comarcas (10 min)
python modules/giro/giro_pipeline.py

# Executar Gravação do Notícias do Judiciário (NJUD)
python modules/jornal/njud_pipeline.py
```

### C. Como funcionam as Regras da Planilha de Boletins
- **Ignorar Boletins Manuais (Editor `RAD`)**: Se você criou ou gravou um boletim manualmente e não quer que a IA o sobrescreva ou processe, preencha a coluna **EDITOR** da planilha com o valor `RAD`. O script ignorará a linha.
- **Divisão de Vozes**: O script altera automaticamente o valor da coluna **LOCUTOR** no Google Sheets para indicar qual voz da fila round-robin foi utilizada no áudio (ex: `LIV ✔`, `LEO ✔`, `ELZ ✔`, `THA ✔`), enquanto o editor de gravação da IA é preenchido como `THI ✔`.

---

## 2. Guia para Agentes de Inteligência Artificial (Desenvolvedores IA)

Se você é um Agente IA instruído a dar manutenção, analisar ou estender este sistema nesta máquina, leia com atenção as regras arquiteturais abaixo:

### A. Organização do Projeto (Padrão 5S)
Siga estritamente as seguintes diretrizes de arquivos:
1. **Raiz Limpa**: Mantenha apenas arquivos de configuração global (`.env`, `.gitignore`, `requirements.txt`, `setup_env.py`, `README.md`) na raiz do repositório.
2. **Pastas Estruturadas**:
   - `core/`: Motor central unificado (`engine.py`, `best_practices.py`, `voice_queue.py`).
   - `modules/`: Lógicas individuais e pipelines de cada programa da rádio (`boletins/`, `giro/`, `jornal/`). Cada módulo deve conter sua pasta local `workspace/` para arquivos temporários locais.
   - `data/`: Planilhas de controle local e dicionários de pronúncia (`pronunciation_rules.json`).
   - `assets/`: Vinhetas (`vht/`) e perfis de mixagem (`profiles/`).
   - `tests/`: Suítes de testes automatizados (`test_system.py`).
   - `archive/`: Arquivo morto com versões legadas para evitar colisões com agentes novos.

### B. Ciclo de Vida do Processamento de Áudio
O pipeline segue cinco passos lógicos orquestrados pela `PipelineEngine` (`core/engine.py`):
1. **Extração/Download**: O pipeline baixa a pauta/planilha e os textos do Google Drive ou Google Sheets local.
2. **Reescrita IA (LLM)**: O texto é limpo e editado usando prompts jornalísticos específicos de rádio via `LLMFactory`.
3. **Fonetização e Gravação (TTS)**: O texto revisado passa pela função `aplicar_pronuncia` (para siglas como `TJRN` -> `T-J-R-N`, `COSERN` -> `Cozern` etc.) e é gravado com Microsoft Edge-TTS via `Communicator` com resiliência de retentativas `@retry_async`.
4. **Mixagem**: O áudio sintetizado é montado e mixado com as vinhetas e trilhas de fundo (BG) de acordo com o perfil de mixagem utilizando a biblioteca `pydub`.
5. **Distribuição**: Os arquivos finais em MP3 são copiados de volta para os respectivos diretórios de publicação do Google Drive mapeados no `.env`.

### C. Como Executar e Validar Alterações de Código
Sempre que fizer alterações no código do motor (`core/`), execute a suíte de testes unitários para garantir que não houve regressões:
```powershell
python -m unittest tests/test_system.py
```
A suíte testa isoladamente a fila de rotação de vozes, a fonetização baseada em JSON e o carregador dinâmico de variáveis do `.env`.
