import streamlit as st
import pandas as pd
import plotly.express as px
import os
import unicodedata
import base64
import io

# Configuração da Página
st.set_page_config(page_title="Monitoramento CGALP", layout="wide", page_icon="📊")

# --- INJEÇÃO DE CSS PARA VISUAL TECH/MODERNO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    html, body, [data-testid="stSidebar"] {
        font-family: 'Inter', sans-serif;
    }

    /* Estilo dos Títulos de Seção */
    .section-header {
        font-size: 1.4rem;
        font-weight: 800;
        color: #113359;
        border-left: 6px solid #5CA0D3;
        padding-left: 15px;
        margin-top: 2rem;
        margin-bottom: 1rem;
        letter-spacing: -0.5px;
    }

    /* Container das Tabelas (Dataframes) */
    .stDataFrame {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }

    /* Cartões de Métricas Customizados */
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #f1f5f9;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        text-align: center;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        border-color: #5CA0D3;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 1.8rem;
        color: #1e293b;
        font-weight: 800;
    }

    /* Divider estilizado */
    hr {
        margin: 2em 0;
        border: 0;
        border-top: 1px solid #f1f5f9;
    }
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

@st.cache_data
def load_data():
    excel_file = 'Solicitações - Câmara dos Deputados.xlsx'
    if not os.path.exists(excel_file): return pd.DataFrame()
    try:
        df_dict = pd.read_excel(excel_file, sheet_name=None)
        df_list = []
        for sheet_name, temp_df in df_dict.items():
            if "Produtividade" in sheet_name: continue
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
        df = pd.concat(df_list, ignore_index=True)
        if 'Data' in df.columns:
            df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
            df['Ano'] = df['Data'].dt.year
        df['Respondido'] = df['DataSaida'].notna()
        for col in ['Requerente', 'Orgao', 'Bairro', 'Status']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.upper()
                df[col] = df[col].replace(['NAN', 'NONE', ''], 'NÃO INFORMADO')
        return df
    except Exception as e:
        st.error(f"Erro ao carregar Excel: {e}")
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
        html_items += f"""
        <div class="chart-row">
            <div class="chart-label">
                <span>{row[coluna_grupo]}</span>
                <span class="stats-info">{int(row['Respondidos'])} respondidos de {int(row['Total'])}</span>
            </div>
            <div class="bar-outer">
                <div class="bar-inner-total bar-{cor_classe}-light" style="width: {perc_total}%;"></div>
                <div class="bar-inner-respondido bar-{cor_classe}-dark" style="width: {perc_resp}%;"></div>
            </div>
        </div>"""
    return html_items

def exportar_html(df_filtrado, estilo_mapa):
    try:
        with open("relatorio.html", "r", encoding="utf-8") as f:
            template = f.read()
        
        counts = df_filtrado[df_filtrado['Bairro'] != 'NÃO INFORMADO']['Bairro'].value_counts().reset_index()
        counts.columns = ['Bairro', 'Quantidade']
        counts['lat'] = counts['Bairro'].apply(lambda b: BAIRROS_RJ_COORDS.get(normalizar(b), [None, None])[0])
        counts['lon'] = counts['Bairro'].apply(lambda b: BAIRROS_RJ_COORDS.get(normalizar(b), [None, None])[1])
        map_final = counts.dropna(subset=['lat', 'lon'])
        
        fig_print = px.scatter_mapbox(map_final, lat="lat", lon="lon", size="Quantidade", 
                                    color="Quantidade", color_continuous_scale='Plasma', size_max=20,
                                    mapbox_style=estilo_mapa)
        fig_print.update_layout(mapbox=dict(center=dict(lat=-22.915, lon=-43.44), zoom=9.2), coloraxis_colorbar=dict(orientation='h', y=-0.1), margin=dict(l=0, r=0, t=0, b=0))
        
        mapa_html = fig_print.to_html(full_html=False, include_plotlyjs='cdn')
        
        html = template.replace("{{LOGO_BASE64}}", get_base64_logo("logo.png"))
        html = html.replace('<img src="data:image/png;base64,{{MAPA_BASE64}}" alt="Mapa de Incidências">', mapa_html)
        html = html.replace("{{TOTAL_SOLIC}}", str(len(df_filtrado)))
        html = html.replace("{{TOTAL_RESP}}", str(int(df_filtrado['Respondido'].sum())))
        html = html.replace("{{TOTAL_BAIRROS}}", str(df_filtrado['Bairro'].nunique()))
        html = html.replace("{{DATA_GERACAO}}", pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"))
        html = html.replace("{{PERIODO}}", "Relatório Filtrado" if any([st.session_state.click_req, st.session_state.click_org]) else "Geral")
        
        html = html.replace("{{CHART_REQUERENTES}}", gerar_grafico_html(df_filtrado, 'Requerente', 'blue'))
        html = html.replace("{{CHART_ORGAOS}}", gerar_grafico_html(df_filtrado, 'Orgao', 'green'))
        html = html.replace("{{CHART_BAIRROS}}", gerar_grafico_html(df_filtrado[df_filtrado['Bairro'] != 'NÃO INFORMADO'], 'Bairro', 'violet'))
        
        status_stats = df_filtrado.groupby('Status').size().reset_index(name='Qtd').sort_values('Qtd', ascending=False)
        max_s = status_stats['Qtd'].max() if not status_stats.empty else 1
        status_html = ""
        for _, row in status_stats.iterrows():
            p = (row['Qtd'] / max_s * 100)
            status_html += f'<div class="chart-row"><div class="chart-label"><span>{row["Status"]}</span><span>{row["Qtd"]}</span></div><div class="bar-outer"><div class="bar-inner-respondido bar-orange-dark" style="width: {p}%;"></div></div></div>'
        html = html.replace("{{CHART_STATUS}}", status_html)
        
        return html
    except Exception as e:
        return f"Erro ao gerar: {e}"

# ----------------- UI -----------------
col_logo, col_title = st.columns([1, 3])
with col_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=1000)
with col_title:
    st.write(""); st.write(""); st.write("")
    st.markdown("<h1 style='text-align: center; color: #113359; font-family: Inter, sans-serif; font-weight: 800;'>Monitoramento Legislativo</h1>", unsafe_allow_html=True)

