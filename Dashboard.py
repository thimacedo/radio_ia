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
    ["🎛️ Produção", "🟢 Aprovação de Áudio", "⚙️ Configurar Programas", "✍️ Estilo Editorial", "🔑 Conexões e API"],
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
# PÁGINA 2: APROVAÇÃO DE ÁUDIO
# -------------------------------------------------------------------

elif pagina == "🟢 Aprovação de Áudio":
    st.title("🟢 Aprovação de Áudio — Locução Humana")
    st.write("Envie gravações de locução humana, analise erros ou repetições, aprove e inicie a montagem final com trilhas e vinhetas.")

    voice_agent_url = os.getenv("VOICE_AGENT_URL", "http://127.0.0.1:8002").rstrip("/")
    st.info(f"Voice Agent ativo em: {voice_agent_url}")

    def call_voice_agent(method: str, endpoint: str, payload: dict = None):
        url = f"{voice_agent_url}{endpoint}"
        return _http_request(method, url, payload)

    # 1. Enviar Nova Locução
    st.subheader("📤 Enviar Novo Áudio de Locução Humana")
    prog_opcoes = {
        "Giro nas Comarcas": "giro",
        "Notícias do Judiciário (NJUD)": "njud",
        "Boletins Notícias da Hora": "boletins"
    }
    
    col_up1, col_up2 = st.columns([1, 2])
    with col_up1:
        prog_nome = st.selectbox("Selecione o Programa", list(prog_opcoes.keys()))
        prog_id = prog_opcoes[prog_nome]
    with col_up2:
        uploaded_file = st.file_uploader("Selecione o arquivo gravado pelo locutor (.mp3 ou .wav)", type=["mp3", "wav"])

    if uploaded_file is not None:
        if st.button("🚀 Iniciar Análise & Limpeza de Áudio"):
            # Salvar arquivo na pasta inputs/{programa}/
            input_dir = pathlib.Path("inputs") / prog_id
            input_dir.mkdir(parents=True, exist_ok=True)
            dest_path = input_dir / uploaded_file.name
            
            try:
                with open(dest_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success(f"Arquivo salvo localmente em: `{dest_path}`")
                
                # Chamar a API /voice/process
                with st.spinner("Processando áudio (Whisper local & Detecção de Hésitações)..."):
                    status_code, data = call_voice_agent("POST", "/voice/process", {
                        "program": prog_id,
                        "input_path": str(dest_path.resolve()),
                        "auto_approve": False
                    })
                    
                    if status_code == 200:
                        st.success("Áudio enviado com sucesso! Job cadastrado na fila.")
                        st.rerun()
                    else:
                        st.error(f"Erro ao cadastrar processamento na API: {status_code} - {data}")
            except Exception as e:
                st.error(f"Falha ao processar arquivo: {e}")

    st.markdown("---")

    # 2. Exibir Fila de Jobs em Tempo Real
    st.subheader("📋 Fila de Locuções Humana & Status")
    
    try:
        status_code, jobs_dict = call_voice_agent("GET", "/voice/jobs")
        
        if status_code == 200 and jobs_dict:
            # Ordena por atualizado mais recentemente
            sorted_jobs = sorted(jobs_dict.items(), key=lambda x: x[1].get("updated_at", 0), reverse=True)
            
            for job_id, job in sorted_jobs:
                prog = job.get("program", "default").upper()
                status = job.get("status", "desconhecido")
                input_file = pathlib.Path(job.get("input_path", "")).name
                
                # Cores e rótulos
                status_labels = {
                    "awaiting_approval": "🟡 Aguardando Aprovação",
                    "completed": "🟢 Montado com Sucesso",
                    "running": "🔵 Processando...",
                    "failed": "🔴 Falhou",
                    "accepted": "🔵 Aceito, Montando...",
                    "rejected": "⚪ Rejeitado"
                }
                status_label = status_labels.get(status, f"❓ {status}")
                
                with st.expander(f"Job {prog}: {input_file} ({status_label})", expanded=(status == "awaiting_approval")):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"**ID do Job:** `{job_id}`")
                        st.markdown(f"**Áudio Processado:** `{job.get('clean_path')}`")
                        
                        # Exibe relatório HTML se existir
                        report_file = job.get("report")
                        if report_file and os.path.exists(report_file):
                            st.info(f"📄 Relatório de qualidade gerado localmente em: `{report_file}`")
                        
                        # Exibe issues encontradas
                        issues = job.get("issues", [])
                        if issues:
                            st.warning(f"⚠️ **Hésitações/Problemas Detectados ({len(issues)}):**")
                            for issue in issues[:5]:
                                st.write(f"- Tipo: *{issue.get('type')}* | Trecho: \"{issue.get('text')}\"")
                            if len(issues) > 5:
                                st.write(f"*(e mais {len(issues) - 5} outros trechos)*")
                        else:
                            st.success("✨ Nenhuma repetição ou hesitação crítica detectada no áudio.")
                            
                    with col2:
                        st.markdown("**Ações Disponíveis:**")
                        
                        if status == "awaiting_approval":
                            if st.button("✅ Aprovar & Montar", key=f"app_{job_id}"):
                                with st.spinner("Mixando com trilhas e vinhetas..."):
                                    s_code, res = call_voice_agent("POST", "/voice/approve", {
                                        "program": job.get("program"),
                                        "arquivo_clean": job.get("clean_path"),
                                        "cortes": [],
                                        "job_id": job_id
                                    })
                                    if s_code == 200:
                                        st.success("Aprovado! Iniciada montagem em background.")
                                        st.rerun()
                                    else:
                                        st.error(f"Erro: {res}")
                                        
                            if st.button("❌ Rejeitar", key=f"rej_{job_id}"):
                                with st.spinner("Registrando rejeição..."):
                                    s_code, res = call_voice_agent("POST", "/voice/reject", {
                                        "program": job.get("program"),
                                        "arquivo_clean": job.get("clean_path"),
                                        "motivo": "Rejeitado pelo editor humano.",
                                        "job_id": job_id
                                    })
                                    if s_code == 200:
                                        st.warning("Locução Rejeitada.")
                                        st.rerun()
                                    else:
                                        st.error(f"Erro: {res}")
                                        
                        elif status == "completed":
                            final_path = job.get("final_path")
                            if final_path and os.path.exists(final_path):
                                st.success("🎉 Áudio Final Pronto:")
                                st.audio(final_path)
                                with open(final_path, "rb") as f:
                                    st.download_button(
                                        label="📥 Baixar Áudio Final (MP3)",
                                        data=f,
                                        file_name=pathlib.Path(final_path).name,
                                        mime="audio/mp3",
                                        key=f"dl_{job_id}"
                                    )
                            else:
                                st.warning("Áudio final não localizado fisicamente no disco.")
                                
                        elif status in ["running", "accepted"]:
                            st.info("⏳ Processando montagem em segundo plano... Por favor, aguarde.")
                            if st.button("🔄 Atualizar Status", key=f"up_{job_id}"):
                                st.rerun()
                                
                        elif status == "failed":
                            st.error(f"Erro no processamento: {job.get('error')}")
                            
        else:
            st.info("Nenhum áudio de locução humana em andamento ou aguardando aprovação na fila.")
            
    except Exception as e:
        st.error("🔌 Não foi possível conectar ao serviço local Voice Edit Agent.")
        st.warning("Certifique-se de que a API FastAPI está em execução na porta 8002. Para ativá-la, execute no terminal:")
        st.code("uvicorn voice_agent.api:app --host 0.0.0.0 --port 8002")

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
