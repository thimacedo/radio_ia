"""Notifier: integra com ntfy ou outro sistema de notificação.

Função simples: send_ntfy(topic, message)
"""

import subprocess
import shlex
import re


def send_ntfy(topic: str, message: str) -> bool:
    """Envia notificação via ntfy CLI se disponível.
    Fallback: imprime no stdout.
    """
    if not re.match(r"^[a-zA-Z0-9_\-./\\]+$", topic):
        return False
    if not re.match(r"^[a-zA-Z0-9_\-./\\]+$", message):
        return False
    try:
        cmd = f"ntfy -t {shlex.quote(topic)} publish '{message}'"
        subprocess.run(cmd, shell=True, check=False)
        return True
    except Exception:
        print(f"[notifier] {topic}: {message}")
        return False


if __name__ == "__main__":
    send_ntfy("radio_teste", "Mensagem de teste do Voice Edit Agent")
