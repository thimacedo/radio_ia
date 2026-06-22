# Guia de Configuração e Execução do Sistema de Locução (Edge TTS)

Este guia descreve como configurar e rodar o gerador de locução automática em lote em qualquer outro computador Windows.

## 🛠️ Requisitos de Sistema

Para que o script funcione com a mesma velocidade e eficiência, o novo computador precisa ter instalado:

1. **Python 3.10 ou superior**:
   * Baixe e instale do site oficial (python.org).
   * **IMPORTANTE:** Durante a instalação, marque a caixinha **"Add Python to PATH"**.
2. **FFmpeg**:
   * O `pydub` precisa do FFmpeg para ler/gravar os arquivos MP3.
   * **Como instalar:**
     * Baixe o build estático de [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) (versão `ffmpeg-release-essentials.zip`).
     * Extraia a pasta em um local seguro (ex: `C:\ffmpeg`).
     * Adicione a pasta `bin` (`C:\ffmpeg\bin`) às variáveis de ambiente PATH do sistema Windows.

---

## 🚀 Como Configurar em 1 Clique (Automatizado)

Criamos o script **`configurar_e_rodar.ps1`** que automatiza todo o processo de verificação e instalação das dependências.

### Como usar:
1. Copie toda a pasta `e:\NJUD` para o novo computador (ou clone o repositório).
2. Abra o PowerShell na pasta do projeto.
3. Execute o comando:
   ```powershell
   ./configurar_e_rodar.ps1
   ```
   *Ele vai instalar o `edge-tts` e o `pydub`, validar se o `ffmpeg` está no PATH e executar o script principal automaticamente.*

---

## ✍️ Configuração Manual (Passo a Passo)

Caso prefira fazer a instalação manualmente, siga os passos abaixo:

### Passo 1: Instalar Bibliotecas do Python
Abra o terminal na pasta do projeto e execute:
```cmd
pip install edge-tts pydub
```

### Passo 2: Estrutura de Pastas Necessária
Garanta que a pasta do projeto contenha as seguintes pastas e arquivos na raiz:
```
[NJUD]/
├── VH AB - NOTICIAS DA HORA.mp3       (Vinheta de abertura - Obrigatória)
├── VH ENC - NOTICIAS DA HORA.mp3      (Vinheta de encerramento - Obrigatória)
├── gerar_locucao_multi_speaker.py     (Script de locução principal)
├── roteiros_processados/              (Pasta de entrada dos textos por mês)
│   ├── 3 - MARÇO/
│   ├── 4 - ABRIL/
│   └── 5 - MAIO/
```

### Passo 3: Rodar o Gerador
```cmd
python gerar_locucao_multi_speaker.py
```

O script criará a pasta `locucoes_geradas_tts` contendo os áudios divididos por meses no formato padrão `NJUD_<EPISÓDIO>_<DD-MM-YYYY>.mp3` contendo as vinhetas e as duas vozes neurais premium.
