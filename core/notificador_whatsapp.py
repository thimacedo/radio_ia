"""
core/notificador_whatsapp.py
────────────────────────────
Módulo de notificações WhatsApp para o Agente de IA da Rádio TJRN.

DUAS OPÇÕES DE USO (configure no .env):

  OPÇÃO A — CallMeBot (recomendado para começar, zero infraestrutura):
    Serviço gratuito que entrega mensagens no seu WhatsApp pessoal via API.
    Limite: 150 mensagens/dia (mais que suficiente).
    Setup: 5 minutos, só precisa enviar uma mensagem para ativar.

  OPÇÃO B — Evolution API (recomendado se já tiver Docker):
    Self-hosted, sem limite, sem dependência de terceiros.
    Setup: ~30 minutos com Docker.

Configure no .env:
─────────────────
# Opção A (CallMeBot)
WA_MODO=callmebot
WA_NUMERO=5584999999999          # Seu número com DDI+DDD, sem + e sem espaço
WA_CALLMEBOT_APIKEY=XXXXXXXX    # Chave gerada pelo bot (ver SETUP abaixo)

# Opção B (Evolution API)
WA_MODO=evolution
WA_NUMERO=5584999999999
WA_EVOLUTION_URL=http://localhost:8080
WA_EVOLUTION_INSTANCE=radio-tjrn
WA_EVOLUTION_APIKEY=sua-chave-aqui
"""

import os
import json
import time
import urllib.parse
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


# ─────────────────────────────────────────────
# OPÇÃO A: CALLMEBOT
# ─────────────────────────────────────────────

class CallMeBotNotifier:
    """
    Envia mensagens WhatsApp via CallMeBot.
    Gratuito, sem servidor, funciona com número pessoal.
    Limite: 150 msgs/dia.
    """
    BASE_URL = "https://api.callmebot.com/whatsapp.php"

    def __init__(self):
        self.numero = carregar_env_var("WA_NUMERO")
        self.apikey = carregar_env_var("WA_CALLMEBOT_APIKEY")

        if not self.numero or not self.apikey:
            raise ValueError(
                "[CallMeBot] WA_NUMERO e WA_CALLMEBOT_APIKEY precisam estar no .env\n"
                "Siga o SETUP no topo deste arquivo."
            )

    def enviar(self, mensagem: str) -> bool:
        """Envia mensagem. Retorna True se enviou com sucesso."""
        texto_encoded = urllib.parse.quote(mensagem)
        url = f"{self.BASE_URL}?phone={self.numero}&text={texto_encoded}&apikey={self.apikey}"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RadioTJRN/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                status = resp.status
                corpo = resp.read().decode("utf-8", errors="ignore")
                if status == 200 and "message queued" in corpo.lower():
                    return True
                print(f"[CallMeBot] Resposta inesperada (status {status}): {corpo[:200]}")
                return False
        except urllib.error.URLError as e:
            print(f"[CallMeBot] Erro de rede: {e}")
            return False
        except Exception as e:
            print(f"[CallMeBot] Erro ao enviar: {e}")
            return False


# ─────────────────────────────────────────────
# OPÇÃO B: EVOLUTION API
# ─────────────────────────────────────────────

class EvolutionAPINotifier:
    """
    Envia mensagens via Evolution API self-hosted.
    Sem limite de mensagens, sem dependência de terceiros.
    Requer Docker rodando localmente.
    """

    def __init__(self):
        self.numero    = carregar_env_var("WA_NUMERO")
        self.base_url  = carregar_env_var("WA_EVOLUTION_URL", "http://localhost:8080").rstrip("/")
        self.instance  = carregar_env_var("WA_EVOLUTION_INSTANCE", "radio-tjrn")
        self.apikey    = carregar_env_var("WA_EVOLUTION_APIKEY")

        if not self.numero or not self.apikey:
            raise ValueError(
                "[EvolutionAPI] WA_NUMERO e WA_EVOLUTION_APIKEY precisam estar no .env\n"
                "Siga o SETUP no topo deste arquivo."
            )

    def _post(self, endpoint: str, payload: dict) -> dict | None:
        url = f"{self.base_url}{endpoint}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "apikey": self.apikey,
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            corpo = e.read().decode("utf-8", errors="ignore")
            print(f"[EvolutionAPI] HTTP {e.code}: {corpo[:300]}")
            return None
        except Exception as e:
            print(f"[EvolutionAPI] Erro: {e}")
            return None

    def verificar_conexao(self) -> bool:
        """Verifica se a instância está conectada ao WhatsApp."""
        resultado = self._post(
            f"/instance/connectionState/{self.instance}", {}
        )
        if resultado:
            estado = resultado.get("instance", {}).get("state", "")
            return estado == "open"
        return False

    def enviar(self, mensagem: str) -> bool:
        """Envia mensagem de texto. Retorna True se enviou com sucesso."""
        numero_formatado = self.numero.lstrip("+").replace(" ", "").replace("-", "")

        payload = {
            "number": numero_formatado,
            "text": mensagem
        }
        resultado = self._post(
            f"/message/sendText/{self.instance}",
            payload
        )
        if resultado and resultado.get("key", {}).get("id"):
            return True
        print(f"[EvolutionAPI] Falha ao enviar. Resposta: {resultado}")
        return False


# ─────────────────────────────────────────────
# INTERFACE UNIFICADA
# ─────────────────────────────────────────────

