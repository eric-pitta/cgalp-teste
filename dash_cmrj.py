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
    mapeamentos = {
        'FREGUESIA': 'FREGUESIA JACAREPAGUA',
        'FREGUESIA DO JACAREPAGUA': 'FREGUESIA JACAREPAGUA',
        'ILHA DE PAQUETA': 'PAQUETA',
        'PAQUETA': 'PAQUETA',
        'RECREIO': 'RECREIO DOS BANDEIRANTES',
        'BARRA': 'BARRA DA TIJUCA'
    }
    if bairro_norm in mapeamentos: bairro_norm = mapeamentos[bairro_norm]
    if bairro_norm in BAIRROS_RJ_COORDS: return BAIRROS_RJ_COORDS[bairro_norm]
    
    geolocator = Nominatim(user_agent="monitoramento_cgalp_cmrj_v2")
    try:
        time.sleep(0.5)
        location = geolocator.geocode(f"{bairro}, Rio de Janeiro, RJ, Brasil", timeout=5)
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
        sources = [
            {"id": "1jgUBYqqpTFwAhT6POV-NRKWwKPzCprmJL4yPDzpQM6M", "gids": [1506037823, 1750823131, 354190818, 530317761]},
            {"id": "1m_fPafrJW1MZq0b_r2C_6Te2GoLlZ3QX9YUikNk0arc", "gids": [1096879621, 2132611364]}
        ]
        df_list = []
        for src in sources:
            spreadsheet = client.open_by_key(src["id"])
            all_worksheets = spreadsheet.worksheets()
            for gid in src["gids"]:
                worksheet = next((ws for ws in all_worksheets if ws.id == gid), None)
                if worksheet:
                    rows = worksheet.get_all_values()
                    if rows:
                        headers = rows[0]
                        counts = {}
                        new_headers = []
                        for h in headers:
                            if not h: h = "COL_VAZIA"
                            if h in counts:
                                counts[h] += 1
                                new_headers.append(f"{h}_{counts[h]}")
                            else:
                                counts[h] = 0
                                new_headers.append(h)
                        temp_df = pd.DataFrame(rows[1:], columns=new_headers)
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
            df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
            df['Ano'] = df['Data'].dt.year.fillna(0).astype(int)
        
        df['Respondido'] = df['DataSaida'].notna() & (df['DataSaida'].astype(str).str.strip() != "") & (df['DataSaida'].astype(str).str.strip() != "0")
        
        for col in ['Requerente', 'Bairro', 'Status']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.upper().replace(['NAN', 'NONE', '', '0', '0.0'], 'NÃO INFORMADO')
        
        if 'Bairro' in df.columns:
            mapeamento_bairros = {
                'ILHA DE PAQUETÁ': 'PAQUETÁ',
                'ILHA DE PAQUETA': 'PAQUETÁ',
                'PAQUETA': 'PAQUETÁ'
            }
            df['Bairro'] = df['Bairro'].replace(mapeamento_bairros)
            
        return df
    except Exception as e:
        st.error(f"Erro na conexão CMRJ: {e}"); return pd.DataFrame()
        df['Respondido'] = df['DataSaida'].notna() & (df['DataSaida'] != "")
        # Limpeza final de strings e Unificação de nomes
        for col in ['Requerente', 'Bairro', 'Status', 'Órgão Demandado', 'Órgão Demandado 2', 'Órgão Demandado 3']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.upper().replace(['NAN', 'NONE', '', '0', '0.0'], 'NÃO INFORMADO')
        
        # Unificação de Bairros Duplicados
        if 'Bairro' in df.columns:
            mapeamento_bairros = {
                'ILHA DE PAQUETÁ': 'PAQUETÁ',
                'ILHA DE PAQUETA': 'PAQUETÁ',
                'PAQUETA': 'PAQUETÁ'
            }
            df['Bairro'] = df['Bairro'].replace(mapeamento_bairros)
            
        return df
    except Exception as e:
        st.error(f"Erro na conexão CMRJ: {e}"); return pd.DataFrame()

