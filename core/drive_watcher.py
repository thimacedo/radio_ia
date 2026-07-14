"""
core/drive_watcher.py
---------------------
Watcher reativo para pastas do Google Drive via API changes.list().
Monitora mudanças e dispara callbacks para novos arquivos de roteiro.

Uso:
    from core.drive_watcher import DriveWatcher

    watcher = DriveWatcher(
        service=drive_service,
        watched_folders={
            "folder_id_njud":  on_new_njud,
            "folder_id_giro":  on_new_giro,
        },
        poll_s=120  # verifica a cada 2 minutos
    )
    watcher.run_forever()  # bloqueia; use run_background() para thread daemon
"""
from __future__ import annotations

import time
import threading
import logging
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


class DriveWatcher:
    """
    Monitora pastas do Google Drive usando a API changes.list() com pageToken.
    A cada poll_s segundos, verifica se houve novos arquivos nas pastas monitoradas.

    Args:
        service: Objeto do cliente Google Drive (googleapiclient.discovery.build).
        watched_folders: Dict mapeando folder_id -> callback(file_metadata: dict).
        poll_s: Intervalo entre verificações em segundos (padrão: 120).
        page_size: Número máximo de mudanças por página (padrão: 100).
    """

    def __init__(
        self,
        service,
        watched_folders: Dict[str, Callable[[dict], None]],
        poll_s: int = 120,
        page_size: int = 100,
    ):
        self.service = service
        self.watched_folders = watched_folders
        self.poll_s = poll_s
        self.page_size = page_size
        self._stop_event = threading.Event()
        self._page_token: Optional[str] = None
        self._page_token = self._fetch_start_token()

    # ------------------------------------------------------------------
    # API Pública
    # ------------------------------------------------------------------

    def run_forever(self) -> None:
        """
        Inicia o loop de monitoramento em modo bloqueante.
        Use run_background() para rodar em thread separada.
        """
        logger.info("[DriveWatcher] Iniciando monitoramento. Intervalo: %ds", self.poll_s)
        while not self._stop_event.is_set():
            try:
                self._poll_once()
            except Exception as e:
                logger.error("[DriveWatcher] Erro durante poll: %s", e)
            self._stop_event.wait(timeout=self.poll_s)
        logger.info("[DriveWatcher] Monitoramento encerrado.")

    def run_background(self) -> threading.Thread:
        """
        Inicia o watcher em uma thread daemon. Retorna a thread.
        """
        t = threading.Thread(target=self.run_forever, name="DriveWatcher", daemon=True)
        t.start()
        logger.info("[DriveWatcher] Thread daemon iniciada (id=%s).", t.ident)
        return t

    def stop(self) -> None:
        """Sinaliza parada do loop. A thread encerra no próximo ciclo."""
        self._stop_event.set()

    # ------------------------------------------------------------------
    # Implementação Interna
    # ------------------------------------------------------------------

    def _fetch_start_token(self) -> Optional[str]:
        """
        Obtém o pageToken inicial para que apenas mudanças *futuras* sejam processadas.
        """
        try:
            resp = self.service.changes().getStartPageToken().execute()
            token = resp.get("startPageToken")
            logger.info("[DriveWatcher] Token inicial obtido: %s", token)
            return token
        except Exception as e:
            logger.warning("[DriveWatcher] Não foi possível obter token inicial: %s", e)
            return None

    def _poll_once(self) -> None:
        """
        Executa uma rodada de verificação de mudanças e dispara callbacks.
        """
        if self._page_token is None:
            logger.warning("[DriveWatcher] Sem pageToken — tentando obter novamente.")
            self._page_token = self._fetch_start_token()
            if self._page_token is None:
                return

        try:
            while True:
                resp = (
                    self.service.changes()
                    .list(
                        pageToken=self._page_token,
                        pageSize=self.page_size,
                        fields="nextPageToken,newStartPageToken,changes(fileId,removed,file(id,name,parents,mimeType,modifiedTime))",
                        includeRemoved=False,
                        supportsAllDrives=False,
                    )
                    .execute()
                )

                for change in resp.get("changes", []):
                    self._handle_change(change)

                # Avança o token
                if "newStartPageToken" in resp:
                    self._page_token = resp["newStartPageToken"]
                    break
                elif "nextPageToken" in resp:
                    self._page_token = resp["nextPageToken"]
                else:
                    break

        except Exception as e:
            logger.error("[DriveWatcher] Erro na API changes.list(): %s", e)

    def _handle_change(self, change: dict) -> None:
        """
        Avalia se uma mudança é relevante e dispara o callback da pasta correta.
        """
        file_meta = change.get("file")
        if not file_meta or change.get("removed"):
            return

        file_id = file_meta.get("id")
        file_name = file_meta.get("name", "")
        parents = file_meta.get("parents", [])
        mime = file_meta.get("mimeType", "")

        # Ignorar pastas
        if mime == "application/vnd.google-apps.folder":
            return

        # Verificar se o arquivo pertence a alguma pasta monitorada
        for folder_id, callback in self.watched_folders.items():
            if folder_id in parents:
                logger.info(
                    "[DriveWatcher] Novo arquivo detectado: '%s' (id=%s) na pasta %s",
                    file_name, file_id, folder_id
                )
                try:
                    callback(file_meta)
                except Exception as e:
                    logger.error(
                        "[DriveWatcher] Erro no callback para '%s': %s", file_name, e
                    )
                break  # Arquivo só pertence a uma pasta monitorada por vez


# ---------------------------------------------------------------------------
# Funções helper para integração com o agente
# ---------------------------------------------------------------------------

def criar_watcher_padrao(drive_service, callbacks: Dict[str, Callable]) -> DriveWatcher:
    """
    Cria um DriveWatcher pré-configurado com as pastas padrão do sistema Radio IA.

    Args:
        drive_service: Serviço autenticado do Google Drive.
        callbacks: Dict {folder_id: callable} com as pastas a monitorar.
    """
    import sys
    import pathlib
    project_root_path = str(pathlib.Path(__file__).parent.parent)
    if project_root_path not in sys.path:
        sys.path.append(project_root_path)
    from core.best_practices import carregar_env_var

    # Carrega IDs das pastas do .env (adicione NJUD_ROTEIROS_FOLDER_ID ao .env)
    njud_folder = carregar_env_var("NJUD_ROTEIROS_FOLDER_ID", "")

    pastas: Dict[str, Callable] = {}
    if njud_folder and njud_folder in callbacks:
        pastas[njud_folder] = callbacks[njud_folder]

    # Adiciona outras pastas vindas do dict de callbacks
    for fid, cb in callbacks.items():
        if fid not in pastas:
            pastas[fid] = cb

    return DriveWatcher(service=drive_service, watched_folders=pastas)
