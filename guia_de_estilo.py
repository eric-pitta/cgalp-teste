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
    'COELHO NETO': [-22.8275, -43.3442], 'SANTA TERESA': [-22.9253, -43.1931], 'LAPA': [-22.9133, -43.1821],
    'LAGOA': [-22.9719, -43.2025], 'GAVEA': [-22.9751, -43.2285], 'HUMAITA': [-22.9571, -43.1994],
    'URCA': [-22.9555, -43.1647], 'SAO CRISTOVAO': [-22.8975, -43.2253], 'GLORIA': [-22.9218, -43.1767],
    'CATETE': [-22.9259, -43.1768], 'COSME VELHO': [-22.9419, -43.1994], 'LARANJEIRAS': [-22.9341, -43.1888],
    'JARDIM BOTANICO': [-22.9667, -43.2251], 'MARACANA': [-22.9122, -43.2301], 'PRACA DA BANDEIRA': [-22.9094, -43.2181],
    'ESTACIO': [-22.9147, -43.2025], 'SANTO CRISTO': [-22.9003, -43.1969], 'GAMBOA': [-22.8972, -43.1897],
    'SAUDE': [-22.8967, -43.1844], 'CAJU': [-22.8872, -43.2169], 'BENFICA': [-22.8931, -43.2372],
    'MANGUEIRA': [-22.9036, -43.2325], 'ROCHA': [-22.9008, -43.2458], 'RIACHUELO': [-22.9001, -43.2567],
    'SAMPAIO': [-22.9006, -43.2647], 'ENGENHO NOVO': [-22.9003, -43.2731], 'LINS DE VASCONCELOS': [-22.9117, -43.2847],
    'TODOS OS SANTOS': [-22.8953, -43.2867], 'CACHAMBI': [-22.8858, -43.2758], 'ENGENHO DE DENTRO': [-22.8958, -43.2967],
    'ABOLICAO': [-22.8853, -43.3031], 'PILARES': [-22.8797, -43.2953], 'PIEDADE': [-22.8917, -43.3053],
    'QUINTINO BOCAIUVA': [-22.8867, -43.3153], 'CASCADURA': [-22.8817, -43.3253], 'CAVALCANTE': [-22.8717, -43.3253],
    'ENGENHEIRO LEAL': [-22.8717, -43.3333], 'TURIACO': [-22.8617, -43.3453], 'OSWALDO CRUZ': [-22.8667, -43.3553],
    'BENTO RIBEIRO': [-22.8617, -43.3653], 'MARECHAL HERMES': [-22.8617, -43.3753], 'DEODORO': [-22.8553, -43.3853],
    'GUADALUPE': [-22.8367, -43.3753], 'RICARDO DE ALBUQUERQUE': [-22.8367, -43.3953], 'ANCHIETA': [-22.8217, -43.4053],
    'PARQUE ANCHIETA': [-22.8217, -43.4153], 'COSTA BARROS': [-22.8117, -43.3653], 'BARROS FILHO': [-22.8117, -43.3553],
    'HONORIO GURGEL': [-22.8317, -43.3553], 'ROCHA MIRANDA': [-22.8517, -43.3453], 'COLEGIO': [-22.8317, -43.3353],
    'IRAJA': [-22.8317, -43.3253], 'VILA DA PENHA': [-22.8417, -43.3153], 'VICENTE DE CARVALHO': [-22.8517, -43.3153],
    'VILA KOSMOS': [-22.8517, -43.3053], 'PENHA CIRCULAR': [-22.8317, -43.2953], 'BRAS DE PINA': [-22.8253, -43.2953],
    'CORDOVIL': [-22.8153, -43.2953], 'PARADA DE LUCAS': [-22.8053, -43.2953], 'VIGARIO GERAL': [-22.7953, -43.2953],
    'JARDIM AMERICA': [-22.7953, -43.3153], 'HIGIENOPOLIS': [-22.8653, -43.2653], 'MARIA DA GRACA': [-22.8753, -43.2653],
    'DEL CASTILHO': [-22.8753, -43.2753], 'INHAUMA': [-22.8753, -43.2853], 'ENGENHO DA RAINHA': [-22.8653, -43.2953],
    'BONSUCESSO': [-22.8617, -43.2553], 'MANGUINHOS': [-22.8817, -43.2453], 'MARE': [-22.8553, -43.2353],
    'ACARI': [-22.8167, -43.3417], 'CURICICA': [-22.9467, -43.3853], 'ANIL': [-22.9567, -43.3353],
    'GARDENIA AZUL': [-22.9667, -43.3553], 'CIDADE DE DEUS': [-22.9467, -43.3653], 'TAQUARA': [-22.9267, -43.3753],
    'TANQUE': [-22.9167, -43.3653], 'PECHINCHA': [-22.9367, -43.3553], 'FREGUESIA JACAREPAGUA': [-22.9417, -43.3417],
    'PRACA SECA': [-22.8967, -43.3553], 'VILA VALQUEIRE': [-22.8867, -43.3653], 'CAMORIM': [-22.9717, -43.4053],
    'VARGEM PEQUENA': [-22.9917, -43.4453], 'VARGEM GRANDE': [-22.9917, -43.4853], 'GRUMARI': [-23.0417, -43.5253],
    'GUARATIBA': [-22.9867, -43.6053], 'BARRA DE GUARATIBA': [-23.0617, -43.5653], 'PEDRA DE GUARATIBA': [-23.0017, -43.6353],
    'SEPETIBA': [-22.9717, -43.7053], 'PACIENCIA': [-22.9167, -43.6353], 'COSMOS': [-22.9067, -43.6153],
    'INHOAIBA': [-22.9117, -43.5853], 'SENADOR CAMARA': [-22.8867, -43.5053], 'SENADOR VASCONCELOS': [-22.8967, -43.5253],
    'SANTISSIMO': [-22.8867, -43.5353], 'PADRE MIGUEL': [-22.8767, -43.4553], 'MAGALHAES BASTOS': [-22.8767, -43.4253],
    'VILA MILITAR': [-22.8667, -43.4053], 'PAQUETA': [-22.7567, -43.1053], 'ROCINHA': [-22.9883, -43.2483],
    'VIDIGAL': [-22.9933, -43.2383], 'JACARE': [-22.8917, -43.2553], 'VILA DA PENHA': [-22.8417, -43.3153]
}