def get_organ_stats(df_input):
    o1 = df_input[['Órgão Demandado', 'Respondido']].rename(columns={'Órgão Demandado': 'Orgao'})
    cols_to_check = [c for c in ['Órgão Demandado 2', 'Órgão Demandado 3'] if c in df_input.columns]
    df_parts = [o1]
    for c in cols_to_check:
        df_parts.append(df_input[[c, 'Respondido']].rename(columns={c: 'Orgao'}))
    combined = pd.concat(df_parts, ignore_index=True)
    combined = combined[~combined['Orgao'].isin(['NÃO INFORMADO', 'N/A', 'NA', '', '0', '0.0'])]
    stats = combined.groupby('Orgao').agg(Total=('Respondido', 'count'), Respondidos=('Respondido', 'sum')).reset_index()
    stats['% Respondido'] = (stats['Respondidos'] / stats['Total'] * 100).fillna(0)
    return stats.sort_values('Total', ascending=False).reset_index(drop=True)

def gerar_tabela_html(df_input, coluna_grupo, titulo, icone, cor_classe, is_status=False):
    if df_input.empty: return ""
    if 'Total' in df_input.columns and 'Respondidos' in df_input.columns:
        stats = df_input.copy()
    else:
        stats = df_input.groupby(coluna_grupo).agg(Total=('Respondido', 'count'), Respondidos=('Respondido', 'sum')).reset_index()
    
    stats = stats.sort_values('Total', ascending=False).reset_index(drop=True)
    max_total = stats['Total'].max() if not stats.empty else 1
    
    html = f"<div class='table-header-bar'>{icone} {titulo}</div>"
    html += "<table><thead><tr><th>Exibição</th><th>Qtd Total</th><th>Respondidos</th><th>%</th></tr></thead><tbody>"
    
    for i, row in stats.iterrows():
        medal = ""
        cls = ""
        if not is_status:
            if i == 0: medal = " 🥇"; cls = "top-1"
            elif i == 1: medal = " 🥈"; cls = "top-2"
            elif i == 2: medal = " 🥉"; cls = "top-3"
        else:
            s_up = str(row[coluna_grupo]).upper()
            if s_up in ['SIM', 'CONCLUÍDO', 'ATENDIDO', 'FINALIZADO']: cls = "status-sim"
            elif s_up in ['NÃO', 'EM ATRASO']: cls = "status-nao"
            elif s_up in ['EM ANDAMENTO','PENDENTE' ]: cls = "status-andamento"
            elif s_up in ['PARCIAL', 'AGUARDANDO']: cls = "status-parcial"

        total_val = int(row['Total'])
        resp_val = int(row['Respondidos'])
        perc = (resp_val / total_val * 100) if total_val > 0 else 0
        perc_barra_total = (total_val / max_total * 100)
        
        html += f"<tr>"
        html += f"<td class='{cls}'>{row[coluna_grupo]}{medal}</td>"
        html += f"<td>{total_val}<div class='progress-container'><div class='progress-bar bar-blue' style='width: {perc_barra_total}%; opacity: 0.6;'></div></div></td>"
        html += f"<td>{resp_val}<div class='progress-container'><div class='progress-bar bar-{cor_classe}' style='width: {perc}%;'></div></div></td>"
        html += f"<td>{perc:.1f}%</td>"
        html += f"</tr>"
    
    html += "</tbody></table>"
    return html