df = load_data()
if df.empty: st.error("Arquivo Excel não encontrado."); st.stop()

# ESTADO DE SESSÃO
for key in ['click_req', 'click_org', 'click_bairro', 'click_status']:
    if key not in st.session_state: st.session_state[key] = None

# Sidebar
st.sidebar.header("🔍 Painel de Controle")
anos = sorted(df['Ano'].dropna().unique().tolist())
ano_sel = st.sidebar.multiselect("Filtrar por Ano", anos, default=anos)

# APLICAÇÃO FILTROS
df_f = df.copy()
if ano_sel: df_f = df_f[df_f['Ano'].isin(ano_sel)]
if st.session_state.click_req: df_f = df_f[df_f['Requerente'] == st.session_state.click_req]
if st.session_state.click_org: df_f = df_f[df_f['Orgao'] == st.session_state.click_org]
if st.session_state.click_bairro: df_f = df_f[df_f['Bairro'] == st.session_state.click_bairro]
if st.session_state.click_status: df_f = df_f[df_f['Status'] == st.session_state.click_status]

estilo_mapa = st.sidebar.selectbox("Estilo do Mapa", ["open-street-map", "carto-positron", "carto-darkmatter"], index=0)

st.sidebar.divider()
st.sidebar.subheader("📄 Exportação")
if st.sidebar.button("Preparar Relatório Executivo"):
    with st.spinner("Compilando dados..."):
        rel_html = exportar_html(df_f, estilo_mapa)
        st.sidebar.success("✅ Pronto!")
        st.sidebar.download_button(label="📥 Baixar Relatório", data=rel_html, file_name="relatorio_cgalp.html", mime="text/html")

if st.sidebar.button("Limpar Todos os Filtros"):
    st.session_state.click_req = st.session_state.click_org = st.session_state.click_bairro = st.session_state.click_status = None
    st.rerun()

# --- MAPA ---
st.markdown("<div class='section-header'>🗺️ Geocalização de Demandas</div>", unsafe_allow_html=True)
map_df_base = df_f[df_f['Bairro'] != 'NÃO INFORMADO']['Bairro'].value_counts().reset_index()
map_df_base.columns = ['Bairro', 'Quantidade']
map_df_base['lat_lon'] = map_df_base['Bairro'].apply(lambda x: BAIRROS_RJ_COORDS.get(normalizar(x), [None, None]))
map_df_base['lat'] = [c[0] for c in map_df_base['lat_lon']]
map_df_base['lon'] = [c[1] for c in map_df_base['lat_lon']]
map_ready = map_df_base.dropna(subset=['lat', 'lon']).copy()

fig_map = px.scatter_mapbox(map_ready, lat="lat", lon="lon", size="Quantidade", hover_name="Bairro", color="Quantidade", color_continuous_scale='Plasma', size_max=40, zoom=10, mapbox_style=estilo_mapa)
fig_map.update_layout(height=500, margin={"r":0,"t":0,"l":0,"b":0}, clickmode='event+select')
sel_map = st.plotly_chart(fig_map, use_container_width=True, on_select="rerun")
if sel_map and sel_map["selection"]["points"]:
    st.session_state.click_bairro = sel_map["selection"]["points"][0]["hovertext"]
    st.rerun()

