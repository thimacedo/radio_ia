"""
core/notificador.py
───────────────────
Notificações push para o Agente de IA da Rádio TJRN via ntfy.

COMO FUNCIONA:
  O ntfy é um servidor pub/sub HTTP. O agente publica uma mensagem
  num "tópico" (ex: radio-tjrn). O app no celular, inscrito nesse
  tópico, recebe a notificação instantaneamente.
  Sem WhatsApp, sem bot, sem conta, sem API key.

SETUP (uma vez só — ~10 minutos):
─────────────────────────────────
  1. Suba o servidor ntfy (Docker):
       Copie docker-compose-ntfy.yml para C:\\ntfy\\docker-compose.yml
       Abra o terminal nessa pasta e execute: docker compose up -d

  2. Instale o app no celular:
       Android: https://play.google.com/store/apps/details?id=io.heckel.ntfy
       iOS:     https://apps.apple.com/app/ntfy/id1625396347

  3. Conecte o app ao servidor local:
       No app → ícone + → "Change default server"
       → Digite: http://SEU_IP_LOCAL:2586
       (Para saber seu IP: no terminal Windows, rode "ipconfig",
        procure "Endereço IPv4" da sua rede, ex: 192.168.1.10)

  4. Inscreva-se no tópico:
       No app → ícone + → "Subscribe to topic" → "radio-tjrn"

  5. Adicione no .env:
       NTFY_URL=http://192.168.1.10:2586   ← seu IP local
       NTFY_TOPIC=radio-tjrn

  6. Teste:
       python core/notificador.py

CONFIGURAÇÃO NO .env:
─────────────────────
  NTFY_URL=http://192.168.1.10:2586
  NTFY_TOPIC=radio-tjrn

  # Opcional: proteger o tópico com senha (recomendado)
  NTFY_USUARIO=admin
  NTFY_SENHA=sua-senha-aqui
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path


# ─────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────

def _ler_env(chave: str, fallback: str = "") -> str:
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for linha in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in linha and not linha.strip().startswith("#"):
                k, _, v = linha.partition("=")
                if k.strip() == chave:
                    return v.strip().strip('"').strip("'")
    import os
    return os.environ.get(chave, fallback)


# ─────────────────────────────────────────────
# CLIENTE NTFY
# ─────────────────────────────────────────────

class Notificador:
    """
    Envia push notifications via ntfy self-hosted.
    100% stdlib Python — sem dependências externas.
    """

    # Prioridades do ntfy
    URGENTE = "urgent"   # som alto + sem DND
    ALTO    = "high"     # som normal
    NORMAL  = "default"  # silencioso
    BAIXO   = "low"      # silencioso, agrupa

    def __init__(self):
        self.url     = _ler_env("NTFY_URL", "http://localhost:2586").rstrip("/")
        self.topico  = _ler_env("NTFY_TOPIC", "radio-tjrn")
        self.usuario = _ler_env("NTFY_USUARIO", "")
        self.senha   = _ler_env("NTFY_SENHA", "")

        if not self.url:
            raise ValueError(
                "[Notificador] NTFY_URL não configurado no .env\n"
                "Exemplo: NTFY_URL=http://192.168.1.10:2586"
            )

    def _autenticar(self, req: urllib.request.Request):
        """Adiciona autenticação Basic se configurada."""
        if self.usuario and self.senha:
            import base64
            credencial = base64.b64encode(
                f"{self.usuario}:{self.senha}".encode()
            ).decode()
            req.add_header("Authorization", f"Basic {credencial}")

    def enviar(
        self,
        mensagem: str,
        titulo: str = "Rádio TJRN",
        prioridade: str = "default",
        tags: list[str] | None = None,
        tentativas: int = 3,
    ) -> bool:
        """
        Envia uma notificação push.

        Args:
            mensagem:   Corpo da notificação.
            titulo:     Título exibido no celular.
            prioridade: 'urgent' | 'high' | 'default' | 'low'
            tags:       Emojis/ícones (ex: ['white_check_mark', 'radio'])
                        Lista completa: https://docs.ntfy.sh/emojis/
            tentativas: Retentativas automáticas em caso de falha.
        """
        url = f"{self.url}/{self.topico}"
        req = urllib.request.Request(url, method="POST")
        req.add_header("Content-Type", "text/plain; charset=utf-8")
        req.add_header("Title",    titulo)
        req.add_header("Priority", prioridade)
        if tags:
            req.add_header("Tags", ",".join(tags))
        self._autenticar(req)

        dados = mensagem.encode("utf-8")

        for tentativa in range(1, tentativas + 1):
            try:
                with urllib.request.urlopen(req, data=dados, timeout=10) as resp:
                    if resp.status in (200, 201):
                        return True
                    print(f"[Notificador] Status inesperado: {resp.status}")
                    return False
            except urllib.error.URLError as e:
                print(f"[Notificador] Tentativa {tentativa}/{tentativas} falhou: {e}")
                if tentativa < tentativas:
                    time.sleep(3 * tentativa)
            except Exception as e:
                print(f"[Notificador] Erro: {e}")
                return False

        return False

    # ─────────────────────────────────────────────
    # MÉTODOS SEMÂNTICOS (chamados pelo agente)
    # ─────────────────────────────────────────────

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
                f"Google Drive (H:) não detectado às {datetime.now().strftime('%H:%M')}.\n"
                "O agente tentará montar automaticamente.\n"
                "Verifique se o Google Drive Desktop está aberto."
            ),
            titulo="Drive Offline ⚠️",
            prioridade=self.ALTO,
            tags=["warning", "floppy_disk"],
        )

    def notificar_relatorio_diario(self, resultados: dict):
        """
        resultados = {
            "boletins": {"ok": True,  "count": 8, "duracao_s": 240},
            "njud":     {"ok": True,  "count": 2, "duracao_s": 175},
            "giro":     {"ok": False, "count": 0, "duracao_s": 0, "erro": "Timeout TTS"},
            "conflitos_corrigidos": 1,
            "duracao_total_s": 480,
        }
        """
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


# ─────────────────────────────────────────────
# INTEGRAÇÃO COM agente_ia.py
# ─────────────────────────────────────────────
#
# Substitua o bloco do notificador_whatsapp por:
#
#   try:
#       from core.notificador import Notificador
#       notificador = Notificador()
#       NOTIF_ATIVO = True
#   except Exception as e:
#       print(f"[AVISO] Notificador indisponível: {e}")
#       NOTIF_ATIVO = False
#
# E nos pontos de evento:
#
#   if NOTIF_ATIVO: notificador.notificar_drive_offline()
#   if NOTIF_ATIVO: notificador.notificar_relatorio_diario({...})


# ─────────────────────────────────────────────
# TESTE RÁPIDO
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Teste do Notificador ntfy ===\n")

    try:
        n = Notificador()
        print(f"Servidor: {n.url}")
        print(f"Tópico:   {n.topico}\n")

        print("1. Enviando notificação de teste...")
        ok = n.enviar(
            mensagem="Notificador configurado e funcionando!",
            titulo="Rádio TJRN — Teste ✅",
            prioridade=Notificador.ALTO,
            tags=["white_check_mark", "radio"],
        )
        print(f"   Resultado: {'ENVIADO ✅' if ok else 'FALHOU ❌'}\n")

        if ok:
            print("2. Enviando relatório simulado...")
            n.notificar_relatorio_diario({
                "boletins": {"ok": True,  "count": 8,  "duracao_s": 230},
                "njud":     {"ok": True,  "count": 2,  "duracao_s": 175},
                "giro":     {"ok": False, "count": 0,  "duracao_s": 0,
                             "erro": "Timeout Edge TTS na fala 3"},
                "conflitos_corrigidos": 1,
                "duracao_total_s": 430,
            })
            print("   Relatório enviado ✅")

    except ValueError as e:
        print(f"CONFIGURAÇÃO INCOMPLETA:\n{e}")
        print("\nAdicione NTFY_URL e NTFY_TOPIC no .env e tente novamente.")
    except Exception as e:
        print(f"ERRO: {e}")
        print("Verifique se o Docker está rodando: docker ps")
