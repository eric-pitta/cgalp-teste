import streamlit as st
import pandas as pd
import plotly.express as px
import os
import unicodedata
import base64
import gspread
from google.oauth2.service_account import Credentials
import io

# Configuração da Página
st.set_page_config(page_title="Monitoramento CGALP", layout="wide", page_icon="📊")

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
        border: 1px solid #113359 !important;
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

# Funções Auxiliares
def get_base64_logo(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def normalizar(texto):
    if not texto or pd.isna(texto): return ""
    texto = str(texto).upper().strip()
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

# DICIONÁRIO DE COORDENADAS
BAIRROS_RJ_COORDS = {
    'CENTRO': [-22.9035, -43.1823], 'COPACABANA': [-22.9698, -43.1847], 'TIJUCA': [-22.9301, -43.2367],
    'BARRA DA TIJUCA': [-23.0003, -43.3659], 'CAMPO GRANDE': [-22.9027, -43.5591], 'BANGU': [-22.8753, -43.4667],
    'SANTA CRUZ': [-22.9197, -43.6847], 'RECREIO DOS BANDEIRANTES': [-23.0201, -43.4664], 'MEIER': [-22.8936, -43.2801],
    'MADUREIRA': [-22.8751, -43.3341], 'BOTAFOGO': [-22.9519, -43.1857], 'IPANEMA': [-22.9836, -43.2045],
    'FLAMENGO': [-22.9377, -43.1757], 'ILHA DO GOVERNADOR': [-22.8122, -43.2091], 'JACAREPAGUA': [-22.9333, -43.3411],
    'REALENGO': [-22.8833, -43.4333], 'LEBLON': [-22.9844, -43.2231], 'GRAJAU': [-22.9231, -43.2625],
    'VILA ISABEL': [-22.9167, -43.2458], 'PENHA': [-22.8333, -43.2833], 'PAVUNA': [-22.8058, -43.3644],
    'VAZ LOBO': [-22.8533, -43.3267], 'ITANHANGA': [-22.9833, -43.3000], 'TOMAS COELHO': [-22.8722, -43.3047],
    'OLARIA': [-22.8422, -43.2567], 'RAMOS': [-22.8458, -43.2458]
}

# --- CARREGAMENTO GOOGLE SHEETS HÍBRIDO ---
@st.cache_data(ttl=600)
def load_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Tenta carregar dos Secrets (Nuvem) ou JSON local
        if "gcp_service_account" in st.secrets:
            creds_info = dict(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        else:
            json_file = 'bot-consultor-10-10e87b7a88cd.json'
            if not os.path.exists(json_file):
                st.error("Arquivo de credenciais não encontrado.")
                return pd.DataFrame()
            creds = Credentials.from_service_account_file(json_file, scopes=scope)
            
        client = gspread.authorize(creds)
        sheet_id = "1wZrs1u09oD5yQTVrBuFFmCWavJGMS_-l3Gic8jz3aZk"
        spreadsheet = client.open_by_key(sheet_id)
        
        # GIDs das abas
        gids = [151993621, 2138173973, 1659318255, 94298383, 168990156]
        df_list = []
        all_worksheets = spreadsheet.worksheets()
        
        for gid in gids:
            worksheet = next((ws for ws in all_worksheets if ws.id == gid), None)
            if worksheet:
                data = worksheet.get_all_records()
                if data:
                    temp_df = pd.DataFrame(data)
                    col_mapping = {
                        'Data do Recebimento': 'Data', 'Data de Recebimento': 'Data',
                        'Ementa': 'Assunto', 'Assunto': 'Assunto',
                        'Deputado(a) Requerente': 'Requerente', 'Requerente': 'Requerente',
                        'Órgão Requerido': 'Orgao', 'Órgão Demandado': 'Orgao',
                        'Bairro Da Ocorrência': 'Bairro', 'Bairro da Ocorrência': 'Bairro',
                        'Atendimento': 'Status', 'Data da Saída': 'DataSaida'
                    }
                    temp_df.rename(columns=col_mapping, inplace=True)
                    df_list.append(temp_df)
        
        if not df_list: return pd.DataFrame()
        df = pd.concat(df_list, ignore_index=True)
        
        # Processamento
        if 'Data' in df.columns:
            df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
            df['Ano'] = df['Data'].dt.year.fillna(0).astype(int)
        df['Respondido'] = df['DataSaida'].notna()
        for col in ['Requerente', 'Orgao', 'Bairro', 'Status']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.upper()
                df[col] = df[col].replace(['NAN', 'NONE', ''], 'NÃO INFORMADO')
        return df
    except Exception as e:
        st.error(f"Erro ao conectar com Google Sheets: {e}")
        return pd.DataFrame()

# --- LÓGICA DE RELATÓRIO HTML ---
def gerar_grafico_html(df_input, coluna_grupo, cor_classe):
    if df_input.empty: return "<p>Sem dados.</p>"
    stats = df_input.groupby(coluna_grupo).agg(Total=('Respondido', 'count'), Respondidos=('Respondido', 'sum')).reset_index().sort_values('Total', ascending=False)
    max_val = stats['Total'].max()
    html_items = ""
    for _, row in stats.iterrows():
        perc_total = (row['Total'] / max_val * 100)
        perc_resp = (row['Respondidos'] / max_val * 100)
        html_items += f'<div class="chart-row"><div class="chart-label"><span>{row[coluna_grupo]}</span><span class="stats-info">{int(row["Respondidos"])} respondidos de {int(row["Total"])}</span></div><div class="bar-outer"><div class="bar-inner-total bar-{cor_classe}-light" style="width: {perc_total}%;"></div><div class="bar-inner-respondido bar-{cor_classe}-dark" style="width: {perc_resp}%;"></div></div></div>'
    return html_items

def exportar_html(df_filtrado, estilo_mapa):
    try:
        with open("relatorio.html", "r", encoding="utf-8") as f: template = f.read()
        counts = df_filtrado[df_filtrado['Bairro'] != 'NÃO INFORMADO']['Bairro'].value_counts().reset_index()
        counts.columns = ['Bairro', 'Quantidade']
        counts['lat'] = counts['Bairro'].apply(lambda b: BAIRROS_RJ_COORDS.get(normalizar(b), [None, None])[0])
        counts['lon'] = counts['Bairro'].apply(lambda b: BAIRROS_RJ_COORDS.get(normalizar(b), [None, None])[1])
        map_final = counts.dropna(subset=['lat', 'lon'])
        fig_print = px.scatter_mapbox(map_final, lat="lat", lon="lon", size="Quantidade", color="Quantidade", color_continuous_scale='Plasma', size_max=20, mapbox_style=estilo_mapa)
        fig_print.update_layout(mapbox=dict(center=dict(lat=-22.915, lon=-43.44), zoom=9.2), coloraxis_colorbar=dict(orientation='h', y=-0.1), margin=dict(l=0, r=0, t=0, b=0))
        mapa_html = fig_print.to_html(full_html=False, include_plotlyjs='cdn')
        html = template.replace("{{LOGO_BASE64}}", get_base64_logo("logo.png")).replace('<img src="data:image/png;base64,{{MAPA_BASE64}}" alt="Mapa de Incidências">', mapa_html)
        html = html.replace("{{TOTAL_SOLIC}}", str(len(df_filtrado))).replace("{{TOTAL_RESP}}", str(int(df_filtrado['Respondido'].sum()))).replace("{{TOTAL_BAIRROS}}", str(df_filtrado['Bairro'].nunique()))
        html = html.replace("{{DATA_GERACAO}}", pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")).replace("{{PERIODO}}", "Geral")
        html = html.replace("{{CHART_REQUERENTES}}", gerar_grafico_html(df_filtrado, 'Requerente', 'blue')).replace("{{CHART_ORGAOS}}", gerar_grafico_html(df_filtrado, 'Orgao', 'green')).replace("{{CHART_BAIRROS}}", gerar_grafico_html(df_filtrado[df_filtrado['Bairro'] != 'NÃO INFORMADO'], 'Bairro', 'violet'))
        status_stats = df_filtrado.groupby('Status').size().reset_index(name='Qtd').sort_values('Qtd', ascending=False)
        status_html = "".join([f'<div class="chart-row"><div class="chart-label"><span>{r["Status"]}</span><span>{r["Qtd"]}</span></div><div class="bar-outer"><div class="bar-inner-respondido bar-orange-dark" style="width: {(r["Qtd"]/status_stats["Qtd"].max()*100)}%;"></div></div></div>' for _, r in status_stats.iterrows()])
        html = html.replace("{{CHART_STATUS}}", status_html)
        return html
    except Exception as e: return f"Erro: {e}"

# ----------------- UI -----------------
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True); st.write("")
    st.header("🔍 Painel de Controle")

st.markdown("<h1 class='main-title'>Solicitações - Câmara dos Deputados</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 2px; font-size: 0.8rem; margin-bottom: 30px;'>Coordenadoria Geral de Acompanhamento Legislativo e Parlamentar</p>", unsafe_allow_html=True)

with st.spinner("Carregando dados da nuvem..."):
    df = load_data()

if df.empty: st.error("Erro ao carregar dados. Verifique a planilha e credenciais."); st.stop()

for key in ['click_req', 'click_org', 'click_bairro']:
    if key not in st.session_state: st.session_state[key] = None

# Sidebar Filtros
anos_dis = sorted([int(a) for a in df['Ano'].unique() if a > 0])
ano_sel = st.sidebar.multiselect("Filtrar por Ano", anos_dis, default=anos_dis)
estilo_mapa = st.sidebar.selectbox("Estilo do Mapa", ["open-street-map", "carto-positron", "carto-darkmatter"], index=0)

st.sidebar.divider()
if st.sidebar.button("Preparar Relatório"):
    with st.spinner("Gerando..."):
        rel_html = exportar_html(df.copy(), estilo_mapa)
        st.sidebar.download_button(label="📥 Baixar Relatório", data=rel_html, file_name="relatorio_cgalp.html", mime="text/html")

if st.sidebar.button("Limpar Filtros"):
    st.session_state.click_req = st.session_state.click_org = st.session_state.click_bairro = None; st.rerun()

# Filtros
df_f = df.copy()
if ano_sel: df_f = df_f[df_f['Ano'].isin(ano_sel)]
if st.session_state.click_req: df_f = df_f[df_f['Requerente'] == st.session_state.click_req]
if st.session_state.click_org: df_f = df_f[df_f['Orgao'] == st.session_state.click_org]
if st.session_state.click_bairro: df_f = df_f[df_f['Bairro'] == st.session_state.click_bairro]

# --- MAPA ---
st.markdown("<div class='section-header'>🗺️ Geocalização de Demandas</div>", unsafe_allow_html=True)
map_counts = df_f[df_f['Bairro'] != 'NÃO INFORMADO']['Bairro'].value_counts().reset_index()
map_counts.columns = ['Bairro', 'Quantidade']
map_counts['lat'] = map_counts['Bairro'].apply(lambda x: BAIRROS_RJ_COORDS.get(normalizar(x), [None, None])[0])
map_counts['lon'] = map_counts['Bairro'].apply(lambda x: BAIRROS_RJ_COORDS.get(normalizar(x), [None, None])[1])
map_ready = map_counts.dropna(subset=['lat', 'lon'])
fig_map = px.scatter_mapbox(map_ready, lat="lat", lon="lon", size="Quantidade", hover_name="Bairro", color="Quantidade", color_continuous_scale='Plasma', size_max=40, zoom=10, mapbox_style=estilo_mapa)
fig_map.update_layout(height=550, margin={"r":0,"t":0,"l":0,"b":0}, clickmode='event+select')
sel_map = st.plotly_chart(fig_map, use_container_width=True, on_select="rerun")
if sel_map and sel_map["selection"]["points"]:
    st.session_state.click_bairro = sel_map["selection"]["points"][0]["hovertext"]; st.rerun()

# --- MÉTRICAS ---
st.write("")
m_col = st.columns(5)
metrics = [("Solicitações", len(df_f)), ("Respondidos", int(df_f['Respondido'].sum())), ("Requerentes", df_f['Requerente'].nunique()), ("Órgãos", df_f['Orgao'].nunique()), ("Bairros", df_f['Bairro'].nunique())]
for i, (label, val) in enumerate(metrics):
    with m_col[i]: st.markdown(f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{val}</div></div>", unsafe_allow_html=True)

# --- TABELAS ---
def criar_tabela_tech(df_input, col, titulo, icone, key, cor):
    if df_input.empty: return
    stats = df_input.groupby(col).agg(Qtd=('Respondido', 'count'), Resp=('Respondido', 'sum')).reset_index()
    stats['%'] = (stats['Resp'] / stats['Qtd'] * 100).fillna(0); stats = stats.sort_values('Qtd', ascending=False)
    st.markdown(f"<div class='table-header-bar'>{icone} {titulo}</div>", unsafe_allow_html=True)
    sel = st.dataframe(stats[[col, 'Qtd', '%']], column_config={col: st.column_config.TextColumn(col.capitalize(), width="medium"), "Qtd": st.column_config.ProgressColumn("Qtd", format="%d", min_value=0, max_value=int(stats['Qtd'].max()) if int(stats['Qtd'].max()) > 0 else 100, color=cor), "%": st.column_config.ProgressColumn("%", format="%.0f%%", min_value=0, max_value=100, color=cor)}, hide_index=True, use_container_width=True, on_select="rerun")
    if sel and sel["selection"]["rows"]: st.session_state[key] = stats.iloc[sel["selection"]["rows"][0]][col]; st.rerun()

criar_tabela_tech(df_f, 'Requerente', "Desempenho por Requerente", "👤", 'click_req', "blue")
criar_tabela_tech(df_f, 'Orgao', "Desempenho por Órgão", "🏢", 'click_org', "green")
criar_tabela_tech(df_f[df_f['Bairro'] != 'NÃO INFORMADO'], 'Bairro', "Solicitações por Bairro", "📍", 'click_bairro', "violet")

# --- STATUS BOARD ---
st.markdown("<div class='section-header'>📌 Situação dos Atendimentos</div>", unsafe_allow_html=True)
if not df_f.empty:
    status_counts = df_f['Status'].value_counts().reset_index().sort_values('count', ascending=False)
    total_s = status_counts['count'].sum()
    for _, row in status_counts.iterrows():
        p = (row['count'] / total_s) * 100
        cor = "#636EFA"
        status_up = str(row['Status']).upper()
        if status_up in ['SIM', 'CONCLUÍDO', 'ATENDIDO', 'FINALIZADO']: cor = "#00CC96"
        elif status_up in ['NÃO', 'EM ATRASO']: cor = "#EF4444"
        elif status_up in ['EM ANDAMENTO', 'PARCIAL']: cor = "#8B5CF6"
        elif status_up in ['PENDENTE', 'AGUARDANDO']: cor = "#FACC15"
        elif status_up == 'NÃO INFORMADO': cor = "#94a3b8"
        st.markdown(f"<div class='status-item'><div class='status-label-row'><span>{row['Status']}</span><span>{row['count']} ({p:.1f}%)</span></div><div class='status-bar-bg'><div class='status-bar-fill' style='width: {p}%; background: {cor}; box-shadow: 0 0 10px {cor}44;'></div></div></div>", unsafe_allow_html=True)

st.write("")
with st.expander("📄 Base de Dados Completa"):
    st.dataframe(df_f[['Data', 'Requerente', 'Bairro', 'Orgao', 'Status', 'Assunto']], use_container_width=True)