def exportar_html_cmrj(df_filtrado, estilo_mapa, titulo_rel):
    try:
        with open("relatorio_legislativo.html", "r", encoding="utf-8") as f: template = f.read()
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
        
        html = template.replace("{{LOGO_BASE64}}", get_base64_logo("logo2.png"))
        html = html.replace("{{MAPA_HTML}}", mapa_html)
        html = html.replace("{{TITULO_RELATORIO}}", titulo_rel)
        html = html.replace("{{LABEL_SOLIC}}", "Indicações")
        html = html.replace("{{TOTAL_SOLIC}}", str(total_sol))
        html = html.replace("{{TOTAL_RESP}}", str(total_resp))
        html = html.replace("{{PERC_RESP}}", f"{perc_total:.1f}")
        html = html.replace("{{TOTAL_BAIRROS}}", str(df_filtrado[~df_filtrado['Bairro'].isin(['NÃO INFORMADO', 'N/A', 'NA', '', '0', '0.0'])]['Bairro'].nunique()))
        
        # --- RESUMO DE FILTROS APLICADOS ---
        filtros_list = []
        anos = sorted(st.session_state.sb_ano_cmrj) if 'sb_ano_cmrj' in st.session_state else []
        if anos: filtros_list.append(f"Anos: {', '.join(map(str, anos))}")
        
        # Filtros TOP X
        if st.session_state.get('sb_top_req') and st.session_state.sb_top_req != "TODOS": filtros_list.append(f"Top {st.session_state.sb_top_req} Requerentes")
        if st.session_state.get('sb_top_org') and st.session_state.sb_top_org != "TODOS": filtros_list.append(f"Top {st.session_state.sb_top_org} Órgãos")
        if st.session_state.get('sb_top_bairro') and st.session_state.sb_top_bairro != "TODOS": filtros_list.append(f"Top {st.session_state.sb_top_bairro} Bairros")
        if st.session_state.get('sb_top_status') and st.session_state.sb_top_status != "TODOS": filtros_list.append(f"Top {st.session_state.sb_top_status} Situações")

        # Filtros Multiselect
        if st.session_state.get('sb_req_cmrj'): filtros_list.append(f"Requerentes: {', '.join(st.session_state.sb_req_cmrj)}")
        if st.session_state.get('sb_org_cmrj'): filtros_list.append(f"Órgãos: {', '.join(st.session_state.sb_org_cmrj)}")
        if st.session_state.get('sb_bairro_cmrj'): filtros_list.append(f"Bairros: {', '.join(st.session_state.sb_bairro_cmrj)}")
        if st.session_state.get('sb_status_cmrj'): filtros_list.append(f"Situações: {', '.join(st.session_state.sb_status_cmrj)}")
        
        if st.session_state.get('click_req'): filtros_list.append(f"Filtro Gráfico (Vereador): {st.session_state.click_req}")
        if st.session_state.get('click_org'): filtros_list.append(f"Filtro Gráfico (Órgão): {st.session_state.click_org}")
        if st.session_state.get('click_bairro'): filtros_list.append(f"Filtro Gráfico (Bairro): {st.session_state.click_bairro}")
        
        periodo = " | ".join(filtros_list) if filtros_list else "Relatório Geral"
        html = html.replace("{{PERIODO}}", periodo)
        
        tab_html = gerar_tabela_html(df_filtrado, 'Requerente', "Demandas por Vereador", "👤", 'blue')
        org_stats_df = get_organ_stats(df_filtrado)
        if not org_stats_df.empty:
            tab_html += gerar_tabela_html(org_stats_df, 'Orgao', "Demandas por Órgão", "🏢", 'green')
        tab_html += gerar_tabela_html(df_filtrado[~df_filtrado['Bairro'].isin(['NÃO INFORMADO', 'N/A', 'NA', '', '0', '0.0'])], 'Bairro', "Indicações por Bairro", "📍", 'violet')
        
        status_stats = df_filtrado.groupby('Status').agg(Total=('Respondido', 'count'), Respondidos=('Respondido', 'sum')).reset_index().sort_values('Total', ascending=False)
        tab_html += gerar_tabela_html(status_stats, 'Status', "Situação das Indicações", "📌", 'orange', is_status=True)
        
        html = html.replace("{{TABELAS_HTML}}", tab_html)
        return html
    except Exception as e: return f"Erro ao gerar relatório: {e}"

# --- CARREGAMENTO DE DADOS ---
df = load_data()
if df.empty: st.stop()

# --- ESTADO DE SESSÃO INICIAL ---
for key in ['click_req', 'click_org', 'click_bairro']:
    if key not in st.session_state: st.session_state[key] = None

# --- SIDEBAR FILTROS ---
def limpar_filtros_cmrj():
    for k in ['click_req', 'click_org', 'click_bairro', 'sb_ano_cmrj', 'sb_req_cmrj', 'sb_org_cmrj', 'sb_bairro_cmrj', 'sb_status_cmrj', 'sb_top_req', 'sb_top_org', 'sb_top_bairro', 'sb_top_status']:
        if k in st.session_state: del st.session_state[k]

with st.sidebar:
    st.button("Limpar Filtros", on_click=limpar_filtros_cmrj)
    st.divider()
    
    anos_dis = sorted([int(a) for a in df['Ano'].unique() if a > 0])
    st.multiselect("Filtrar por Ano", anos_dis, default=anos_dis, key="sb_ano_cmrj")
    st.divider()

    st.subheader("Filtro por TOP X")
    top_options = ["TODOS", 5, 10, 15, 20, 30, 50]
    st.selectbox("Top Requerente", top_options, key="sb_top_req")
    st.selectbox("Top Órgão", top_options, key="sb_top_org")
    st.selectbox("Top Bairro", top_options, key="sb_top_bairro")
    st.selectbox("Top Situação", top_options, key="sb_top_status")
    st.divider()

    st.multiselect("Requerente", sorted(df['Requerente'].unique().tolist()), key="sb_req_cmrj")
    
    # Coletar lista única de órgãos para o filtro
    lista_orgaos = sorted(list(set(df['Órgão Demandado'].unique().tolist() + df['Órgão Demandado 2'].unique().tolist() + df['Órgão Demandado 3'].unique().tolist())))
    if 'NÃO INFORMADO' in lista_orgaos: lista_orgaos.remove('NÃO INFORMADO')
    st.multiselect("Órgão Demandado", lista_orgaos, key="sb_org_cmrj")
    
    st.multiselect("Bairro", sorted(df['Bairro'].unique().tolist()), key="sb_bairro_cmrj")
    st.multiselect("Situação", sorted(df['Status'].unique().tolist()), key="sb_status_cmrj")
    st.divider()
    
    estilo_mapa = st.selectbox("Mapa", ["carto-positron", "open-street-map", "carto-darkmatter"], key="sb_mapa_cmrj")
    st.divider()