class NotificadorWhatsApp:
    """
    Interface única para envio de notificações.
    Seleciona automaticamente o modo configurado no .env (WA_MODO).
    """

    def __init__(self):
        modo = carregar_env_var("WA_MODO", "callmebot").lower()
        self._modo = modo

        if modo == "evolution":
            self._backend = EvolutionAPINotifier()
        else:
            self._backend = CallMeBotNotifier()

        print(f"[Notificador] Modo ativo: {self._modo.upper()}")

    def enviar(self, mensagem: str, tentativas: int = 3) -> bool:
        """Envia mensagem com retentativas automáticas."""
        for i in range(tentativas):
            if self._backend.enviar(mensagem):
                return True
            if i < tentativas - 1:
                espera = 5 * (i + 1)
                print(f"[Notificador] Tentativa {i+1}/{tentativas} falhou. Aguardando {espera}s...")
                time.sleep(espera)
        print(f"[Notificador] FALHA: mensagem não enviada após {tentativas} tentativas.")
        return False

    def notificar_inicio(self, pipeline: str):
        emoji = {"boletins": "📻", "njud": "📰", "giro": "🎙️"}.get(pipeline.lower(), "⚙️")
        msg = (
            f"{emoji} *Rádio TJRN — Início*\n"
            f"Pipeline: *{pipeline.upper()}*\n"
            f"Hora: {datetime.now().strftime('%H:%M:%S')}"
        )
        self.enviar(msg)

    def notificar_sucesso(self, pipeline: str, count: int, duracao_s: float):
        emoji = {"boletins": "📻", "njud": "📰", "giro": "🎙️"}.get(pipeline.lower(), "✅")
        msg = (
            f"{emoji} *Rádio TJRN — Produção Concluída*\n"
            f"Pipeline: *{pipeline.upper()}*\n"
            f"Edições geradas: *{count}*\n"
            f"Duração: {int(duracao_s // 60)}min {int(duracao_s % 60)}s\n"
            f"Hora: {datetime.now().strftime('%H:%M:%S')}"
        )
        self.enviar(msg)

    def notificar_erro(self, pipeline: str, erro: str):
        msg = (
            f"❌ *Rádio TJRN — ERRO*\n"
            f"Pipeline: *{pipeline.upper()}*\n"
            f"Erro: {erro[:200]}\n"
            f"Hora: {datetime.now().strftime('%H:%M:%S')}\n"
            f"_Verifique o log em modules/agente/agente_ia.log_"
        )
        self.enviar(msg)

    def notificar_relatorio_diario(self, resultados: dict):
        """
        resultados = {
            "boletins": {"ok": True, "count": 8, "duracao_s": 240},
            "njud":     {"ok": True, "count": 2, "duracao_s": 180},
            "giro":     {"ok": False, "count": 0, "duracao_s": 0, "erro": "Timeout TTS"},
            "conflitos_corrigidos": 1,
            "duracao_total_s": 480,
        }
        """
        data = datetime.now().strftime("%d/%m/%Y")
        linhas = [f"📊 *Rádio TJRN — Relatório {data}*\n"]

        emojis = {"boletins": "📻", "njud": "📰", "giro": "🎙️"}
        nomes  = {"boletins": "Boletins", "njud": "Jornal NJUD", "giro": "Giro nas Comarcas"}

        total_edicoes = 0
        for prog in ["boletins", "njud", "giro"]:
            r = resultados.get(prog, {})
            ok = r.get("ok", False)
            count = r.get("count", 0)
            total_edicoes += count
            status = "✅" if ok else "❌"
            emoji = emojis[prog]
            nome = nomes[prog]
            linha = f"{emoji} {nome}: {status}"
            if ok and count:
                duracao = r.get("duracao_s", 0)
                linha += f" — {count} edição(ões) em {int(duracao // 60)}min"
            elif not ok:
                erro = r.get("erro", "")
                if erro:
                    linha += f"\n   ↳ _{erro[:80]}_"
            linhas.append(linha)

        conflitos = resultados.get("conflitos_corrigidos", 0)
        if conflitos:
            linhas.append(f"\n🔧 Conflitos de tag corrigidos: {conflitos}")

        duracao_total = resultados.get("duracao_total_s", 0)
        linhas.append(f"\n⏱ Tempo total: {int(duracao_total // 60)}min {int(duracao_total % 60)}s")
        linhas.append(f"🎵 Total de edições: {total_edicoes}")

        self.enviar("\n".join(linhas))

    def notificar_drive_offline(self):
        msg = (
            "⚠️ *Rádio TJRN — Drive Offline*\n"
            f"Google Drive não detectado às {datetime.now().strftime('%H:%M')}.\n"
            "O agente tentará montar automaticamente.\n"
            "_Verifique se o Google Drive Desktop está aberto._"
        )
        self.enviar(msg)


if __name__ == "__main__":
    print("=== Teste do Notificador WhatsApp ===\n")

    try:
        n = NotificadorWhatsApp()

        print("Enviando mensagem de teste...")
        ok = n.enviar("✅ Rádio TJRN — Notificador configurado com sucesso!")
        print(f"Resultado: {'ENVIADO' if ok else 'FALHOU'}\n")

        if ok:
            print("Enviando relatório simulado...")
            n.notificar_relatorio_diario({
                "boletins": {"ok": True,  "count": 8, "duracao_s": 230},
                "njud":     {"ok": True,  "count": 2, "duracao_s": 175},
                "giro":     {"ok": False, "count": 0, "duracao_s": 0, "erro": "Timeout Edge TTS na fala 3"},
                "conflitos_corrigidos": 1,
                "duracao_total_s": 430,
            })
            print("Relatório enviado!\n")

    except ValueError as e:
        print(f"CONFIGURAÇÃO INCOMPLETA:\n{e}")
        print("\nAdicione as variáveis ao seu .env e tente novamente.")
