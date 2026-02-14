import streamlit as st
import pandas as pd
import os
from sqlalchemy import create_engine, text
from datetime import datetime, time, timedelta
from io import BytesIO
from fpdf import FPDF
import time as time_module

# --- CONFIGURAÇÕES DE MARCA ---
NOME_SISTEMA = "Up 2 Today"
SLOGAN = "Seu Controle. Nossa Prioridade."
LOGO_URL = "https://i.postimg.cc/85HwzdmP/logo-png.png"
ORDEM_AREAS = ["Motorista", "Borracharia", "Mecânica", "Elétrica", "Chapeamento", "Limpeza"]
LISTA_TURNOS = ["Não definido", "Dia", "Noite"]

COR_AZUL = "#1b224c" 
COR_VERDE = "#31ad64"
COR_FUNDO = "#f4f7f6"

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title=f"{NOME_SISTEMA} - Tudo em Dia", layout="wide", page_icon="🛠️")

# --- CSS FINAL: LOGIN AZUL, ABAS VERDES E SETA CINZA ---
st.markdown(f"""
    <style>
    /* FUNDOS E SIDEBAR */
    html, body, [data-testid="stAppViewContainer"], .stApp {{ background-color: #FFFFFF !important; }}
    [data-testid="stSidebar"] {{ background-color: #DFDFDF !important; }}

    /* FLECHINHA DA SIDEBAR EM CINZA */
    [data-testid="stSidebarCollapsedControl"] svg, 
    button[data-testid="stBaseButton-headerNoPadding"] svg {{
        fill: #808080 !important;
        color: #808080 !important;
    }}

    /* TEXTOS GERAIS */
    p, label, span, div, .stMarkdown, [data-testid="stText"] {{ color: #31333F !important; }}

    /* TODOS OS BOTÕES: Azul Marinho (Inclui o Login e Sair) */
    button[kind="primary"], button[kind="secondary"], button {{
        background-color: #1b224c !important;
        border: 2px solid #31ad64 !important;
        border-radius: 8px !important;
        color: #FFFFFF !important;
    }}

    /* DESTAQUE EXCLUSIVO DAS ABAS (DENTRO DE COLUNAS) */
    [data-testid="stHorizontalBlock"] button[kind="primary"] {{
        background-color: #31ad64 !important;
        border: 2px solid #1b224c !important;
    }}

    /* Texto branco em todos os botões */
    button p, button span, button div {{ color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important; }}

    /* CALENDÁRIO: Fundo Verde para Seleção */
    div[data-baseweb="calendar"] [aria-selected="true"],
    div[data-baseweb="calendar"] [class*="Selected"] {{
        background-color: #31ad64 !important;
        background: #31ad64 !important;
    }}

    /* LOGOTIPO E RÁDIO */
    div[data-testid="stRadio"] > div {{ display: flex; justify-content: center; background-color: #ffffff; padding: 10px; border-radius: 10px; border: 1px solid #e0e0e0; }}
    .logo-u {{ color: #1b224c !important; }}
    .logo-2t {{ color: #31ad64 !important; }}
    </style>
""", unsafe_allow_html=True)

# --- 2. FUNÇÕES DE BANCO ---
@st.cache_resource
def get_engine():
    db_url = st.secrets.get("database_url") or os.environ.get("database_url", "postgresql://neondb_owner:npg_WRMhXvJVY79d@ep-lucky-sound-acy7xdyi-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require")
    return create_engine(db_url.replace("postgres://", "postgresql://", 1), pool_pre_ping=True)

