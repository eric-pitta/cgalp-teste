import streamlit as st
import os

# Configuração Global (Única vez)
st.set_page_config(page_title="Central de Monitoramento CGALP", layout="wide", page_icon="📊")

# --- INJEÇÃO DE CSS TECH PREMIUM ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
    
    html, body, [data-testid="stSidebar"] {
        font-family: 'Inter', sans-serif;
        background-color: #fcfcfc;
    }

    /* Cabeçalho Principal */
    .main-title {
        text-align: center;
        padding: 20px 0 10px 0;
        color: #113359 !important;
        font-weight: 900;
        letter-spacing: -1.5px;
    }

    /* Títulos de Seção com Gradiente */
    .section-header {
        font-size: 1.6rem;
        font-weight: 900;
        background: linear-gradient(90deg, #113359 0%, #5CA0D3 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding-bottom: 10px;
        margin-top: 2.5rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #f1f5f9;
    }

    /* Cabeçalho de Tabela Estilo SaaS com Gradiente */
    .table-header-bar {
        background: linear-gradient(135deg, #113359 0%, #5CA0D3 100%);
        color: white;
        padding: 12px 18px;
        border-radius: 12px 12px 0 0;
        font-weight: 700;
        font-size: 1.1rem;
        display: flex;
        align-items: center;
        gap: 12px;
        margin-top: 30px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    /* Ajuste da Tabela para encaixar na barra */
    .stDataFrame {
        border: none !important;
        border-radius: 0 0 12px 12px !important;
        overflow: hidden;
        margin-top: -1px !important;
    }

    /* Cartões de Métricas Estilo SaaS */
    .metric-card {
        background: #ffffff;
        padding: 25px 15px;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        position: relative;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
        text-align: center;
        transition: all 0.3s ease;
    }
    .metric-card::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 5px;
        background: linear-gradient(135deg, #113359 0%, #5CA0D3 100%);
        border-radius: 16px 16px 0 0;
    }
    .metric-card:hover {
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        transform: translateY(-5px);
    }
    .metric-label {
        font-size: 0.75rem;
        color: #94a3b8;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 5px;
    }
    .metric-value {
        font-size: 2.2rem;
        color: #0f172a;
        font-weight: 900;
    }

    /* Sidebar e Filtros */
    [data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }
    
    /* Estilização das Tags do Multiselect (Filtro de Ano) */
    span[data-baseweb="tag"] {
        background-color: #113359 !important;
        border-radius: 4px !important;
    }
    span[data-baseweb="tag"] span {
        color: white !important;
    }

    /* Botões Laterais */
    div.stButton > button {
        background: linear-gradient(135deg, #113359 0%, #5CA0D3 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        width: 100%;
    }
    div.stButton > button:hover {
        opacity: 0.9;
        color: white;
    }

    /* Status Progress Board */
    .status-item { margin-bottom: 20px; padding: 15px; background: white; border-radius: 12px; border: 1px solid #f1f5f9; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    .status-label-row { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 0.95rem; font-weight: 700; color: #1e293b; text-transform: uppercase; }
    .status-bar-bg { background: #e2e8f0; border-radius: 10px; height: 12px; width: 100%; overflow: hidden; }
    .status-bar-fill { height: 100%; border-radius: 10px; transition: width 1s ease-in-out; }
    </style>
""", unsafe_allow_html=True)

# --- MENU LATERAL UNIFICADO ---
with st.sidebar:
    if os.path.exists("logo.png"):
        side_col1, side_col2, side_col3 = st.columns([1, 2, 1])
        with side_col2: st.image("logo.png", width=80)
        st.write("")
    
    st.header("🔍 Painel de Controle")
    
    # Seletor de Dashboard no TOPO
    pagina = st.selectbox(
        "Selecione o Painel:",
        ["Câmara Federal - Deputados", "CMRJ - Indicações Legislativas", "CMRJ - Solicitações Legislativas"]
    )
    st.divider()

# --- CARREGAMENTO DINÂMICO ---
if pagina == "Câmara Federal - Deputados":
    with open("dash_federal.py", "r", encoding="utf-8") as f:
        code = f.read()
        exec(code)

elif pagina == "CMRJ - Indicações Legislativas":
    with open("dash_cmrj.py", "r", encoding="utf-8") as f:
        code = f.read()
        exec(code)

elif pagina == "CMRJ - Solicitações Legislativas":
    with open("dash_solicitacoes_cmrj.py", "r", encoding="utf-8") as f:
        code = f.read()
        exec(code)