@st.cache_data(show_spinner=False)
def obter_coordenadas(bairro):
    if not bairro or bairro in ['NÃO INFORMADO', 'N/A', 'NA', '', '0', '0.0']: return [None, None]
    bairro_norm = normalizar(bairro)
    
    # Mapeamentos de nomes comuns para garantir correspondência no dicionário
    mapeamentos = {
        'FREGUESIA': 'FREGUESIA JACAREPAGUA',
        'FREGUESIA DO JACAREPAGUA': 'FREGUESIA JACAREPAGUA',
        'ILHA DE PAQUETA': 'PAQUETA',
        'PAQUETA': 'PAQUETA',
        'RECREIO': 'RECREIO DOS BANDEIRANTES',
        'BARRA': 'BARRA DA TIJUCA'
    }
    if bairro_norm in mapeamentos: bairro_norm = mapeamentos[bairro_norm]
    
    if bairro_norm in BAIRROS_RJ_COORDS:
        return BAIRROS_RJ_COORDS[bairro_norm]
    
    # Fallback para Geocodificação (apenas se não estiver no dicionário)
    geolocator = Nominatim(user_agent="monitoramento_cgalp_rj_v2")
    query = f"{bairro}, Rio de Janeiro, RJ, Brasil"
    try:
        time.sleep(0.5) # Reduzido para melhorar performance
        location = geolocator.geocode(query, timeout=5)
        if location:
            return [location.latitude, location.longitude]
    except Exception:
        pass
    return [None, None]

@st.cache_data(ttl=600)
def load_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        json_file = 'bot-consultor-10-10e87b7a88cd.json'
        creds = None
        if os.path.exists(json_file):
            creds = Credentials.from_service_account_file(json_file, scopes=scope)
        elif "gcp_service_account" in st.secrets:
            creds_info = st.secrets["gcp_service_account"]
            creds_dict = {
                "type": creds_info["type"], "project_id": creds_info["project_id"],
                "private_key_id": creds_info["private_key_id"], "private_key": creds_info["private_key"].replace("\\n", "\n"),
                "client_email": creds_info["client_email"], "client_id": creds_info["client_id"],
                "auth_uri": creds_info["auth_uri"], "token_uri": creds_info["token_uri"],
                "auth_provider_x509_cert_url": creds_info["auth_provider_x509_cert_url"],
                "client_x509_cert_url": creds_info["client_x509_cert_url"]
            }
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        else:
            return pd.DataFrame()
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key("1wZrs1u09oD5yQTVrBuFFmCWavJGMS_-l3Gic8jz3aZk")
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
        if 'Data' in df.columns:
            df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
            df['Ano'] = df['Data'].dt.year.fillna(0).astype(int)
        df['Respondido'] = df['DataSaida'].notna()
        for col in ['Requerente', 'Orgao', 'Bairro', 'Status']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.upper()
                df[col] = df[col].replace(['NAN', 'NONE', '', '0', '0.0'], 'NÃO INFORMADO')
        return df
    except Exception as e:
        st.error(f"Erro crítico na conexão Google: {e}")
        return pd.DataFrame()