# --- APLICAÇÃO FILTROS ---
df_f = df.copy()

# 1. Filtro de Ano (Sempre primeiro)
if 'sb_ano_cmrj' in st.session_state and st.session_state.sb_ano_cmrj: 
    df_f = df_f[df_f['Ano'].isin(st.session_state.sb_ano_cmrj)]

# --- CÁLCULO DE RANKING ABSOLUTO (PÓS-ANO) PARA MEDALHAS ---
top_3_req_global = df_f['Requerente'].value_counts().nlargest(3).index.tolist()
top_3_bairro_global = df_f[~df_f['Bairro'].isin(['NÃO INFORMADO', 'N/A', 'NA', '', '0', '0.0'])]['Bairro'].value_counts().nlargest(3).index.tolist()
org_stats_global = get_organ_stats(df_f)
top_3_org_global = org_stats_global['Orgao'].head(3).tolist()

# 2. Filtros TOP X
if st.session_state.get('sb_top_req') and st.session_state.sb_top_req != "TODOS":
    top_n = st.session_state.sb_top_req
    top_list = df_f['Requerente'].value_counts().nlargest(top_n).index.tolist()
    df_f = df_f[df_f['Requerente'].isin(top_list)]

if st.session_state.get('sb_top_org') and st.session_state.sb_top_org != "TODOS":
    top_n = st.session_state.sb_top_org
    org_counts = pd.concat([df_f['Órgão Demandado'], df_f['Órgão Demandado 2'], df_f['Órgão Demandado 3']]).value_counts()
    if 'NÃO INFORMADO' in org_counts: org_counts = org_counts.drop('NÃO INFORMADO')
    top_list = org_counts.nlargest(top_n).index.tolist()
    df_f = df_f[(df_f['Órgão Demandado'].isin(top_list)) | (df_f['Órgão Demandado 2'].isin(top_list)) | (df_f['Órgão Demandado 3'].isin(top_list))]

if st.session_state.get('sb_top_bairro') and st.session_state.sb_top_bairro != "TODOS":
    top_n = st.session_state.sb_top_bairro
    top_list = df_f[~df_f['Bairro'].isin(['NÃO INFORMADO', 'N/A', 'NA', '', '0', '0.0'])]['Bairro'].value_counts().nlargest(top_n).index.tolist()
    df_f = df_f[df_f['Bairro'].isin(top_list)]

if st.session_state.get('sb_top_status') and st.session_state.sb_top_status != "TODOS":
    top_n = st.session_state.sb_top_status
    top_list = df_f['Status'].value_counts().nlargest(top_n).index.tolist()
    df_f = df_f[df_f['Status'].isin(top_list)]

# 3. Filtros Multiselect (Sidebar)
if 'sb_req_cmrj' in st.session_state and st.session_state.sb_req_cmrj: 
    df_f = df_f[df_f['Requerente'].isin(st.session_state.sb_req_cmrj)]

if 'sb_org_cmrj' in st.session_state and st.session_state.sb_org_cmrj:
    org_sels = st.session_state.sb_org_cmrj
    df_f = df_f[(df_f['Órgão Demandado'].isin(org_sels)) | (df_f['Órgão Demandado 2'].isin(org_sels)) | (df_f['Órgão Demandado 3'].isin(org_sels))]

if 'sb_bairro_cmrj' in st.session_state and st.session_state.sb_bairro_cmrj: 
    df_f = df_f[df_f['Bairro'].isin(st.session_state.sb_bairro_cmrj)]

if 'sb_status_cmrj' in st.session_state and st.session_state.sb_status_cmrj: 
    df_f = df_f[df_f['Status'].isin(st.session_state.sb_status_cmrj)]

