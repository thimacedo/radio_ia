# Regras Inegociáveis do Agente

## 🚫 Preservação de Arquivos e Proibição de Exclusão

1. **Proibição Estrita de Exclusão**: O agente está terminantemente proibido de excluir, remover ou apagar qualquer arquivo ou diretório do workspace ou do Google Drive (`H:\Meu Drive\...`) que ele mesmo não tenha criado nesta sessão de execução.
2. **Preservação de Documentos Contratuais**: Roteiros originais (formatos `.gdoc`, `.docx`, `.txt`) e gravações/áudios originais (formatos `.mp3`, `.wav`) são documentos de comprovação contratual. Sob nenhuma hipótese eles podem ser apagados, renomeados ou modificados de forma destrutiva.
3. **Limpeza Segura (5S)**: A limpeza e organização do projeto (padrão 5S) deve se limitar exclusivamente a arquivos temporários de execução criados pelo próprio agente, respeitando todas as pastas de origem de dados, pautas, roteiros e áudios históricos.
4. **Verificação de Links e Junções**: Antes de realizar qualquer operação de deleção ou limpeza em diretórios locais, o agente deve verificar se o diretório não é uma junção de pastas (Directory Junction) ou link simbólico apontando para o Google Drive, para evitar que deleções locais se propaguem para a nuvem.
