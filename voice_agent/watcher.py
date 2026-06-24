"""Watcher: monitora pastas de input e dispara pipeline de processamento.

Uso mínimo: executar em background; usa watchdog Observer.
Este arquivo contém stubs que devem ser completados com lógica de enfileiramento.
"""

import time
import os
from pathlib import Path
from threading import Thread

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except Exception:
    Observer = None
    FileSystemEventHandler = object

DEFAULT_INPUT_DIR = Path("inputs")


class _Handler(FileSystemEventHandler):
    def __init__(self, on_created_cb):
        super().__init__()
        self.on_created_cb = on_created_cb

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        time.sleep(1.5)  # aguarda upload completar
        self.on_created_cb(path)


def default_on_created(path: Path):
    print(f"[watcher] novo arquivo detectado: {path}")
    try:
        from .runner import process_file
        result = process_file(str(path), auto_approve=False)
        print(f"[watcher] processamento concluído: {result}")
    except Exception as e:
        print(f"[watcher] falha ao processar {path}: {e}")


def start_watch(input_root: Path = DEFAULT_INPUT_DIR, on_created_cb=default_on_created):
    if Observer is None:
        print("watchdog não instalado — execute processamento manualmente")
        return
    input_root.mkdir(parents=True, exist_ok=True)
    event_handler = _Handler(on_created_cb)
    observer = Observer()
    observer.schedule(event_handler, str(input_root), recursive=True)
    observer.start()
    print(f"Watcher iniciado em {input_root}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    start_watch()
