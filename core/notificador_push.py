"""
core/notificador_push.py
────────────────────────
Módulo de notificações push para o Agente de IA da Rádio TJRN via ntfy.

COMO FUNCIONA:
  O ntfy é um serviço de pub/sub HTTP gratuito e open-source. O agente publica
  uma mensagem em um tópico e o app no celular (inscrito no mesmo tópico)
  recebe a notificação instantaneamente.

SETUP RÁPIDO (Sem Docker — usando servidor público gratuito):
─────────────────────────────────────────────────────────────
  1. Instale o app "ntfy" no seu celular:
       - Android: Google Play Store
       - iOS: App Store
  2. No app, clique no "+" (Subscribe) e digite um nome de canal único,
     por exemplo: "radio-tjrn-notif-2026"
  3. No arquivo .env, configure:
       PUSH_ATIVO=true
       NTFY_URL=https://ntfy.sh
       NTFY_TOPIC=radio-tjrn-notif-2026  <-- Cole o mesmo nome único escolhido no app
"""

import os
import json
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

try:
    from core.best_practices import carregar_env_var
except ImportError:
    try:
        from best_practices import carregar_env_var
    except ImportError:
        def carregar_env_var(chave: str, fallback: str = "") -> str:
            env_path = Path(__file__).parent.parent / ".env"
            if env_path.exists():
                for linha in env_path.read_text(encoding="utf-8").splitlines():
                    if "=" in linha and not linha.strip().startswith("#"):
                        k, _, v = linha.partition("=")
                        if k.strip() == chave:
                            return v.strip().strip('"').strip("'")
            return os.environ.get(chave, fallback)


class NotificadorPush:
    """Envia push notifications via ntfy (self-hosted ou servidor público ntfy.sh)."""

    URGENTE = "urgent"   # Som alto + ignora DND
    ALTO    = "high"     # Som normal
    NORMAL  = "default"  # Silencioso / som padrão
    BAIXO   = "low"      # Silencioso, agrupado

    def __init__(self):
        self.url     = carregar_env_var("NTFY_URL", "https://ntfy.sh").rstrip("/")
        self.topico  = carregar_env_var("NTFY_TOPIC", "radio-tjrn-notif-2026")
        self.usuario = carregar_env_var("NTFY_USUARIO", "")
        self.senha   = carregar_env_var("NTFY_SENHA", "")

    def _autenticar(self, req: urllib.request.Request):
        if self.usuario and self.senha:
            import base64
            credencial = base64.b64encode(f"{self.usuario}:{self.senha}".encode()).decode()
            req.add_header("Authorization", f"Basic {credencial}")

    def enviar(
        self,
        mensagem: str,
        titulo: str = "Rádio TJRN",
        prioridade: str = "default",
        tags: list[str] | None = None,
        tentativas: int = 3,
    ) -> bool:
        # Quando publicamos via JSON, enviamos um POST para o root URL (ex: https://ntfy.sh)
        url = self.url
        req = urllib.request.Request(url, method="POST")
        req.add_header("Content-Type", "application/json; charset=utf-8")
        self._autenticar(req)

        payload = {
            "topic": self.topico,
            "message": mensagem,
            "title": titulo,
            "priority": prioridade
        }
        if tags:
            payload["tags"] = tags

        dados = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        for tentativa in range(1, tentativas + 1):
            try:
                with urllib.request.urlopen(req, data=dados, timeout=10) as resp:
                    if resp.status in (200, 201):
                        return True
            except urllib.error.URLError as e:
                print(f"[Push] Tentativa {tentativa}/{tentativas} falhou: {e}")
                if tentativa < tentativas:
                    time.sleep(3 * tentativa)
            except Exception as e:
                print(f"[Push] Erro: {e}")
                return False

        return False

    def notificar_inicio(self, pipeline: str):
        emojis = {"boletins": "loudspeaker", "njud": "newspaper", "giro": "microphone"}
        tag = emojis.get(pipeline.lower(), "gear")
        self.enviar(
            mensagem=f"Pipeline iniciado às {datetime.now().strftime('%H:%M:%S')}",
            titulo=f"{pipeline.upper()} — Iniciando",
            prioridade=self.BAIXO,
            tags=[tag],
        )

    def notificar_sucesso(self, pipeline: str, count: int, duracao_s: float):
        emojis = {"boletins": "loudspeaker", "njud": "newspaper", "giro": "microphone"}
        tag = emojis.get(pipeline.lower(), "white_check_mark")
        mins = int(duracao_s // 60)
        segs = int(duracao_s % 60)
        self.enviar(
            mensagem=f"{count} edição(ões) gerada(s) em {mins}min {segs}s.",
            titulo=f"{pipeline.upper()} — Concluído ✅",
            prioridade=self.NORMAL,
            tags=[tag, "white_check_mark"],
        )

    def notificar_erro(self, pipeline: str, erro: str):
        self.enviar(
            mensagem=f"{erro[:300]}\n\nVerifique: modules/agente/agente_ia.log",
            titulo=f"{pipeline.upper()} — ERRO ❌",
            prioridade=self.URGENTE,
            tags=["rotating_light", "x"],
        )

    def notificar_drive_offline(self):
        self.enviar(
            mensagem=(
                f"Google Drive não detectado às {datetime.now().strftime('%H:%M')}.\n"
                "O agente tentará montar automaticamente.\n"
                "Verifique se o Google Drive Desktop está aberto."
            ),
            titulo="Drive Offline ⚠️",
            prioridade=self.ALTO,
            tags=["warning", "floppy_disk"],
        )

    def notificar_relatorio_diario(self, resultados: dict):
        data = datetime.now().strftime("%d/%m/%Y")
        nomes = {"boletins": "Boletins", "njud": "Jornal NJUD", "giro": "Giro"}

        linhas = []
        total_edicoes = 0
        algum_erro = False

        for prog in ["boletins", "njud", "giro"]:
            r = resultados.get(prog, {})
            ok = r.get("ok", False)
            count = r.get("count", 0)
            total_edicoes += count
            status = "✅" if ok else "❌"
            linha = f"{status} {nomes[prog]}: {count} edição(ões)"
            if not ok:
                algum_erro = True
                erro = r.get("erro", "")
                if erro:
                    linha += f"\n   → {erro[:80]}"
            linhas.append(linha)

        conflitos = resultados.get("conflitos_corrigidos", 0)
        if conflitos:
            linhas.append(f"🔧 Tags corrigidas: {conflitos}")

        duracao = resultados.get("duracao_total_s", 0)
        linhas.append(f"⏱ Tempo total: {int(duracao // 60)}min {int(duracao % 60)}s")
        linhas.append(f"🎵 Total: {total_edicoes} edição(ões)")

        self.enviar(
            mensagem="\n".join(linhas),
            titulo=f"Relatório {data} {'⚠️' if algum_erro else '✅'}",
            prioridade=self.ALTO if algum_erro else self.NORMAL,
            tags=["bar_chart", "rotating_light" if algum_erro else "white_check_mark"],
        )
