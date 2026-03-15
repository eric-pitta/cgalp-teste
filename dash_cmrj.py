import streamlit as st
import pandas as pd
import plotly.express as px
import os
import unicodedata
import base64
import gspread
from google.oauth2.service_account import Credentials
import io
import time
from geopy.geocoders import Nominatim

# Configuração da Página
st.set_page_config(page_title="CMRJ - Indicações Legislativas", layout="wide", page_icon="📊")

# --- INJEÇÃO DE CSS TECH PREMIUM ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
    
    html, body, [data-testid="stSidebar"] {
        font-family: 'Inter', sans-serif;
        background-color: #fcfcfc;
    }

    .main-title {
        text-align: center;
        padding: 20px 0 10px 0;
        color: #113359 !important;
        font-weight: 900;
        letter-spacing: -1.5px;
    }

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

    .stDataFrame {
        border: 1px solid #113359 !important;
        border-radius: 0 0 12px 12px !important;
        overflow: hidden;
        margin-top: -1px !important;
    }

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
    .metric-card:hover { box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); transform: translateY(-5px); }
    .metric-label { font-size: 0.75rem; color: #94a3b8; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
    .metric-value { font-size: 2.2rem; color: #0f172a; font-weight: 900; }

    .status-item { margin-bottom: 20px; padding: 15px; background: white; border-radius: 12px; border: 1px solid #f1f5f9; }
    .status-label-row { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 0.95rem; font-weight: 700; color: #1e293b; text-transform: uppercase; }
    .status-bar-bg { background: #e2e8f0; border-radius: 10px; height: 12px; width: 100%; overflow: hidden; }
    .status-bar-fill { height: 100%; border-radius: 10px; transition: width 1s ease-in-out; }

    [data-testid="stSidebar"] { background-color: #f8fafc; border-right: 1px solid #e2e8f0; }
    span[data-baseweb="tag"] { background-color: #113359 !important; border-radius: 4px !important; }
    span[data-baseweb="tag"] span { color: white !important; }

    div.stButton > button { background: linear-gradient(135deg, #113359 0%, #5CA0D3 100%); color: white; border: none; border-radius: 8px; padding: 10px 20px; font-weight: 600; width: 100%; }
    div.stButton > button:hover { opacity: 0.9; color: white; }
    </style>
""", unsafe_allow_html=True)

# Funções Auxiliares
def get_base64_logo(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f: return base64.b64encode(f.read()).decode()
    return ""

def normalizar(texto):
    if not texto or pd.isna(texto): return ""
    texto = str(texto).upper().strip()
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

BAIRROS_RJ_COORDS = {
    'CENTRO': [-22.9035, -43.1823], 'COPACABANA': [-22.9698, -43.1847], 'TIJUCA': [-22.9301, -43.2367],
    'BARRA DA TIJUCA': [-23.0003, -43.3659], 'CAMPO GRANDE': [-22.9027, -43.5591], 'BANGU': [-22.8753, -43.4667],
    'SANTA CRUZ': [-22.9197, -43.6847], 'RECREIO DOS BANDEIRANTES': [-23.0201, -43.4664], 'MEIER': [-22.8936, -43.2801],
    'MADUREIRA': [-22.8751, -43.3341], 'BOTAFOGO': [-22.9519, -43.1857], 'IPANEMA': [-22.9836, -43.2045],
    'FLAMENGO': [-22.9377, -43.1757], 'ILHA DO GOVERNADOR': [-22.8122, -43.2091], 'JACAREPAGUA': [-22.9333, -43.3411],
    'REALENGO': [-22.8833, -43.4333], 'LEBLON': [-22.9844, -43.2231], 'GRAJAU': [-22.9231, -43.2625],
    'VILA ISABEL': [-22.9167, -43.2458], 'PENHA': [-22.8333, -43.2833], 'PAVUNA': [-22.8058, -43.3644],
    'VAZ LOBO': [-22.8533, -43.3267], 'ITANHANGA': [-22.9833, -43.3000], 'TOMAS COELHO': [-22.8722, -43.3047],
    'OLARIA': [-22.8422, -43.2567], 'RAMOS': [-22.8458, -43.2458], 'RIO COMPRIDO': [-22.9264, -43.2086],
    'COELHO NETO': [-22.8275, -43.3442]
}

@st.cache_data(show_spinner=False)
def obter_coordenadas(bairro):
    bairro_norm = normalizar(bairro)
    if bairro_norm in BAIRROS_RJ_COORDS: return BAIRROS_RJ_COORDS[bairro_norm]
    geolocator = Nominatim(user_agent="monitoramento_cgalp_cmrj")
    try:
        time.sleep(1)
        location = geolocator.geocode(f"{bairro}, Rio de Janeiro, RJ, Brasil")
        if location: return [location.latitude, location.longitude]
    except: pass
    return [None, None]

# --- CARREGAMENTO GOOGLE SHEETS CMRJ ---
@st.cache_data(ttl=600)
def load_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        json_file = 'bot-consultor-10-10e87b7a88cd.json'
        
        creds = None
        if os.path.exists(json_file):
            creds = Credentials.from_service_account_file(json_file, scopes=scope)
        elif "gcp_service_account" in st.secrets:
            creds_dict = {k: v for k, v in st.secrets["gcp_service_account"].items()}
            if "private_key" in creds_dict: creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        else: return pd.DataFrame()
            
        client = gspread.authorize(creds)
        
        # Lista de Planilhas e GIDs da CMRJ
        sources = [
            {"id": "1jgUBYqqpTFwAhT6POV-NRKWwKPzCprmJL4yPDzpQM6M", "gids": [1506037823, 1750823131, 354190818, 530317761]},
            {"id": "1m_fPafrJW1MZq0b_r2C_6Te2GoLlZ3QX9YUikNk0arc", "gids": [1096879621]}
        ]
        
        df_list = []
        for src in sources:
            spreadsheet = client.open_by_key(src["id"])
            all_worksheets = spreadsheet.worksheets()
            for gid in src["gids"]:
                worksheet = next((ws for ws in all_worksheets if ws.id == gid), None)
                if worksheet:
                    data = worksheet.get_all_records()
                    if data:
                        temp_df = pd.DataFrame(data)
                        col_mapping = {
                            'Data de Chegada': 'Data', 'Ementa': 'Assunto',
                            'Vereador Requerente': 'Requerente', 'Bairro da Ocorrência': 'Bairro',
                            'Concluído': 'Status', 'Data de Saída': 'DataSaida'
                        }
                        temp_df.rename(columns=col_mapping, inplace=True)
                        df_list.append(temp_df)
        
        if not df_list: return pd.DataFrame()
        df = pd.concat(df_list, ignore_index=True)
        
        if 'Data' in df.columns:
            df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
            df['Ano'] = df['Data'].dt.year.fillna(0).astype(int)
        
        df['Respondido'] = df['DataSaida'].notna() & (df['DataSaida'] != "")
        
        # Normalização de Status e Órgãos
        for col in ['Requerente', 'Bairro', 'Status', 'Órgão Demandado', 'Órgão Demandado 2', 'Órgão Demandado 3']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.upper().replace(['NAN', 'NONE', '', '0', '0.0'], 'NÃO INFORMADO')
        
        return df
    except Exception as e:
        st.error(f"Erro na conexão CMRJ: {e}"); return pd.DataFrame()

# --- LÓGICA ÓRGÃOS (TRIPLO) ---
def get_organ_stats(df_input):
    # Unifica as 3 colunas de órgãos para uma contagem única
    o1 = df_input[['Órgão Demandado', 'Respondido']].rename(columns={'Órgão Demandado': 'Orgao'})
    o2 = df_input[['Órgão Demandado 2', 'Respondido']].rename(columns={'Órgão Demandado 2': 'Orgao'})
    o3 = df_input[['Órgão Demandado 3', 'Respondido']].rename(columns={'Órgão Demandado 3': 'Orgao'})
    combined = pd.concat([o1, o2, o3], ignore_index=True)
    combined = combined[combined['Orgao'] != 'NÃO INFORMADO']
    stats = combined.groupby('Orgao').agg(Total=('Respondido', 'count'), Respondidos=('Respondido', 'sum')).reset_index()
    return stats.sort_values('Total', ascending=False)

# --- UI ---
with st.sidebar:
    if os.path.exists("logo.png"):
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2: st.image("logo.png", width=80)
    st.header("Painel CMRJ")

st.markdown("<h1 class='main-title'>CMRJ - Indicações Legislativas</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 2px; font-size: 0.8rem; margin-bottom: 30px;'>Acompanhamento de Demandas e Produtividade</p>", unsafe_allow_html=True)

df = load_data()
if df.empty: st.stop()

# --- RESET ---
def limpar_filtros():
    for k in ['click_req', 'click_org', 'click_bairro', 'sb_ano', 'sb_req', 'sb_bairro', 'sb_status']:
        if k in st.session_state: del st.session_state[k]

# --- SIDEBAR FILTROS ---
anos_dis = sorted([int(a) for a in df['Ano'].unique() if a > 0])
ano_sel = st.sidebar.multiselect("Filtrar por Ano", anos_dis, default=anos_dis, key="sb_ano")
req_sel = st.sidebar.selectbox("Requerente", ["TODOS"] + sorted(df['Requerente'].unique().tolist()), key="sb_req")
bairro_sel = st.sidebar.selectbox("Bairro", ["TODOS"] + sorted(df['Bairro'].unique().tolist()), key="sb_bairro")
status_sel = st.sidebar.selectbox("Situação", ["TODOS"] + sorted(df['Status'].unique().tolist()), key="sb_status")
estilo_mapa = st.sidebar.selectbox("Mapa", ["carto-positron", "open-street-map", "carto-darkmatter"])

st.sidebar.button("Limpar Filtros", on_click=limpar_filtros)

# Aplicação Filtros
df_f = df.copy()
if "sb_ano" in st.session_state and st.session_state.sb_ano: df_f = df_f[df_f['Ano'].isin(st.session_state.sb_ano)]
if "sb_req" in st.session_state and st.session_state.sb_req != "TODOS": df_f = df_f[df_f['Requerente'] == st.session_state.sb_req]
if "sb_bairro" in st.session_state and st.session_state.sb_bairro != "TODOS": df_f = df_f[df_f['Bairro'] == st.session_state.sb_bairro]
if "sb_status" in st.session_state and st.session_state.sb_status != "TODOS": df_f = df_f[df_f['Status'] == st.session_state.sb_status]

# Cross-filtering cliques
if 'click_req' in st.session_state and st.session_state.click_req: df_f = df_f[df_f['Requerente'] == st.session_state.click_req]
if 'click_bairro' in st.session_state and st.session_state.click_bairro: df_f = df_f[df_f['Bairro'] == st.session_state.click_bairro]

# --- MAPA ---
st.markdown("<div class='section-header'>🗺️ Geocalização CMRJ</div>", unsafe_allow_html=True)
map_counts = df_f[df_f['Bairro'] != 'NÃO INFORMADO']['Bairro'].value_counts().reset_index()
map_counts.columns = ['Bairro', 'Quantidade']
with st.spinner("Mapeando..."):
    map_counts['coords'] = map_counts['Bairro'].apply(obter_coordenadas)
    map_counts['lat'] = map_counts['coords'].apply(lambda x: x[0] if x else None)
    map_counts['lon'] = map_counts['coords'].apply(lambda x: x[1] if x else None)
map_ready = map_counts.dropna(subset=['lat', 'lon'])
if not map_ready.empty:
    fig = px.scatter_mapbox(map_ready, lat="lat", lon="lon", size="Quantidade", hover_name="Bairro", color="Quantidade", color_continuous_scale='Plasma', size_max=40, zoom=10, mapbox_style=estilo_mapa)
    fig.update_layout(height=550, margin={"r":0,"t":0,"l":0,"b":0})
    sel_map = st.plotly_chart(fig, width="stretch", on_select="rerun")
    if sel_map and sel_map["selection"]["points"]:
        st.session_state.click_bairro = sel_map["selection"]["points"][0]["hovertext"]; st.rerun()

# --- MÉTRICAS ---
st.write("")
m = st.columns(5)
metrics = [("Indicações", len(df_f)), ("Respondidos", int(df_f['Respondido'].sum())), ("Vereadores", df_f['Requerente'].nunique()), ("Bairros", df_f['Bairro'].nunique())]
for i, (l, v) in enumerate(metrics):
    with m[i]: st.markdown(f"<div class='metric-card'><div class='metric-label'>{l}</div><div class='metric-value'>{v}</div></div>", unsafe_allow_html=True)

# --- TABELAS ---
def criar_tabela(df_input, col, titulo, icone, key, cor):
    stats = df_input.groupby(col).agg(Qtd=('Respondido', 'count'), Resp=('Respondido', 'sum')).reset_index()
    stats['%'] = (stats['Resp'] / stats['Qtd'] * 100).fillna(0); stats = stats.sort_values('Qtd', ascending=False)
    st.markdown(f"<div class='table-header-bar'>{icone} {titulo}</div>", unsafe_allow_html=True)
    sel = st.dataframe(stats[[col, 'Qtd', '%']], column_config={col: st.column_config.TextColumn(col, width="medium"), "Qtd": st.column_config.ProgressColumn("Qtd", format="%d", min_value=0, max_value=int(stats['Qtd'].max()), color=cor), "%": st.column_config.ProgressColumn("%", format="%.0f%%", min_value=0, max_value=100, color=cor)}, hide_index=True, width="stretch", on_select="rerun")
    if sel and sel["selection"]["rows"]: st.session_state[key] = stats.iloc[sel["selection"]["rows"][0]][col]; st.rerun()

criar_tabela(df_f, 'Requerente', "Desempenho por Vereador", "👤", 'click_req', "blue")

# Tabela Órgão (Lógica Especial Tripla)
org_stats = get_organ_stats(df_f)
st.markdown(f"<div class='table-header-bar'>🏢 Demandas por Órgão</div>", unsafe_allow_html=True)
st.dataframe(org_stats, column_config={"Orgao": "Órgão", "Total": st.column_config.ProgressColumn("Total", format="%d", min_value=0, max_value=int(org_stats['Total'].max() if not org_stats.empty else 1), color="green")}, hide_index=True, width="stretch")

criar_tabela(df_f[df_f['Bairro'] != 'NÃO INFORMADO'], 'Bairro', "Solicitações por Bairro", "📍", 'click_bairro', "violet")

# --- STATUS ---
st.markdown("<div class='section-header'>📌 Situação das Indicações</div>", unsafe_allow_html=True)
status_counts = df_f['Status'].value_counts().reset_index().sort_values('count', ascending=False)
total_s = status_counts['count'].sum()
for _, row in status_counts.iterrows():
    p = (row['count'] / total_s) * 100
    cor = "#636EFA"
    s_up = str(row['Status']).upper()
    if s_up in ['SIM', 'CONCLUÍDO', 'ATENDIDO', 'FINALIZADO']: cor = "#00CC96"
    elif s_up in ['NÃO', 'EM ATRASO']: cor = "#EF4444"
    elif s_up in ['EM ANDAMENTO','PENDENTE' ]: cor = "#EEF65C"
    elif s_up in ['PARCIAL', 'AGUARDANDO']: cor = "#15E7FA"
    st.markdown(f"<div class='status-item'><div class='status-label-row'><span>{row['Status']}</span><span>{row['count']} ({p:.1f}%)</span></div><div class='status-bar-bg'><div class='status-bar-fill' style='width: {p}%; background: {cor};'></div></div></div>", unsafe_allow_html=True)

with st.expander("📄 Dados Detalhados CMRJ"): st.dataframe(df_f[['Data', 'Requerente', 'Bairro', 'Status', 'Assunto']], width="stretch")
