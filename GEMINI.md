# Regras de Organização do Projeto (Padrão 5S)

1. **Raiz Limpa**: Manter na raiz apenas o .env, .gitignore, README.md e os arquivos iniciadores do Dashboard.
2. **Arquitetura**: O motor fica em core/, os assets em ssets/vht/, o arquivo morto em rchive/ e as lógicas de programas em modules/.
3. **Arquivos Temporários**: Testes devem ser feitos em scratch dentro do rchive/ e deletados quando não mais úteis.
4. **Workspaces Locais**: Cada módulo (ex: modules/giro) deve ter sua pasta workspace/ para converter os textos e áudios, sem espalhar lixo pelo projeto.