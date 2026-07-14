"""CLI utilities to drive the Voice Edit Agent for development.

Comandos:
  run-watcher
  process <file>
  approve <job_json>
"""

import sys
import json
from pathlib import Path

from voice_agent.runner import process_file
from voice_agent.watcher import start_watch


def cmd_run_watcher():
    start_watch()


def cmd_process(path: str):
    res = process_file(path)
    print(json.dumps(res, indent=2, ensure_ascii=False))


def cmd_approve(json_path: str):
    with open(json_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    import requests
    r = requests.post("http://127.0.0.1:8001/voice/approve", json=payload)
    print(r.json())


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "run-watcher":
        cmd_run_watcher()
    elif cmd == "process" and len(sys.argv) > 2:
        cmd_process(sys.argv[2])
    elif cmd == "approve" and len(sys.argv) > 2:
        cmd_approve(sys.argv[2])
    else:
        print("Comando inválido")


if __name__ == "__main__":
    main()
