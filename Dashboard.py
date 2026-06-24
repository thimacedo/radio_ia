import streamlit as st
import yaml
import pathlib
import os
import json
from urllib.parse import urlparse
from dotenv import load_dotenv, set_key
import nest_asyncio

# Tenta importar run_pipeline de core.runner, mas ignora se não existir ainda.
try:
    from core.runner import run_pipeline
except ImportError:
    def run_pipeline(prog_id, logger=print):
        logger(f"⚠️ Atenção: 'run_pipeline' não encontrado em 'core.runner'. Simulando a execução do {prog_id}...")

# Permite loops aninhados para compatibilidade com Streamlit
nest_asyncio.apply()

# Configuração da Página
st.set_page_config(
    page_title="Estúdio Rádio IA - Painel Gerencial", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS para visual "Estúdio de Rádio"
st.markdown("""
<style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    h1, h2, h3 { color: #58a6ff; font-family: sans-serif; }
    .stButton>button { background-color: #238636; color: white; border-radius: 6px; }
    .stTextInput>div>div>input, .stTextArea textarea { background-color: #161b22; color: #c9d1d9; border: 1px solid #30363d; }
    .stSelectbox>div>div>select { background-color: #161b22; color: #c9d1d9; }
    label { color: #8b949e !important; }
    .stAlert { background-color: #161b22; border: 1px solid #30363d; }
</style>
""", unsafe_allow_html=True)

# Caminhos dos arquivos de config
CONFIG_PATH = pathlib.Path("config.yaml")
ENV_PATH = pathlib.Path(".env")
load_dotenv(ENV_PATH)

# -------------------------------------------------------------------
# FUNÇÕES AUXILIARES DE GESTÃO
# -------------------------------------------------------------------

def carregar_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {"emissora": {}, "programas": {}, "agendamentos": {}}

def salvar_config(data):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

def carregar_prompt_txt(caminho):
    path = pathlib.Path(caminho)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""

def salvar_prompt_txt(caminho, texto):
    path = pathlib.Path(caminho)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(texto, encoding="utf-8")


def _http_request(method: str, url: str, payload: dict = None):
    try:
        import requests
        if method.upper() == "GET":
            resp = requests.get(url, timeout=15)
        else:
            resp = requests.post(url, json=payload or {}, timeout=15)
        try:
            data = resp.json()
        except Exception:
            data = {"text": resp.text}
        return resp.status_code, data
    except Exception:
        from urllib.parse import urlparse
        import http.client
        import json as _json

        parsed = urlparse(url)
        conn = http.client.HTTPConnection(parsed.netloc, timeout=15)
        if method.upper() == "GET":
            conn.request("GET", parsed.path)
        else:
            body = _json.dumps(payload or {}).encode("utf-8")
            conn.request("POST", parsed.path, body=body, headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        text = resp.read().decode("utf-8", errors="replace")
        try:
            data = _json.loads(text)
        except Exception:
            data = {"text": text}
        return resp.status, data


# -------------------------------------------------------------------
# BARRA LATERAL (NAVEGAÇÃO)
# -------------------------------------------------------------------

st.sidebar.title("🎙️ Estúdio Rádio IA")
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2933/2933245.png", width=80) # Ícone decorativo

pagina = st.sidebar.radio(
    "Navegação",
    ["🎛️ Produção", "🟢 Aprovação de Áudio", "🕵️ Acompanhamento do Agente", "⚙️ Configurar Programas", "✍️ Estilo Editorial", "🔑 Conexões e API"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
config = carregar_config()
emissora = config.get("emissora", {})
st.sidebar.info(f"**Emissora:** {emissora.get('nome', 'Não configurada')}\n\n**Frequência:** {emissora.get('frequencia', '--')}")

# -------------------------------------------------------------------
# PÁGINA 1: PRODUÇÃO (Execução)
# -------------------------------------------------------------------

if pagina == "🎛️ Produção":
    st.title("🎛️ Painel de Produção")
    st.write("Selecione os programas para processar imediatamente ou visualize o status.")

    programas = config.get("programas", {})
    
    if not programas:
        st.warning("Nenhum programa cadastrado. Vá em 'Configurar Programas' para iniciar.")
    else:
        cols = st.columns(3)
        selecionados = []
        
        # Lista de programas com cards visuais
        for i, (prog_id, info) in enumerate(programas.items()):
            col = cols[i % 3]
            with col.container(border=True):
                # Tenta ler status simples (se existir)
                status = "🔵 Pronto" 
                if st.checkbox(f"**{info.get('nome', prog_id)}**", key=f"chk_{prog_id}"):
                    selecionados.append(prog_id)
                st.caption(f"Entrada: `{info.get('armazenamento', {}).get('entrada', {}).get('caminho', 'N/A')}`")

        st.markdown("---")
        
        if st.button("🚀 Processar Programas Selecionados", type="primary"):
            if not selecionados:
                st.toast("Selecione ao menos um programa!", icon="⚠️")
            else:
                log_container = st.empty()
                log_lines = []

                def logger_ui(msg):
                    log_lines.append(msg)
                    log_container.code("\n".join(log_lines), language="log")

                progress_bar = st.progress(0, text="Iniciando...")
                
                for idx, prog_id in enumerate(selecionados):
                    try:
                        logger_ui(f"▶ INICIANDO: {prog_id}")
                        run_pipeline(prog_id, logger=logger_ui)
                        logger_ui(f"✓ CONCLUÍDO: {prog_id}\n")
                    except Exception as e:
                        logger_ui(f"🚨 ERRO CRÍTICO: {e}")
                    
                    # Atualiza barra de progresso geral
                    progress_bar.progress((idx + 1) / len(selecionados), text=f"Processando {prog_id}...")

                st.toast("Processamento em lote finalizado!", icon="✅")
                st.balloons()

# -------------------------------------------------------------------
# PÁGINA 1.5: ACOMPANHAMENTO DO AGENTE
# -------------------------------------------------------------------

elif pagina == "🕵️ Acompanhamento do Agente":
    st.title("🕵️ Acompanhamento do Agente de IA")
    st.write("Monitore em tempo real as atividades, andamento e logs do agente supervisor da rádio.")

    # Status e Progresso
    status_file = pathlib.Path("modules/agente/agente_status.json")
    log_file = pathlib.Path("modules/agente/agente_ia.log")
    
    status_data = {"status": "Inativo", "progress": 0.0, "step": "Sem atividades recentes.", "last_update": "N/A"}
    if status_file.exists():
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                status_data = json.load(f)
        except Exception:
            pass

    # Layout de Status em Cards
    col1, col2, col3 = st.columns(3)
    
    status_value = status_data.get("status", "Inativo")
    if status_value == "Executando":
        col1.metric("Status Atual", "🏃 Executando", delta="Em progresso")
    elif status_value == "Sucesso":
        col1.metric("Status Atual", "✅ Sucesso", delta="Última execução OK")
    elif status_value == "Erro":
        col1.metric("Status Atual", "🚨 Erro", delta="Verifique os logs", delta_color="inverse")
    else:
        col1.metric("Status Atual", "💤 Inativo", delta="Aguardando gatilho")
        
    col2.metric("Progresso Geral", f"{int(status_data.get('progress', 0.0) * 100)}%")
    col3.metric("Última Atualização", status_data.get("last_update", "N/A"))

    # Barra de progresso visual
    st.markdown("### Andamento da Atividade")
    st.progress(status_data.get("progress", 0.0), text=status_data.get("step", ""))

    st.markdown("---")

    # Controles
    col_btn1, col_btn2 = st.columns([1, 4])
    
    # Executar Agente de IA
    if col_btn1.button("🚀 Iniciar Agente", type="primary", disabled=(status_value == "Executando")):
        st.toast("Disparando o Agente em segundo plano...", icon="🚀")
        try:
            import subprocess
            # Usando python do venv e rodando unbuffered para o log escrever em tempo real
            python_exe = str(pathlib.Path(".venv/Scripts/python.exe").resolve())
            agent_script = str(pathlib.Path("modules/agente/agente_ia.py").resolve())
            
            # Limpa o status antigo para iniciar do zero
            status_data = {"status": "Executando", "progress": 0.05, "step": "Disparando processo do agente...", "last_update": "Agora"}
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(status_data, f, indent=4)
                
            # Executa como processo separado desvinculado (detached)
            if os.name == 'nt':
                # Windows detached process flags
                DETACHED_PROCESS = 0x00000008
                subprocess.Popen(
                    [python_exe, "-u", agent_script, "--once"],
                    creationflags=DETACHED_PROCESS,
                    close_fds=True
                )
            else:
                subprocess.Popen(
                    [python_exe, "-u", agent_script, "--once"],
                    close_fds=True
                )
            st.toast("Agente disparado com sucesso!", icon="✅")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao iniciar o agente: {e}")

    # Forçar Atualização
    if col_btn2.button("🔄 Atualizar Painel"):
        st.rerun()

    # Visualizador de Logs
    st.markdown("### 📋 Logs de Execução Recentes")
    if log_file.exists():
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Exibe as últimas 50 linhas
            recent_logs = "".join(lines[-50:])
            st.code(recent_logs, language="log")
        except Exception as e:
            st.error(f"Erro ao ler os logs locais: {e}")
    else:
        st.info("Nenhum log local gravado ainda pelo agente.")

# PÁGINA 2: APROVAÇÃO DE ÁUDIO
# -------------------------------------------------------------------

elif pagina == "🟢 Aprovação de Áudio":
    st.title("🟢 Aprovação de Áudio")
    st.write("Aprovar gravações clean e iniciar a montagem final no serviço Voice Edit Agent.")

    voice_agent_url = os.getenv("VOICE_AGENT_URL", "http://127.0.0.1:8002").rstrip("/")
    st.info(f"Voice Agent ativo em: {voice_agent_url}")

    def call_voice_agent(method: str, endpoint: str, payload: dict = None):
        url = f"{voice_agent_url}{endpoint}"
        return _http_request(method, url, payload)

    # Inicializa variáveis no session_state
    if "active_job_id" not in st.session_state:
        st.session_state["active_job_id"] = ""
    if "active_job_data" not in st.session_state:
        st.session_state["active_job_data"] = None

    # --- SEÇÃO INTERATIVA ---
    st.subheader("🔍 Carregar Job de Áudio para Edição")
    col1, col2 = st.columns([3, 1])
    with col1:
        job_status_id_input = st.text_input("ID do Job do Fatiador (Claquete)", value=st.session_state["active_job_id"])
    with col2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        buscar = st.button("🔎 Buscar")

    if buscar:
        if not job_status_id_input.strip():
            st.error("Informe o Job ID.")
        else:
            status_code, data = call_voice_agent("GET", f"/voice/status/{job_status_id_input.strip()}")
            if status_code == 200:
                st.session_state["active_job_id"] = job_status_id_input.strip()
                st.session_state["active_job_data"] = data
                st.success("Job carregado com sucesso!")
            else:
                st.error(f"Falha ao obter job (Código {status_code})")
                st.json(data)

    active_data = st.session_state["active_job_data"]
    if active_data:
        st.markdown("---")
        st.markdown(f"### 📋 Editando: `{st.session_state['active_job_id']}`")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Programa", active_data.get("program", "Default").upper())
        c2.metric("Status", active_data.get("status", "desconhecido").upper())
        c3.metric("Fração/Claquete", active_data.get("bulletin_id", "N/A"))

        st.markdown(f"**Caminho Cabeça:** `{active_data.get('cabeca_path')}`")
        if active_data.get("off_path"):
            st.markdown(f"**Caminho OFF:** `{active_data.get('off_path')}`")

        # Exibir link para relatório HTML local
        report_path = active_data.get("report")
        if report_path:
            st.info(f"📄 Relatório de Edição Detalhado disponível em: `{report_path}`")

        issues = active_data.get("issues", [])
        if issues:
            st.markdown("#### ✂️ Selecione os trechos para remoção:")
            
            cabeca_choices = []
            off_choices = []
            
            for idx, issue in enumerate(issues):
                part = issue.get("part", "cabeca")
                text_snippet = issue.get("text", "")
                issue_type = issue.get("type", "desconhecido").replace("_", " ").title()
                severity = issue.get("severity", "ATENCAO")
                start_s = issue.get("start", 0)
                end_s = issue.get("end", 0)
                suggested = issue.get("suggested_cut")
                
                if suggested:
                    # Rótulo amigável
                    label_desc = f"**{issue_type}** ({severity}) em **{part.upper()}** de {start_s:.2f}s a {end_s:.2f}s"
                    st.markdown(label_desc)
                    # Mostrar o trecho repetido ou cortado
                    st.caption(f'Trecho: "{text_snippet}"')
                    
                    # Checkbox para aprovação do corte
                    default_checked = severity == "ALTO" or "retake" in issue_type.lower()
                    checked = st.checkbox("Remover este trecho do áudio final", value=default_checked, key=f"cut_{idx}")
                    
                    if checked:
                        cut_ms = {
                            "start_ms": int(suggested["start"] * 1000),
                            "end_ms": int(suggested["end"] * 1000)
                        }
                        if part == "off":
                            off_choices.append(cut_ms)
                        else:
                            cabeca_choices.append(cut_ms)
                    st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #eee;' />", unsafe_allow_html=True)
                else:
                    st.warning(f"⚠️ **Alerta (Sem corte possível):** {issue_type} às {start_s:.2f}s: \"{text_snippet}\"")

            col_app, col_rej = st.columns(2)
            with col_app:
                if st.button("✅ Aprovar Cortes e Iniciar Montagem", use_container_width=True):
                    payload = {
                        "program": active_data.get("program"),
                        "arquivo_clean": active_data.get("cabeca_path"),
                        "cabeca_path": active_data.get("cabeca_path"),
                        "off_path": active_data.get("off_path"),
                        "cortes": {
                            "cabeca_cuts": cabeca_choices,
                            "off_cuts": off_choices
                        },
                        "job_id": st.session_state["active_job_id"]
                    }
                    with st.spinner("Enviando aprovação..."):
                        status_code, data = call_voice_agent("POST", "/voice/approve", payload)
                        if status_code == 200:
                            st.success(f"Montagem iniciada com sucesso! ID: {data.get('job_id')}")
                            st.session_state["active_job_data"]["status"] = "accepted"
                        else:
                            st.error(f"Erro ao processar aprovação (Código {status_code})")
                            st.json(data)
            with col_rej:
                # Botão simples para rejeitar direto
                motivo_rej = st.text_input("Motivo da rejeição (opcional):", key="rej_motivo")
                if st.button("❌ Rejeitar Áudio Completo", use_container_width=True):
                    payload_rej = {
                        "program": active_data.get("program"),
                        "arquivo_clean": active_data.get("cabeca_path"),
                        "motivo": motivo_rej,
                        "job_id": st.session_state["active_job_id"]
                    }
                    with st.spinner("Rejeitando..."):
                        status_code, data = call_voice_agent("POST", "/voice/reject", payload_rej)
                        if status_code == 200:
                            st.warning("Áudio rejeitado.")
                            st.session_state["active_job_data"]["status"] = "rejected"
                        else:
                            st.error(f"Erro ao rejeitar: {status_code}")
        else:
            st.success("Nenhum problema de locução ou repetição detectado neste áudio!")
            if st.button("✅ Aprovar sem Cortes e Montar", use_container_width=True):
                payload = {
                    "program": active_data.get("program"),
                    "arquivo_clean": active_data.get("cabeca_path"),
                    "cabeca_path": active_data.get("cabeca_path"),
                    "off_path": active_data.get("off_path"),
                    "cortes": {"cabeca_cuts": [], "off_cuts": []},
                    "job_id": st.session_state["active_job_id"]
                }
                status_code, data = call_voice_agent("POST", "/voice/approve", payload)
                if status_code == 200:
                    st.success("Montagem iniciada!")
                else:
                    st.error("Erro ao aprovar")

    st.markdown("---")
    st.subheader("🛠️ Ferramentas Manuais de Fallback")
    
    with st.expander("Aprovar e Montar (Manual com JSON)"):
        with st.form("voice_approval_form"):
            st.subheader("✅ Aprovar e montar manualmente")
            manual_job_id = st.text_input("Job ID (Opcional)", value="", help="ID do Job se já existente.")
            manual_program = st.text_input("Programa", value="", help="ID do programa usado na configuração de áudio e montagem.")
            manual_arquivo_clean = st.text_input("Arquivo clean (Cabeça)", value="", help="Caminho completo do arquivo WAV processado (Cabeça).")
            manual_off_path = st.text_input("Arquivo Off (Opcional)", value="", help="Caminho completo do arquivo WAV processado (OFF).")
            manual_cortes_json = st.text_area("Cortes aprovados (JSON)", value="[]", height=120,
                                      help="Para único: [{\"start_ms\":...}]. Para multipart: {\"cabeca_cuts\": [], \"off_cuts\": []}")
            approve_button = st.form_submit_button("✅ Enviar Aprovação")

            if approve_button:
                try:
                    cortes = json.loads(manual_cortes_json or "[]")
                    payload = {
                        "program": manual_program,
                        "arquivo_clean": manual_arquivo_clean,
                        "cabeca_path": manual_arquivo_clean,
                        "off_path": manual_off_path if manual_off_path.strip() else None,
                        "cortes": cortes,
                    }
                    if manual_job_id.strip():
                        payload["job_id"] = manual_job_id.strip()
                        
                    status_code, data = call_voice_agent("POST", "/voice/approve", payload)
                    if status_code == 200:
                        st.success(f"Montagem iniciada. Job ID: {data.get('job_id')}")
                        st.json(data)
                    else:
                        st.error(f"Falha ao chamar Voice Agent: {status_code}")
                        st.json(data)
                except Exception as e:
                    st.error(f"Erro ao processar aprovação: {e}")

    with st.expander("Rejeitar Gravação Manual"):
        with st.form("voice_rejection_form"):
            rejected_program = st.text_input("Programa (rejeição)", value="")
            rejected_audio = st.text_input("Arquivo clean", value="")
            motivo = st.text_area("Motivo da rejeição", value="", height=120)
            reject_button = st.form_submit_button("❌ Rejeitar")

            if reject_button:
                status_code, data = call_voice_agent("POST", "/voice/reject", {
                    "program": rejected_program,
                    "arquivo_clean": rejected_audio,
                    "motivo": motivo,
                })
                if status_code == 200:
                    st.success(f"Rejeição registrada. Job ID: {data.get('job_id')}")
                    st.json(data)
                else:
                    st.error(f"Falha ao chamar Voice Agent para rejeição: {status_code}")
                    st.json(data)

    with st.expander("Consultar Status Bruto (JSON)"):
        with st.form("voice_status_form"):
            job_status_id = st.text_input("Job ID", value="")
            query_button = st.form_submit_button("🔎 Consultar")

            if query_button:
                if not job_status_id:
                    st.error("Informe o Job ID para consultar o status.")
                else:
                    status_code, data = call_voice_agent("GET", f"/voice/status/{job_status_id}")
                    if status_code == 200:
                        st.success("Status obtido com sucesso")
                        st.json(data)
                    else:
                        st.error(f"Falha na consulta: {status_code}")

# -------------------------------------------------------------------
# PÁGINA 2: CONFIGURAR PROGRAMAS (Pastas e Vozes)
# -------------------------------------------------------------------

elif pagina == "⚙️ Configurar Programas":
    st.title("⚙️ Gerenciamento de Programas")
    st.write("Defina pastas de entrada, saída, vozes e parâmetros de áudio.")

    # Seleciona programa para editar ou criar novo
    programas_existentes = list(config.get("programas", {}).keys())
    novo_prog = st.text_input("Criar Novo Programa (ID)", placeholder="ex: jornal_manha")
    
    selecao = st.selectbox(
        "Ou editar existente:", 
        ["--- Selecione ---"] + programas_existentes
    )

    # Determina qual ID está sendo editado
    prog_id_alvo = novo_prog if novo_prog else (selecao if selecao != "--- Selecione ---" else None)

    if prog_id_alvo:
        st.subheader(f"Editando: {prog_id_alvo}")
        
        # Carrega dados atuais (se houver)
        dados_atuais = config.get("programas", {}).get(prog_id_alvo, {})
        
        with st.form("form_programa"):
            nome_amigavel = st.text_input("Nome do Programa", value=dados_atuais.get("nome", prog_id_alvo))
            
            st.markdown("#### 📁 Pastas")
            col1, col2 = st.columns(2)
            entrada = col1.text_input(
                "Pasta de Entrada (Pautas)", 
                value=dados_atuais.get("armazenamento", {}).get("entrada", {}).get("caminho", ""),
                placeholder="C:/RADIO/Entrada/Jornal"
            )
            saida = col2.text_input(
                "Pasta de Saída (Áudio Final)", 
                value=dados_atuais.get("armazenamento", {}).get("saida", {}).get("caminho", ""),
                placeholder="C:/RADIO/Playlist/Jornal"
            )

            st.markdown("#### 🗣️ Vozes")
            vozes_disponiveis = [
                "pt-BR-FranciscaNeural", "pt-BR-AntonioNeural", 
                "pt-BR-ElzaNeural", "pt-BR-ThalitaNeural", "pt-BR-Antonio"
            ]
            vozes_sel = st.multiselect(
                "Selecione as vozes (ordem importa):",
                vozes_disponiveis,
                default=dados_atuais.get("vozes", {}).get("lista", ["pt-BR-FranciscaNeural"])
            )
            estrategia = st.radio(
                "Estratégia de locução:",
                ["inter_file", "intra_file"],
                format_func=lambda x: "Alternar vozes entre arquivos" if x == "inter_file" else "Diálogo (alternar dentro do arquivo)",
                index=0 if dados_atuais.get("vozes", {}).get("estrategia") == "inter_file" else 1
            )

            st.markdown("#### 🎚️ Áudio")
            duracao_min = st.slider("Duração mínima do áudio (segundos)", 5, 120, 
                                    value=dados_atuais.get("duracao_minima_s", 15))

            submitted = st.form_submit_button("💾 Salvar Programa", type="primary")
            
            if submitted:
                # Monta estrutura para salvar
                novo_programa = {
                    "nome": nome_amigavel,
                    "workspace": f"./modules/{prog_id_alvo}/workspace",
                    "prompt_file": f"./prompts/{prog_id_alvo}.txt",
                    "perfil_mixagem": f"./assets/vht/{prog_id_alvo}/perfil_audio.json",
                    "duracao_minima_s": duracao_min,
                    "vozes": {
                        "estrategia": estrategia,
                        "lista": vozes_sel
                    },
                    "armazenamento": {
                        "entrada": {"tipo": "local", "caminho": entrada},
                        "saida": {"tipo": "local", "caminho": saida}
                    }
                }
                
                # Atualiza config global
                if "programas" not in config: config["programas"] = {}
                config["programas"][prog_id_alvo] = novo_programa
                
                # Garante arquivos de suporte
                pathlib.Path(novo_programa["prompt_file"]).parent.mkdir(parents=True, exist_ok=True)
                if not pathlib.Path(novo_programa["prompt_file"]).exists():
                    pathlib.Path(novo_programa["prompt_file"]).write_text("Escreva aqui o estilo jornalístico...")
                
                salvar_config(config)
                st.success(f"Programa '{nome_amigavel}' salvo com sucesso!")
                st.rerun()
    else:
        st.info("Digite um ID para criar um novo ou selecione um existente.")

# -------------------------------------------------------------------
# PÁGINA 3: ESTILO EDITORIAL (Prompts)
# -------------------------------------------------------------------

elif pagina == "✍️ Estilo Editorial":
    st.title("✍️ Estilo Editorial e Jornalístico")
    st.write("Defina como a IA deve escrever e falar os textos. Isso substitui a edição manual dos arquivos `.txt`.")

    programas = config.get("programas", {})
    prog_sel = st.selectbox("Selecione o Programa:", list(programas.keys()))

    if prog_sel:
        prompt_path = programas[prog_sel].get("prompt_file")
        if prompt_path:
            texto_atual = carregar_prompt_txt(prompt_path)
            
            novo_texto = st.text_area(
                "Instruções para a IA (System Prompt)",
                value=texto_atual,
                height=400,
                help="Diga à IA como agir. Ex: 'Seja formal', 'Use termos esportivos', 'Resuma em 30 segundos'."
            )
            
            col1, col2 = st.columns([1, 4])
            if col1.button("💾 Salvar Estilo"):
                salvar_prompt_txt(prompt_path, novo_texto)
                st.toast("Estilo salvo!", icon="✅")
            
            if col2.button("🔄 Resetar para Padrão"):
                salvar_prompt_txt(prompt_path, "Você é um âncora de rádio objetivo e claro.")
                st.rerun()

# -------------------------------------------------------------------
# PÁGINA 4: CONEXÕES E API (Segredos)
# -------------------------------------------------------------------

elif pagina == "🔑 Conexões e API":
    st.title("🔑 Configurações de Conexão")
    st.write("Configure as chaves de API para Inteligência Artificial e dados de FTP.")
    st.warning("⚠️ Estes dados são sensíveis e ficam salvos no arquivo `.env` local.")

    load_dotenv(ENV_PATH)

    with st.expander("🧠 Inteligência Artificial (LLMs)", expanded=True):
        st.markdown("Configure suas chaves de API. O sistema tentará usar na ordem: Groq -> OpenAI -> Gemini.")
        
        groq_key = st.text_input("Groq API Key", type="password", value=os.getenv("GROQ_API_KEY", ""))
        openai_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
        gemini_key = st.text_input("Gemini API Key", type="password", value=os.getenv("GEMINI_API_KEY", ""))

    with st.expander("📡 FTP (Distribuição de Áudio)"):
        st.markdown("Configure se seus arquivos de áudio finais vão para um servidor FTP.")
        
        ftp_host = st.text_input("Host FTP", value=os.getenv("FTP_HOST", ""))
        ftp_user = st.text_input("Usuário FTP", value=os.getenv("FTP_USER", ""))
        ftp_pass = st.text_input("Senha FTP", type="password", value=os.getenv("FTP_PASS", ""))

    with st.expander("📧 Notificações"):
        st.markdown("Configure para onde enviar alertas de falhas.")
        
        webhook_url = st.text_input("URL do Webhook (Discord/Slack)", value=os.getenv("WEBHOOK_URL", ""))
        smtp_server = st.text_input("Servidor SMTP", value=os.getenv("SMTP_SERVER", ""))
        smtp_pass = st.text_input("Senha SMTP", type="password", value=os.getenv("SMTP_PASS", ""))

    with st.expander("🟢 Voice Edit Agent"):
        st.markdown("Configure o serviço de aprovação de áudio humana e montagem final.")
        voice_agent_url = st.text_input("Voice Agent URL", value=os.getenv("VOICE_AGENT_URL", "http://127.0.0.1:8002"))

    if st.button("🔒 Salvar Credenciais no .env"):
        # Salva apenas se preenchido
        if groq_key: set_key(ENV_PATH, "GROQ_API_KEY", groq_key)
        if openai_key: set_key(ENV_PATH, "OPENAI_API_KEY", openai_key)
        if gemini_key: set_key(ENV_PATH, "GEMINI_API_KEY", gemini_key)
        if ftp_host: set_key(ENV_PATH, "FTP_HOST", ftp_host)
        if ftp_user: set_key(ENV_PATH, "FTP_USER", ftp_user)
        if smtp_pass: set_key(ENV_PATH, "SMTP_PASS", smtp_pass)
        if webhook_url: set_key(ENV_PATH, "WEBHOOK_URL", webhook_url)
        if voice_agent_url: set_key(ENV_PATH, "VOICE_AGENT_URL", voice_agent_url)
        
        st.success("Credenciais salvas com segurança no arquivo .env!")
        st.info("Reinicie o painel para garantir que as mudanças façam efeito.")