def gerar_tabela_html(df_input, coluna_grupo, titulo, icone, cor_classe):
    if df_input.empty: return ""
    stats = df_input.groupby(coluna_grupo).agg(Total=('Respondido', 'count'), Respondidos=('Respondido', 'sum')).reset_index().sort_values('Total', ascending=False)
    html = f"<div class='table-header-bar'>{icone} {titulo}</div>"
    html += "<table><thead><tr><th>Exibição</th><th>Qtd</th><th>% Respondido</th></tr></thead><tbody>"
    for i, row in stats.reset_index(drop=True).iterrows():
        medal = ""
        cls = ""
        if i == 0: medal = " 🥇"; cls = "top-1"
        elif i == 1: medal = " 🥈"; cls = "top-2"
        elif i == 2: medal = " 🥉"; cls = "top-3"
        perc = (row['Respondidos'] / row['Total'] * 100) if row['Total'] > 0 else 0
        html += f"<tr><td class='{cls}'>{row[coluna_grupo]}{medal}</td><td>{int(row['Total'])}</td><td><div class='progress-container'><div class='progress-bar bar-{cor_classe}' style='width: {perc}%;'></div></div>{perc:.1f}%</td></tr>"
    html += "</tbody></table>"
    return html

def exportar_html(df_filtrado, estilo_mapa):
    try:
        with open("relatorio.html", "r", encoding="utf-8") as f: template = f.read()
        counts = df_filtrado[~df_filtrado['Bairro'].isin(['NÃO INFORMADO', 'N/A', 'NA', '', '0', '0.0'])]['Bairro'].value_counts().reset_index()
        counts.columns = ['Bairro', 'Quantidade']
        counts['coords'] = counts['Bairro'].apply(obter_coordenadas)
        counts['lat'] = counts['coords'].apply(lambda x: x[0] if x else None)
        counts['lon'] = counts['coords'].apply(lambda x: x[1] if x else None)
        map_final = counts.dropna(subset=['lat', 'lon'])
        map_final = map_final[map_final['Quantidade'] > 0]
        fig_print = px.scatter_mapbox(map_final, lat="lat", lon="lon", size="Quantidade", color="Quantidade", color_continuous_scale='Plasma', size_max=20, mapbox_style=estilo_mapa)
        fig_print.update_layout(mapbox=dict(center=dict(lat=-22.915, lon=-43.44), zoom=9.2), coloraxis_colorbar=dict(orientation='h', y=-0.1), margin=dict(l=0, r=0, t=0, b=0))
        mapa_html = fig_print.to_html(full_html=False, include_plotlyjs='cdn')
        total_sol = len(df_filtrado)
        total_resp = int(df_filtrado['Respondido'].sum())
        perc_total = (total_resp / total_sol * 100) if total_sol > 0 else 0
        html = template.replace("{{LOGO_BASE64}}", get_base64_logo("logo2.png")).replace("{{MAPA_HTML}}", mapa_html)
        html = html.replace("{{TITULO_RELATORIO}}", "Relatório de Monitoramento")
        html = html.replace("{{LABEL_SOLIC}}", "Solicitações")
        html = html.replace("{{TOTAL_SOLIC}}", str(total_sol)).replace("{{TOTAL_RESP}}", str(total_resp)).replace("{{PERC_RESP}}", f"{perc_total:.1f}")
        html = html.replace("{{TOTAL_BAIRROS}}", str(df_filtrado[~df_filtrado['Bairro'].isin(['NÃO INFORMADO', 'N/A', 'NA', '', '0', '0.0'])]['Bairro'].nunique()))
        html = html.replace("{{PERIODO}}", "Geral")
        tab_html = gerar_tabela_html(df_filtrado, 'Requerente', "Desempenho por Requerente", "👤", 'blue')
        tab_html += gerar_tabela_html(df_filtrado, 'Orgao', "Demandas por Órgão", "🏢", 'green')
        tab_html += gerar_tabela_html(df_filtrado[~df_filtrado['Bairro'].isin(['NÃO INFORMADO', 'N/A', 'NA', '', '0', '0.0'])], 'Bairro', "Solicitações por Bairro", "📍", 'violet')
        html = html.replace("{{TABELAS_HTML}}", tab_html)
        return html
    except Exception as e: return f"Erro: {e}"

st.markdown("<h1 class='main-title'>Guia de Estilo CGALP</h1>", unsafe_allow_html=True)
with st.spinner("Carregando dados..."):
    df = load_data()
if df.empty: st.stop()

for key in ['click_req', 'click_org', 'click_bairro']:
    if key not in st.session_state: st.session_state[key] = None

# Sidebar
def limpar_filtros():
    st.session_state.click_req = None
    st.session_state.click_org = None
    st.session_state.click_bairro = None
    for k in ["sb_ano", "sb_req", "sb_bairro", "sb_status"]:
        if k in st.session_state: del st.session_state[k]