# 4. Filtros de Clique (Tabelas e Mapa)
if 'click_req' in st.session_state and st.session_state.click_req: 
    req_list = st.session_state.click_req if isinstance(st.session_state.click_req, list) else [st.session_state.click_req]
    df_f = df_f[df_f['Requerente'].isin(req_list)]

if 'click_org' in st.session_state and st.session_state.click_org: 
    org_list = st.session_state.click_org if isinstance(st.session_state.click_org, list) else [st.session_state.click_org]
    df_f = df_f[(df_f['Órgão Demandado'].isin(org_list)) | (df_f['Órgão Demandado 2'].isin(org_list)) | (df_f['Órgão Demandado 3'].isin(org_list))]

if 'click_bairro' in st.session_state and st.session_state.click_bairro: 
    bairro_list = st.session_state.click_bairro if isinstance(st.session_state.click_bairro, list) else [st.session_state.click_bairro]
    df_f = df_f[df_f['Bairro'].isin(bairro_list)]

# Título dinâmico
anos_lista = ", ".join([str(a) for a in sorted(st.session_state.sb_ano_cmrj)]) if 'sb_ano_cmrj' in st.session_state and st.session_state.sb_ano_cmrj else "Geral"
titulo_dinamico = f"CMRJ - Indicações Legislativas ({anos_lista})"

# Botão de Relatório
with st.sidebar:
    if st.button("Preparar Relatório"):
        with st.spinner("Gerando..."):
            rel_html = exportar_html_cmrj(df_f.copy(), estilo_mapa, titulo_dinamico)
            st.download_button(label="📥 Baixar Relatório Legislativo", data=rel_html, file_name="relatorio_cmrj.html", mime="text/html")

# --- TÍTULO DINÂMICO UI ---
st.markdown(f"<h1 class='main-title'>{titulo_dinamico}</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 2px; font-size: 0.8rem; margin-bottom: 30px;'>COORDENADORIA GERAL DE ACOMPANHAMENTO LEGISLATIVO E PARLAMENTAR</p>", unsafe_allow_html=True)

# --- CONTEÚDO ---
st.markdown("<div class='section-header'>🗺️ Geolocalização de demandas</div>", unsafe_allow_html=True)
map_counts = df_f[~df_f['Bairro'].isin(['NÃO INFORMADO', 'N/A', 'NA', '', '0', '0.0'])]['Bairro'].value_counts().reset_index()
map_counts.columns = ['Bairro', 'Quantidade']
with st.spinner("Mapeando..."):
    map_counts['coords'] = map_counts['Bairro'].apply(obter_coordenadas)
    map_counts['lat'] = map_counts['coords'].apply(lambda x: x[0] if x else None)
    map_counts['lon'] = map_counts['coords'].apply(lambda x: x[1] if x else None)
map_ready = map_counts.dropna(subset=['lat', 'lon'])
if not map_ready.empty:
    fig = px.scatter_mapbox(map_ready, lat="lat", lon="lon", size="Quantidade", hover_name="Bairro", color="Quantidade", color_continuous_scale='Plasma', size_max=40, zoom=10, mapbox_style=st.session_state.sb_mapa_cmrj)
    fig.update_layout(height=550, margin={"r":0,"t":0,"l":0,"b":0}, clickmode='event+select')
    sel_map = st.plotly_chart(fig, width="stretch", on_select="rerun")
    if sel_map and sel_map["selection"]["points"]:
        st.session_state.click_bairro = sel_map["selection"]["points"][0]["hovertext"]; st.rerun()

st.write("")
m = st.columns(5)
total_ind = len(df_f)
total_resp = int(df_f['Respondido'].sum())
perc_resp = (total_resp / total_ind * 100) if total_ind > 0 else 0
metrics = [
    ("Indicações", total_ind), 
    ("Respondidos", total_resp), 
    ("% Respondido", f"{perc_resp:.1f}%"),
    ("Vereadores", df_f['Requerente'].nunique()), 
    ("Bairros", df_f['Bairro'].nunique())
]
for i, (l, v) in enumerate(metrics):
    with m[i]: st.markdown(f"<div class='metric-card'><div class='metric-label'>{l}</div><div class='metric-value'>{v}</div></div>", unsafe_allow_html=True)

