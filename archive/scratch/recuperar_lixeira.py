import os
import sys
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Configurações
CREDENTIALS_PATH = Path(r"e:\RÁDIO_IA\config\credentials\gen-lang-client-0980378916-8cc8eb1488d1.json")

if not CREDENTIALS_PATH.exists():
    print(f"Credenciais não encontradas em: {CREDENTIALS_PATH}")
    sys.exit(1)

scopes = ["https://www.googleapis.com/auth/drive"]
creds = service_account.Credentials.from_service_account_file(str(CREDENTIALS_PATH), scopes=scopes)
drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)

def listar_e_restaurar():
    print("Buscando arquivos na lixeira do Google Drive...")
    
    # Query para buscar arquivos deletados (na lixeira)
    query = "trashed = true"
    
    try:
        results = drive_service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType, parents)",
            pageSize=100
        ).execute()
    except Exception as e:
        print(f"Erro ao listar arquivos da lixeira: {e}")
        return
    
    files = results.get("files", [])
    
    if not files:
        print("Nenhum arquivo encontrado na lixeira.")
        return
        
    print(f"Encontrados {len(files)} arquivos na lixeira:")
    for f in files:
        print(f"ID: {f['id']} | Nome: {f['name']} | Tipo: {f['mimeType']}")
        
    restaurados = 0
    print("\nIniciando restauração automática de arquivos do projeto Rádio IA...")
    for f in files:
        name = f['name']
        mime = f['mimeType']
        is_interest = (
            name.endswith(('.gdoc', '.docx', '.mp3', '.wav', '.txt')) or 
            "GNC" in name or 
            "boletim" in name.lower() or 
            "njud" in name.lower() or 
            "programa" in name.lower() or
            "giro" in name.lower()
        )
        if is_interest:
            try:
                drive_service.files().update(
                    fileId=f["id"],
                    body={"trashed": False}
                ).execute()
                print(f"✅ Restaurado: {name} ({mime})")
                restaurados += 1
            except Exception as e:
                print(f"❌ Erro ao restaurar {name}: {e}")
                
    print(f"\nConcluído. Total de arquivos restaurados: {restaurados}")

if __name__ == "__main__":
    listar_e_restaurar()