with st.sidebar:
    st.button("Limpar Filtros", on_click=limpar_filtros)
    anos_dis = sorted([int(a) for a in df['Ano'].unique() if a > 0])
    st.multiselect("Filtrar por Ano", anos_dis, default=anos_dis, key="sb_ano")
    estilo_mapa = st.selectbox("Estilo do Mapa", ["carto-positron", "open-street-map", "carto-darkmatter"], index=0)

# Dados filtrados (df_f)
df_f = df.copy()
if "sb_ano" in st.session_state and st.session_state.sb_ano:
    df_f = df_f[df_f['Ano'].isin(st.session_state.sb_ano)]

# Botão de relatório posicionado após a criação do df_f
with st.sidebar:
    if st.button("Preparar Relatório"):
        with st.spinner("Gerando..."):
            rel_html = exportar_html(df_f.copy(), estilo_mapa)
            st.download_button(label="📥 Baixar Relatório", data=rel_html, file_name="relatorio_cgalp.html", mime="text/html")

# Mapa
st.markdown("<div class='section-header'>🗺️ Geocalização</div>", unsafe_allow_html=True)
map_counts = df_f[~df_f['Bairro'].isin(['NÃO INFORMADO', 'N/A', 'NA', '', '0', '0.0'])]['Bairro'].value_counts().reset_index()
map_counts.columns = ['Bairro', 'Quantidade']
map_counts['coords'] = map_counts['Bairro'].apply(obter_coordenadas)
map_counts['lat'] = map_counts['coords'].apply(lambda x: x[0] if x else None)
map_counts['lon'] = map_counts['coords'].apply(lambda x: x[1] if x else None)
map_ready = map_counts.dropna(subset=['lat', 'lon'])
if not map_ready.empty:
    fig_map = px.scatter_mapbox(map_ready, lat="lat", lon="lon", size="Quantidade", hover_name="Bairro", color="Quantidade", color_continuous_scale='Plasma', size_max=40, zoom=10, mapbox_style=estilo_mapa)
    fig_map.update_layout(height=550, margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_map, width="stretch")

# Métricas
st.write("")
m_col = st.columns(5)
metrics = [("Solicitações", len(df_f)), ("Respondidos", int(df_f['Respondido'].sum())), ("Requerentes", df_f['Requerente'].nunique()), ("Órgãos", df_f['Orgao'].nunique()), ("Bairros", df_f['Bairro'].nunique())]
for i, (label, val) in enumerate(metrics):
    with m_col[i]: st.markdown(f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{val}</div></div>", unsafe_allow_html=True)

# Tabelas
def criar_tabela_exemplo(df_input, col, titulo, icone, cor):
    if df_input.empty: return
    stats = df_input.groupby(col).agg(Qtd=('Respondido', 'count'), Resp=('Respondido', 'sum')).reset_index()
    stats['%'] = (stats['Resp'] / stats['Qtd'] * 100).fillna(0); stats = stats.sort_values('Qtd', ascending=False).reset_index(drop=True)
    def stylize(name, index):
        medal = ""
        if index == 0: medal = " 🥇"
        elif index == 1: medal = " 🥈"
        elif index == 2: medal = " 🥉"
        return f"{name}{medal}"
    stats['Exibição'] = [stylize(row[col], i) for i, row in stats.iterrows()]
    st.markdown(f"<div class='table-header-bar'>{icone} {titulo}</div>", unsafe_allow_html=True)
    def style_top_3(row):
        styles = [''] * len(row)
        if row.name == 0: styles = ['color: #FFD700; font-weight: bold; font-family: Arial'] * len(row)
        elif row.name == 1: styles = ['color: #C0C0C0; font-weight: bold; font-family: Arial'] * len(row)
        elif row.name == 2: styles = ['color: #CD7F32; font-weight: bold; font-family: Arial'] * len(row)
        return styles
    st.dataframe(stats[['Exibição', 'Qtd', '%']].style.apply(style_top_3, axis=1), column_config={"Exibição": st.column_config.TextColumn(col.capitalize(), width="medium"), "Qtd": st.column_config.ProgressColumn("Qtd", format="%d", min_value=0, max_value=int(stats['Qtd'].max()) if int(stats['Qtd'].max()) > 0 else 100, color=cor), "%": st.column_config.ProgressColumn("%", format="%.0f%%", min_value=0, max_value=100, color=cor)}, hide_index=True, width="stretch")

criar_tabela_exemplo(df_f, 'Requerente', "Exemplo de Tabela", "👤", "blue")

st.write("")
with st.expander("📄 Base de Dados"): st.dataframe(df_f[['Data', 'Requerente', 'Bairro', 'Orgao', 'Status', 'Assunto']], width="stretch")