def criar_tabela(df_input, col, titulo, icone, key, cor):
    if df_input.empty: return
    stats = df_input.groupby(col).agg(Qtd=('Respondido', 'count'), Resp=('Respondido', 'sum')).reset_index()
    stats['% Respondido'] = (stats['Resp'] / stats['Qtd'] * 100).fillna(0); stats = stats.sort_values('Qtd', ascending=False).reset_index(drop=True)
    
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

    # Tabela com seleção robusta
    key_table = f"table_{key}"
    sel = st.dataframe(
        stats[[col, "Exibição", 'Qtd', '% Respondido']].style.apply(style_top_3, axis=1), 
        column_config={
            col: None, 
            "Exibição": st.column_config.TextColumn(col, width="medium"), 
            "Qtd": st.column_config.ProgressColumn("Qtd", format="%d", min_value=0, max_value=int(stats['Qtd'].max()) if int(stats['Qtd'].max()) > 0 else 100, color=cor), 
            "% Respondido": st.column_config.ProgressColumn("% Respondido", format="%.0f%%", min_value=0, max_value=100, color=cor)
        }, 
        hide_index=True, width="stretch",
        on_select="rerun",
        selection_mode="multi-row",
        key=key_table
    )

    # Lógica de seleção imediata
    selecionados = sel.get("selection", {}).get("rows", [])

    if selecionados:
        if st.button(f"✅ Filtrar {col} ({len(selecionados)})", key=f"btn_{key}", use_container_width=True):
            st.session_state[key] = [stats.iloc[i][col] for i in selecionados]
            st.rerun()
    elif st.session_state.get(key):
        if st.button(f"❌ Limpar Filtro {col}", key=f"btn_clr_{key}", use_container_width=True):
            st.session_state[key] = None
            st.rerun()

criar_tabela(df_f, 'Requerente', "Demandas por Vereador", "👤", 'click_req', "blue")

# Tabela de Órgãos Estilizada
org_stats = get_organ_stats(df_f)

# --- ISOLAMENTO VISUAL DO FILTRO DE ÓRGÃO ---
if st.session_state.get('click_org'):
    org_stats = org_stats[org_stats['Orgao'].isin(st.session_state.click_org)]

st.markdown(f"<div class='table-header-bar'>🏢 Demandas por Órgão</div>", unsafe_allow_html=True)
def stylize_org(name, index):
    medal = ""
    if index == 0: medal = " 🥇"
    elif index == 1: medal = " 🥈"
    elif index == 2: medal = " 🥉"
    return f"{name}{medal}"
org_stats['Exibição'] = [stylize_org(row['Orgao'], i) for i, row in org_stats.iterrows()]

def style_org_top_3(row):
    styles = [''] * len(row)
    if row.name == 0: styles = ['color: #FFD700; font-weight: bold; font-family: Arial'] * len(row)
    elif row.name == 1: styles = ['color: #C0C0C0; font-weight: bold; font-family: Arial'] * len(row)
    elif row.name == 2: styles = ['color: #CD7F32; font-weight: bold; font-family: Arial'] * len(row)
    return styles

key_org = "table_org"
sel_org = st.dataframe(
    org_stats[["Orgao", "Exibição", "Total", "% Respondido"]].style.apply(style_org_top_3, axis=1), 
    column_config={
        "Orgao": None,
        "Exibição": st.column_config.TextColumn("Órgão", width="medium"), 
        "Total": st.column_config.ProgressColumn("Total", format="%d", min_value=0, max_value=int(org_stats['Total'].max() if not org_stats.empty else 1), color="green"),
        "% Respondido": st.column_config.ProgressColumn("% Respondido", format="%.0f%%", min_value=0, max_value=100, color="green")
    }, 
    hide_index=True, width="stretch",
    selection_mode="multi-row",
    on_select="rerun",
    key=key_org
)

# Lógica do botão para Órgão
selecionados_org = sel_org.get("selection", {}).get("rows", [])

if selecionados_org:
    if st.button(f"✅ Filtrar Órgão ({len(selecionados_org)})", key="btn_org_apply", use_container_width=True):
        st.session_state.click_org = [org_stats.iloc[i]['Orgao'] for i in selecionados_org]
        st.rerun()
elif st.session_state.get('click_org'):
    if st.button("❌ Limpar Filtro Órgão", key="btn_org_clear", use_container_width=True):
        st.session_state.click_org = None
        st.rerun()

criar_tabela(df_f[~df_f['Bairro'].isin(['NÃO INFORMADO', 'N/A', 'NA', '', '0', '0.0'])], 'Bairro', "Indicações por Bairro", "📍", 'click_bairro', "violet")

st.markdown("<div class='section-header'>📌 Conclusão das demandas</div>", unsafe_allow_html=True)
if not df_f.empty:
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
