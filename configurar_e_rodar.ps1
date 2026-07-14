Write-Host "=== CONFIGURADOR E INSTALADOR AUTOMATICO DO SISTEMA DE LOCUCAO ===" -ForegroundColor Cyan

# 1. Verificar se Python esta instalado
$pythonCheck = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCheck) {
    Write-Host "[ERRO] Python nao foi encontrado no sistema! Por favor, instale o Python e marque a opcao 'Add Python to PATH' na instalacao." -ForegroundColor Red
    Pause
    Exit
}
Write-Host "[OK] Python detectado." -ForegroundColor Green

# 2. Instalar dependencias necessarias
Write-Host "`nInstalando/Atualizando dependencias do Python (edge-tts, pydub)..." -ForegroundColor Yellow
python -m pip install --upgrade pip
pip install edge-tts pydub

# 3. Verificar FFmpeg
$ffmpegCheck = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpegCheck) {
    Write-Host "`n[AVISO] FFmpeg nao foi detectado no PATH do Windows!" -ForegroundColor Yellow
    Write-Host "O pydub necessita do FFmpeg instalado no sistema para poder juntar os arquivos MP3 corretamente." -ForegroundColor Yellow
    Write-Host "Como instalar:" -ForegroundColor White
    Write-Host "  1. Baixe o zip de: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    Write-Host "  2. Extraia os arquivos na pasta 'C:\ffmpeg'"
    Write-Host "  3. Adicione 'C:\ffmpeg\bin' ao PATH do Windows (Variaveis de Ambiente)."
    Write-Host "  4. Abra um novo terminal e execute este script novamente.`n"
    Pause
    Exit
}
Write-Host "[OK] FFmpeg detectado e pronto para uso." -ForegroundColor Green

# 4. Executar script de locução
Write-Host "`n[OK] Tudo pronto! Iniciando a geracao de locucoes..." -ForegroundColor Green
python -u gerar_locucao_multi_speaker.py

Pause
