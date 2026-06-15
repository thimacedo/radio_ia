# Giro nas Comarcas — Fluxo de Trabalho Automático

Este diretório contém os roteiros, áudios e ferramentas de automação para o programa semanal **Giro nas Comarcas**.

## 📂 Estrutura de Pastas

* **`tts_txt/`**: Roteiros originais em formato texto.
* **`tts_txt_convertido/`**: Roteiros formatados com tags técnicas (`[Vh ...]`, `[LOC:]`).
* **`tts_txt_revisado/`**: Roteiros processados por IA (OpenAI) para adequação de linguagem (números por extenso, siglas soletradas).
* **`tts_mp3_premium/`**: Áudios finais gerados com vozes neurais de alta qualidade e mixagem de vinhetas.
* **`relatorios/`**: Auditorias de integridade dos arquivos.

## 🛠️ Scripts e Ferramentas

1. **`converter_giroscomarcas_seguro.py`**: Converte os roteiros brutos para o padrão de tags do sistema.
2. **`rewrite_giro_tts.py`**: Utiliza a API da OpenAI para reescrever os blocos de locução seguindo o manual de redação do TJRN.
3. **`gerar_locucao_giro_premium.py`**: Pipeline de síntese de voz (edge-tts) e mixagem automática com as vinhetas oficiais.

## 🎙️ Padrão de Locução

* **Speaker 1 (Feminino)**: `pt-BR-FranciscaNeural`
* **Speaker 2 (Masculino)**: `pt-BR-AntonioNeural`

As vinhetas são inseridas automaticamente conforme as marcações `[Vh abertura GIRO]`, `[Vh passagem]` e `[vht encerramento]`.
