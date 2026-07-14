# Módulo do Agente de IA - Rádio TJRN

Este módulo contém o **Agente de IA** responsável por supervisionar cognitivamente e orquestrar de forma automatizada e resiliente a produção diária de rádio.

## Funcionalidades
1. **Auto-Mount do Drive**: Detecta se a unidade `H:` está desconectada e inicia o Google Drive Desktop.
2. **Cognição e Correção**: Inspeciona as planilhas à procura de incoerências (ex: tags de boletins duplicadas como duas B3) e as corrige na nuvem antes de iniciar a gravação.
3. **Orquestração Subprocessada**: Dispara os pipelines atuais (`gerar_boletins_tts.py` e `gerar_njud_tts.py`) sem alterar o código original, servindo como uma camada superior de controle.
4. **Fechamento de Status (NJUD)**: Atualiza automaticamente as planilhas de jornais após o processamento.
5. **Auditoria 5S**: Escreve relatórios e logs no Drive.

## Como Executar

### Execução única
Para executar o agente uma única vez (ideal para ser colocado no Agendador de Tarefas do Windows):
```bash
python agente_ia.py --once
```

### Execução em background (Daemon)
Para manter o agente rodando e varrendo o sistema a cada 5 minutos:
```bash
python agente_ia.py --daemon --interval 300
```
