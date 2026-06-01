import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pathlib
import datetime
import os

def get_env_key(key_name):
    env_path = pathlib.Path(r"E:\NJUD\.env")
    if env_path.exists():
        content = env_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith(f"{key_name}="):
                return line.split("=", 1)[1].strip()
    return None

def send_report_email(recipient_email, programs_list):
    # Configurações de e-mail (usando variáveis de ambiente para segurança)
    # Nota: O usuário precisará configurar EMAIL_USER e EMAIL_PASS no .env
    # Se não existirem, o script apenas imprimirá o relatório.
    
    sender_email = get_env_key("EMAIL_USER")
    sender_password = get_env_key("EMAIL_PASS")
    
    report_content = f"Relatório de Programas Giro nas Comarcas Gerados em {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
    report_content += "Programas processados e sincronizados com o Google Drive:\n"
    for prog in sorted(programs_list):
        report_content += f"- {prog}\n"
    
    report_content += "\nSistema NJUD - Automação TJRN"

    print("\n=== RELATÓRIO DE GERAÇÃO ===")
    print(report_content)

    if not sender_email or not sender_password:
        print("\n[AVISO] EMAIL_USER ou EMAIL_PASS não configurados no .env. E-mail não enviado.")
        return

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = f"Relatório Giro nas Comarcas - {datetime.datetime.now().strftime('%d/%m/%Y')}"
    
    msg.attach(MIMEText(report_content, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print(f"\n[SUCESSO] Relatório enviado para {recipient_email}")
    except Exception as e:
        print(f"\n[ERRO] Falha ao enviar e-mail: {e}")

if __name__ == "__main__":
    # Teste: pegar arquivos da pasta premium
    output_dir = pathlib.Path(r"E:\NJUD\PROGRAMA GIRO NAS COMARCAS\tts_mp3_premium")
    progs = [f.name for f in output_dir.glob("*.mp3")]
    send_report_email("thi.macedo@gmail.com", progs)
