import os
from pathlib import Path

def aplicar_padrao_giroscomarcas(content: str) -> str:
    header1 = "ROTEIRO GIRO NAS COMARCAS //não entra na locução"
    header2 = "PROGRAMA 98|  EXIBIÇÃO: 28/10/2025 //não entra na locução"
    
    content = content.lstrip('\ufeff').replace('\r\n', '\n').replace('\r', '\n')
    blocks = [block.strip() for block in content.split('\n\n') if block.strip()]
    
    if not blocks:
        return f"{header1}\n{header2}\n\n[Vh abertura GIRO]\n\n[LOC:]\n\n[vht encerramento]"
    
    abertura = blocks[0]
    noticias = blocks[1:] if len(blocks) > 1 else []
    
    output = [
        header1,
        header2,
        "",  # Linha vazia após cabeçalhos
        "[Vh abertura GIRO]",
        "",  # Linha vazia antes de [LOC:]
        "[LOC:]",
        abertura,
        "",  # Linha vazia após bloco de locução
    ]
    
    for noticia in noticias:
        output.extend([
            "[Vh passagem]",
            "",  # Linha vazia antes de [LOC:]
            "[LOC:]",
            noticia,
            ""   # Linha vazia após bloco de locução
        ])
    
    output.append("[vht encerramento]")
    return "\n".join(output)

def main():
    pasta_origem = Path(r"E:\NJUD\PROGRAMA GIRO NAS COMARCAS\tts_txt")
    pasta_destino = pasta_origem.parent / "tts_txt_convertido"
    
    if not pasta_origem.exists():
        raise FileNotFoundError(f"Pasta de origem não encontrada: {pasta_origem}")
    
    pasta_destino.mkdir(parents=True, exist_ok=True)
    print(f"📁 Pasta de destino criada/verificada: {pasta_destino}\n")
    
    arquivos_txt = [f for f in pasta_origem.iterdir() if f.is_file() and f.suffix.lower() == '.txt']
    
    if not arquivos_txt:
        print("⚠️ Nenhum arquivo .txt encontrado na pasta de origem.")
        return
    
    print(f"🔍 {len(arquivos_txt)} arquivo(s) .txt encontrado(s) para processar.\n")
    
    for arquivo_origem in arquivos_txt:
        try:
            with open(arquivo_origem, 'r', encoding='utf-8-sig') as f:
                conteudo_original = f.read()
            
            conteudo_processado = aplicar_padrao_giroscomarcas(conteudo_original)
            
            arquivo_destino = pasta_destino / arquivo_origem.name
            
            with open(arquivo_destino, 'w', encoding='utf-8', newline='\n') as f:
                f.write(conteudo_processado)
            
            print(f"✅ Convertido: {arquivo_origem.name}")
            print(f"   📥 Origem:  {arquivo_origem}")
            print(f"   📤 Destino: {arquivo_destino}\n")
        
        except Exception as e:
            print(f"❌ ERRO em {arquivo_origem.name}: {str(e)}\n")
    
    print("🎉 CONCLUÍDO! Todos os arquivos foram convertidos para:")
    print(f"   {pasta_destino}")
    print("\n💡 Os arquivos originais permanecem intactos em:")
    print(f"   {pasta_origem}")

if __name__ == "__main__":
    main()
