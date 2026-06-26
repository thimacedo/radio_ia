import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pathlib
import datetime
import os
import sys

# Garante project_root no python path para imports corretos
project_root = pathlib.Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from core.best_practices import carregar_env_var

def obter_relatorio_dia() -> str:
    """Carrega dados do banco SQLite execucoes e constrói o relatório das últimas 24h."""
    from core.db import DB_PATH
    import sqlite3
    import time
    
    if not DB_PATH.exists():
        return "Nenhum histórico de execução SQLite encontrado no disco."
        
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cursor = conn.cursor()
        um_dia_atras = time.time() - 86400
        cursor.execute(
            """
            SELECT pipeline, ts_inicio, status, duracao_audio_s, erro_msg 
            FROM execucoes 
            WHERE ts_inicio >= ?
            ORDER BY ts_inicio DESC
            """,
            (um_dia_atras,)
        )
        rows = cursor.fetchall()
        
        if not rows:
            return "Nenhuma execução de pipeline registrada nas últimas 24 horas."
            
        report = "Execuções de Pipelines de Áudio (Últimas 24h):\n"
        report += "="*70 + "\n"
        for pipeline, ts_inicio, status, duracao, erro in rows:
            dt_str = datetime.datetime.fromtimestamp(ts_inicio).strftime("%H:%M:%S")
            duracao_str = f"{duracao:.1f}s" if duracao else "N/A"
            status_symbol = "✔ OK" if status == "ok" else ("❌ ERRO" if status == "erro" else "➖ SKIP")
            report += f"[{dt_str}] {pipeline.upper():<20} | {status_symbol:<7} | Áudio: {duracao_str:<6}"
            if erro:
                report += f" | Erro: {erro}"
            report += "\n"
        return report
    finally:
        conn.close()

def send_daily_report_email(recipient_email: str):
    """Gera e envia o e-mail de relatório consolidado de execuções do dia."""
    sender_email = carregar_env_var("EMAIL_USER", None)
    sender_password = carregar_env_var("EMAIL_PASS", None)
    
    report_content = f"Relatório Consolidado Rádio IA TJRN — {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
    report_content += obter_relatorio_dia()
    report_content += "\n\nSistema Rádio IA - Automação TJRN"
    
    print("\n=== RELATÓRIO CONSOLIDADO DO DIA ===")
    print(report_content)
    
    if not sender_email or not sender_password:
        print("\n[AVISO] EMAIL_USER ou EMAIL_PASS não configurados no .env. E-mail não enviado.")
        return
        
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = f"Relatório Rádio IA TJRN - {datetime.datetime.now().strftime('%d/%m/%Y')}"
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
    email_dest = carregar_env_var("EMAIL_RECIPIENT", "thi.macedo@gmail.com")
    send_daily_report_email(email_dest)