# --- MÉTRICAS CUSTOMIZADAS ---
st.write("")
m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
with m_col1: st.markdown(f"<div class='metric-card'><div class='metric-label'>Solicitações</div><div class='metric-value'>{len(df_f)}</div></div>", unsafe_allow_html=True)
with m_col2: st.markdown(f"<div class='metric-card'><div class='metric-label'>Respondidos</div><div class='metric-value'>{int(df_f['Respondido'].sum())}</div></div>", unsafe_allow_html=True)
with m_col3: st.markdown(f"<div class='metric-card'><div class='metric-label'>Requerentes</div><div class='metric-value'>{df_f['Requerente'].nunique()}</div></div>", unsafe_allow_html=True)
with m_col4: st.markdown(f"<div class='metric-card'><div class='metric-label'>Órgãos</div><div class='metric-value'>{df_f['Orgao'].nunique()}</div></div>", unsafe_allow_html=True)
with m_col5: st.markdown(f"<div class='metric-card'><div class='metric-label'>Bairros</div><div class='metric-value'>{df_f['Bairro'].nunique()}</div></div>", unsafe_allow_html=True)

# --- INFOGRÁFICOS ---
def criar_infografico(df_input, coluna_grupo, titulo, key_session, cor_barra):
    if df_input.empty: return
    stats = df_input.groupby(coluna_grupo).agg(Quantidade=('Respondido', 'count'), Respondidos=('Respondido', 'sum')).reset_index()
    stats['% Respondido'] = (stats['Respondidos'] / stats['Quantidade'] * 100).fillna(0)
    stats = stats.sort_values('Quantidade', ascending=False)
    st.markdown(f"<div class='section-header'>{titulo}</div>", unsafe_allow_html=True)
    sel = st.dataframe(stats[[coluna_grupo, 'Quantidade', '% Respondido']], column_config={coluna_grupo: st.column_config.TextColumn(coluna_grupo.capitalize(), width="medium"), "Quantidade": st.column_config.ProgressColumn("Quantidade", format="%d", min_value=0, max_value=int(stats['Quantidade'].max()) if int(stats['Quantidade'].max()) > 0 else 100, color=cor_barra), "% Respondido": st.column_config.ProgressColumn("% Respondido", format="%.0f%%", min_value=0, max_value=100, color=cor_barra)}, hide_index=True, use_container_width=True, on_select="rerun")
    if sel and sel["selection"]["rows"]:
        st.session_state[key_session] = stats.iloc[sel["selection"]["rows"][0]][coluna_grupo]
        st.rerun()

criar_infografico(df_f, 'Requerente', "👤 Desempenho por Requerente", 'click_req', "blue")
criar_infografico(df_f, 'Orgao', "🏢 Desempenho por Órgão", 'click_org', "green")
criar_infografico(df_f[df_f['Bairro'] != 'NÃO INFORMADO'], 'Bairro', "📍 Solicitações por Bairro", 'click_bairro', "violet")

st.markdown("<div class='section-header'>📌 Situação dos Atendimentos</div>", unsafe_allow_html=True)
if not df_f.empty:
    status_counts = df_f['Status'].value_counts().reset_index()
    status_counts.columns = ['Status_Label', 'Quantidade']
    color_map = {'CONCLUÍDO': '#00CC96', 'ATENDIDO': '#00CC96', 'FINALIZADO': '#00CC96', 'PENDENTE': '#EF553B', 'EM ANDAMENTO': '#636EFA', 'AGUARDANDO': '#FFA15A', 'NÃO INFORMADO': '#94a3b8'}
    fig_status = px.bar(status_counts, x='Quantidade', y='Status_Label', orientation='h', color='Status_Label', color_discrete_map=color_map, text='Quantidade')
    fig_status.update_traces(textposition='outside', marker_line_width=0, opacity=0.9)
    fig_status.update_layout(height=400, showlegend=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis_showgrid=False, yaxis_showgrid=False, xaxis_visible=False, yaxis_title="", margin=dict(l=0, r=50, t=10, b=0), clickmode='event+select')
    sel_s = st.plotly_chart(fig_status, use_container_width=True, on_select="rerun")
    if sel_s and sel_s["selection"]["points"]:
        st.session_state.click_status = sel_s["selection"]["points"][0]["y"]
        st.rerun()

st.write("")
with st.expander("📄 Base de Dados Completa"):
    st.dataframe(df_f[['Data', 'Requerente', 'Bairro', 'Orgao', 'Status', 'Assunto']], use_container_width=True)