def inicializar_banco():
    engine = get_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE IF NOT EXISTS tarefas (id SERIAL PRIMARY KEY, data TEXT, executor TEXT, prefixo TEXT, inicio_disp TEXT, fim_disp TEXT, descricao TEXT, area TEXT, turno TEXT, realizado BOOLEAN DEFAULT FALSE, id_chamado INTEGER, origem TEXT, empresa_id TEXT)"))
            conn.execute(text("CREATE TABLE IF NOT EXISTS chamados (id SERIAL PRIMARY KEY, motorista TEXT, prefixo TEXT, descricao TEXT, data_solicitacao TEXT, status TEXT DEFAULT 'Pendente', empresa_id TEXT)"))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS empresa (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    senha TEXT NOT NULL,
                    data_cadastro DATE DEFAULT CURRENT_DATE,
                    status_assinatura TEXT DEFAULT 'trial',
                    data_expiracao DATE DEFAULT (CURRENT_DATE + INTERVAL '7 days')
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    login TEXT NOT NULL,
                    senha TEXT NOT NULL,
                    perfil TEXT DEFAULT 'motorista',
                    empresa_id TEXT NOT NULL,
                    UNIQUE(login, empresa_id)
                )
            """))
            conn.commit()
    except Exception as e:
        st.error(f"Erro ao inicializar banco: {e}")

# ... (Funções de PDF e Excel permanecem iguais)
def to_excel_native(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Manutencoes')
    return output.getvalue()

@st.cache_data(show_spinner=False)
def gerar_pdf_periodo(df_periodo, data_inicio, data_fim):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 22)
    pdf.set_text_color(27, 34, 76) 
    pdf.cell(6, 10, "U", ln=0)
    pdf.set_text_color(49, 173, 100) 
    pdf.cell(40, 10, "2T", ln=0)
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(144, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=1, align="R")
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(27, 34, 76)
    pdf.cell(190, 10, f"RELATORIO DE MANUTENCAO - {NOME_SISTEMA.upper()}", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(190, 8, f"Periodo: {data_inicio.strftime('%d/%m/%Y')} ate {data_fim.strftime('%d/%m/%Y')}", ln=True, align="C")
    pdf.ln(5)
    for d_process in sorted(df_periodo['data'].unique(), reverse=True):
        d_formatada = pd.to_datetime(d_process).strftime('%d/%m/%Y')
        pdf.set_font("Arial", "B", 11); pdf.set_fill_color(240, 240, 240)
        pdf.cell(190, 8, f" DATA: {d_formatada}", ln=True, fill=True)
        for area in ORDEM_AREAS:
            df_area = df_periodo[(df_periodo['data'] == d_process) & (df_periodo['area'] == area)]
            if not df_area.empty:
                pdf.set_font("Arial", "B", 9); pdf.set_text_color(49, 173, 100)
                pdf.cell(190, 7, f" Setor: {area}", ln=True)
                pdf.set_font("Arial", "B", 8); pdf.set_text_color(50); pdf.set_fill_color(230, 230, 230)
                pdf.cell(20, 6, "Prefixo", 1, 0, 'C', True)
                pdf.cell(35, 6, "Executor", 1, 0, 'C', True)
                pdf.cell(40, 6, "Disponibilidade", 1, 0, 'C', True)
                pdf.cell(95, 6, "Descricao", 1, 1, 'C', True)
                pdf.set_font("Arial", "", 7); pdf.set_text_color(0)
                for _, row in df_area.iterrows():
                    pdf.cell(20, 6, str(row['prefixo']), 1, 0, 'C')
                    pdf.cell(35, 6, str(row['executor'])[:20], 1, 0, 'C')
                    pdf.cell(40, 6, f"{row['inicio_disp']} - {row['fim_disp']}", 1, 0, 'C')
                    pdf.cell(95, 6, str(row['descricao'])[:75], 1, 1, 'L')
                pdf.ln(2)
    return pdf.output(dest='S').encode('latin-1')

# --- 3. LÓGICA DE LOGIN ---
if "logado" not in st.session_state: st.session_state["logado"] = False

if not st.session_state["logado"]:
    _, col_login, _ = st.columns([1.2, 1, 1.2])
    with col_login:
        placeholder_topo = st.empty()
        placeholder_topo.markdown(f"<h1 style='text-align: center; margin-bottom: 0;'><span class='logo-u'>U</span><span class='logo-2t'>2T</span></h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; font-style: italic; color: #555; margin-top: 0;'>{SLOGAN}</p>", unsafe_allow_html=True)
        aba = st.radio("Selecione uma opção", ["Acessar", "Criar Conta"], horizontal=True, label_visibility="collapsed")
        
        if aba == "Acessar":
            with st.container(border=True):
                user_input = st.text_input("E-mail ou Usuário", key="u_log").lower()
                pw_input = st.text_input("Senha", type="password", key="p_log")
                if st.button(f"Acessar Painel {NOME_SISTEMA}", use_container_width=True, type="primary"):
                    engine = get_engine()
                    inicializar_banco()
                    masters = {
                        "bruno": {"pw": "master789", "perfil": "admin", "empresa": "U2T_MATRIZ", "login_original": "bruno"},
                        "motorista": {"pw": "12345", "perfil": "motorista", "empresa": "U2T_MATRIZ", "login_original": "motorista_padrao"}
                    }
                    logado_agora = False
                    if user_input in masters and masters[user_input]["pw"] == pw_input:
                        st.session_state.update({"logado": True, "perfil": masters[user_input]["perfil"], "empresa": masters[user_input]["empresa"], "usuario_ativo": masters[user_input]["login_original"]})
                        logado_agora = True
                    else:
                        with engine.connect() as conn:
                            res = conn.execute(text("SELECT nome, email, senha, data_expiracao, status_assinatura FROM empresa WHERE LOWER(email) = :u OR LOWER(nome) = :u"), {"u": user_input}).fetchone()
                            if res and res[2] == pw_input:
                                if res[3] < datetime.now().date() and res[4] != 'ativo':
                                    st.error(f"⚠️ Teste expirado em {res[3].strftime('%d/%m/%Y')}.")
                                else:
                                    st.session_state.update({"logado": True, "perfil": "admin", "empresa": res[0], "usuario_ativo": res[0]})
                                    logado_agora = True
                            else:
                                u_equipe = conn.execute(text("SELECT login, senha, perfil, empresa_id FROM usuarios WHERE LOWER(login) = :u"), {"u": user_input}).fetchone()
                                if u_equipe and u_equipe[1] == pw_input:
                                    st.session_state.update({"logado": True, "perfil": u_equipe[2], "empresa": u_equipe[3], "usuario_ativo": u_equipe[0]})
                                    logado_agora = True
                    if logado_agora: st.rerun()
                    else: st.error("Dados incorretos.")
        else:
            with st.container(border=True):
                st.markdown(f"<h4 style='color:{COR_AZUL}'>🚀 7 Dias Grátis</h4>", unsafe_allow_html=True)
                n_emp = st.text_input("Nome da Empresa")
                n_ema = st.text_input("E-mail Corporativo")
                n_sen = st.text_input("Senha", type="password")
                if st.button("Criar minha conta agora", use_container_width=True, type="primary"):
                    if n_emp and n_ema and n_sen:
                        try:
                            engine = get_engine(); inicializar_banco()
                            expira = datetime.now().date() + timedelta(days=7)
                            with engine.connect() as conn:
                                conn.execute(text("INSERT INTO empresa (nome, email, senha, data_expiracao) VALUES (:n, :e, :s, :d)"), {"n": n_emp, "e": n_ema, "s": n_sen, "d": expira})
                                conn.commit()
                            st.success("✅ Conta criada!")
                        except: st.error("E-mail já cadastrado.")

else:
    engine = get_engine()
    emp_id = st.session_state["empresa"]
    usuario_logado = st.session_state["usuario_ativo"]
    
    # --- DEFINIÇÃO DINÂMICA DE OPÇÕES (Aba Master para o Bruno) ---
    if st.session_state["perfil"] == "motorista":
        opcoes = ["✍️ Abrir Solicitação", "📜 Status"]
    else:
        opcoes = ["📅 Agenda Principal", "📋 Cadastro Direto", "📥 Chamados Oficina", "📊 Indicadores", "👥 Minha Equipe"]
        if usuario_logado == "bruno":
            opcoes.append("👑 Gestão Master")

    if "opcao_selecionada" not in st.session_state: st.session_state.opcao_selecionada = opcoes[0]

    # --- NAVEGAÇÃO LATERAL ---
    with st.sidebar:
        st.image(LOGO_URL, width=150)
        st.divider()
        escolha_sidebar = st.radio("NAVEGAÇÃO", opcoes, index=opcoes.index(st.session_state.opcao_selecionada), key="nav_radio")
        st.session_state.opcao_selecionada = escolha_sidebar
        st.divider()
        st.write(f"🏢 {emp_id}")
        if st.button("Sair da Conta", type="primary", use_container_width=True): 
            st.session_state.clear()
            st.rerun()

    # --- BOTÕES DE ABA NO TOPO ---
    cols = st.columns(len(opcoes))
    for i, nome in enumerate(opcoes):
        if cols[i].button(nome, key=f"btn_{i}", use_container_width=True, type="primary" if nome == st.session_state.opcao_selecionada else "secondary"):
            st.session_state.opcao_selecionada = nome
            st.rerun()

    st.divider()
    aba_ativa = st.session_state.opcao_selecionada

    # --- CONTEÚDO DAS PÁGINAS (Resumo das principais) ---
    if aba_ativa == "📅 Agenda Principal":
        st.subheader("📅 Agenda Principal")
        # (Seu código original da Agenda Principal continua aqui...)
        df_a = pd.read_sql(text("SELECT * FROM tarefas WHERE empresa_id = :eid ORDER BY data DESC"), engine, params={"eid": emp_id})
        st.dataframe(df_a, use_container_width=True)

    elif aba_ativa == "👑 Gestão Master":
        st.subheader("👑 Painel de Gestão Master (Exclusivo Bruno)")
        st.info("Aqui você gerencia os pagamentos e prazos de todas as empresas cadastradas.")
        
        df_empresas = pd.read_sql(text("SELECT id, nome, email, data_cadastro, data_expiracao, status_assinatura FROM empresa ORDER BY id DESC"), engine)
        
        # Editor para ativar/desativar empresas manualmente
        for index, row in df_empresas.iterrows():
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                c1.write(f"**Empresa:** {row['nome']}")
                c1.write(f"**E-mail:** {row['email']}")
                c2.write(f"📅 Cadastro: {row['data_cadastro']}")
                c2.write(f"⌛ Expira: {row['data_expiracao']}")
                c3.write(f"Status: `{row['status_assinatura']}`")
                
                if row['status_assinatura'] != 'ativo':
                    if c4.button("✅ Ativar", key=f"at_{row['id']}"):
                        nova_data = datetime.now().date() + timedelta(days=365) # Ativa por 1 ano
                        with engine.connect() as conn:
                            conn.execute(text("UPDATE empresa SET status_assinatura = 'ativo', data_expiracao = :d WHERE id = :id"), {"d": nova_data, "id": row['id']})
                            conn.commit()
                        st.success(f"{row['nome']} ativada!")
                        st.rerun()
                else:
                    if c4.button("🚫 Bloquear", key=f"bl_{row['id']}"):
                        with engine.connect() as conn:
                            conn.execute(text("UPDATE empresa SET status_assinatura = 'bloqueado' WHERE id = :id"), {"id": row['id']})
                            conn.commit()
                        st.rerun()

    # (As outras abas: Cadastro Direto, Chamados, Indicadores, Minha Equipe continuam abaixo iguais ao seu original)
    elif aba_ativa == "👥 Minha Equipe":
        st.subheader("👥 Gestão de Equipe")
        # (Seu código original de Minha Equipe aqui...)
