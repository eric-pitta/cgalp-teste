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
    'COELHO NETO': [-22.8275, -43.3442]
}

@st.cache_data(show_spinner=False)
def obter_coordenadas(bairro):
    bairro_norm = normalizar(bairro)
    if bairro_norm in BAIRROS_RJ_COORDS: return BAIRROS_RJ_COORDS[bairro_norm]
    geolocator = Nominatim(user_agent="monitoramento_cgalp_solicitacoes_v5")
    try:
        time.sleep(1)
        location = geolocator.geocode(f"{bairro}, Rio de Janeiro, RJ, Brasil")
        if location: return [location.latitude, location.longitude]
    except: pass
    return [None, None]

# --- CARREGAMENTO GOOGLE SHEETS CMRJ SOLICITAÇÕES ---
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
            {"id": "1wDsLBfJM02h7k46SAAt4VfZCinRmksInwrZ-1nUiSZ0", "gids": [610770331, 1644653035, 604141893, 1190526723]},
            {"id": "14tZprRR9h8iey2j2NY06vrO2PfQ-DTU4Du1P_PIRgXg", "gids": [650094796, 1474842227]}
        ]
        
        df_list = []
        for src in sources:
            spreadsheet = client.open_by_key(src["id"])
            all_worksheets = spreadsheet.worksheets()
            for gid in src["gids"]:
                worksheet = next((ws for ws in all_worksheets if ws.id == gid), None)
                if worksheet:
                    rows = worksheet.get_all_values()
                    if len(rows) > 1:
                        headers = rows[0]
                        temp_df = pd.DataFrame(rows[1:], columns=headers)
                        
                        # Mapeamento dinâmico baseado em normalização
                        for actual_col in temp_df.columns:
                            norm_col = normalizar(actual_col)
                            if norm_col in [normalizar('Data de Recebimento'), normalizar('Data de Chegada')]: temp_df.rename(columns={actual_col: 'Data'}, inplace=True)
                            elif norm_col == normalizar('Ementa'): temp_df.rename(columns={actual_col: 'Assunto'}, inplace=True)
                            elif norm_col == normalizar('Vereador Requerente'): temp_df.rename(columns={actual_col: 'Requerente'}, inplace=True)
                            elif norm_col == normalizar('Órgão Requerido'): temp_df.rename(columns={actual_col: 'Órgão Demandado'}, inplace=True)
                            elif norm_col == normalizar('Órgão Requerido 2'): temp_df.rename(columns={actual_col: 'Órgão Demandado 2'}, inplace=True)
                            elif norm_col == normalizar('Órgão Requerido 3'): temp_df.rename(columns={actual_col: 'Órgão Demandado 3'}, inplace=True)
                            elif norm_col == normalizar('Bairro da Ocorrência'): temp_df.rename(columns={actual_col: 'Bairro'}, inplace=True)
                            elif norm_col in [normalizar('Concluído'), normalizar('Atendimento')]: temp_df.rename(columns={actual_col: 'Status'}, inplace=True)
                            elif norm_col in [normalizar('Data da Saída'), normalizar('Data de Saída'), normalizar('Data Saida')]: temp_df.rename(columns={actual_col: 'DataSaida'}, inplace=True)
                        
                        # Garantir colunas essenciais
                        for col in ['Data', 'Assunto', 'Requerente', 'Bairro', 'Status', 'DataSaida', 'Órgão Demandado']:
                            if col not in temp_df.columns: temp_df[col] = ""
                                
                        df_list.append(temp_df)
        
        if not df_list: return pd.DataFrame()
        df = pd.concat(df_list, ignore_index=True)
        
        if 'Data' in df.columns:
            df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
            df['Ano'] = df['Data'].dt.year.fillna(0).astype(int)
        
        # Respondido se houver qualquer valor em DataSaida diferente de vazio/zero
        df['Respondido'] = df['DataSaida'].notna() & (df['DataSaida'].astype(str).str.strip() != "") & (df['DataSaida'].astype(str).str.strip() != "0")
        
        # Limpeza final de strings e Unificação
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
        st.error(f"Erro na conexão CMRJ Solicitações: {e}"); return pd.DataFrame()

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
            elif s_up in ['EM ANDAMENTO','PENDENTE', 'ABERTO' ]: cls = "status-andamento"
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
        html = html.replace("{{LABEL_SOLIC}}", "Solicitações")
        html = html.replace("{{TOTAL_SOLIC}}", str(total_sol))
        html = html.replace("{{TOTAL_RESP}}", str(total_resp))
        html = html.replace("{{PERC_RESP}}", f"{perc_total:.1f}")
        html = html.replace("{{TOTAL_BAIRROS}}", str(df_filtrado[~df_filtrado['Bairro'].isin(['NÃO INFORMADO', 'N/A', 'NA', '', '0', '0.0'])]['Bairro'].nunique()))
        
        # --- RESUMO DE FILTROS APLICADOS ---
        filtros_list = []
        anos = sorted(st.session_state.sb_ano_sol) if 'sb_ano_sol' in st.session_state else []
        if anos: filtros_list.append(f"Anos: {', '.join(map(str, anos))}")
        
        # Filtros TOP X
        if st.session_state.get('sb_top_req') and st.session_state.sb_top_req != "TODOS": filtros_list.append(f"Top {st.session_state.sb_top_req} Requerentes")
        if st.session_state.get('sb_top_org') and st.session_state.sb_top_org != "TODOS": filtros_list.append(f"Top {st.session_state.sb_top_org} Órgãos")
        if st.session_state.get('sb_top_bairro') and st.session_state.sb_top_bairro != "TODOS": filtros_list.append(f"Top {st.session_state.sb_top_bairro} Bairros")
        if st.session_state.get('sb_top_status') and st.session_state.sb_top_status != "TODOS": filtros_list.append(f"Top {st.session_state.sb_top_status} Situações")

        # Filtros Multiselect
        if st.session_state.get('sb_req_sol'): filtros_list.append(f"Requerentes: {', '.join(st.session_state.sb_req_sol)}")
        if st.session_state.get('sb_org_sol'): filtros_list.append(f"Órgãos: {', '.join(st.session_state.sb_org_sol)}")
        if st.session_state.get('sb_bairro_sol'): filtros_list.append(f"Bairros: {', '.join(st.session_state.sb_bairro_sol)}")
        if st.session_state.get('sb_status_sol'): filtros_list.append(f"Situações: {', '.join(st.session_state.sb_status_sol)}")
        
        if st.session_state.get('click_req_sol'): filtros_list.append(f"Filtro Gráfico (Vereador): {st.session_state.click_req_sol}")
        if st.session_state.get('click_org_sol'): filtros_list.append(f"Filtro Gráfico (Órgão): {st.session_state.click_org_sol}")
        if st.session_state.get('click_bairro_sol'): filtros_list.append(f"Filtro Gráfico (Bairro): {st.session_state.click_bairro_sol}")
        
        periodo = " | ".join(filtros_list) if filtros_list else "Relatório Geral"
        html = html.replace("{{PERIODO}}", periodo)
        
        tab_html = gerar_tabela_html(df_filtrado, 'Requerente', "Demandas por Vereador", "👤", 'blue')
        org_stats_df = get_organ_stats(df_filtrado)
        if not org_stats_df.empty:
            tab_html += gerar_tabela_html(org_stats_df, 'Orgao', "Demandas por Órgão", "🏢", 'green')
        tab_html += gerar_tabela_html(df_filtrado[~df_filtrado['Bairro'].isin(['NÃO INFORMADO', 'N/A', 'NA', '', '0', '0.0'])], 'Bairro', "Indicações por Bairro", "📍", 'violet')
        
        status_stats = df_filtrado.groupby('Status').agg(Total=('Respondido', 'count'), Respondidos=('Respondido', 'sum')).reset_index().sort_values('Total', ascending=False)
        tab_html += gerar_tabela_html(status_stats, 'Status', "Situação das Solicitações", "📌", 'orange', is_status=True)
        
        html = html.replace("{{TABELAS_HTML}}", tab_html)
        return html
    except Exception as e: return f"Erro ao gerar relatório: {e}"

# --- CARREGAMENTO DE DADOS ---
df = load_data()
if df.empty: st.stop()

# --- SIDEBAR FILTROS ---
def limpar_filtros_sol():
    for k in ['click_req_sol', 'click_org_sol', 'click_bairro_sol', 'sb_ano_sol', 'sb_req_sol', 'sb_org_sol', 'sb_bairro_sol', 'sb_status_sol', 'sb_top_req', 'sb_top_org', 'sb_top_bairro', 'sb_top_status']:
        if k in st.session_state: del st.session_state[k]

with st.sidebar:
    st.button("Limpar Filtros", on_click=limpar_filtros_sol)
    st.divider()
    
    anos_dis = sorted([int(a) for a in df['Ano'].unique() if a > 0])
    st.multiselect("Filtrar por Ano", anos_dis, default=anos_dis, key="sb_ano_sol")
    st.divider()

    st.subheader("Filtro por TOP X")
    top_options = ["TODOS", 5, 10, 15, 20, 30, 50]
    st.selectbox("Top Requerente", top_options, key="sb_top_req")
    st.selectbox("Top Órgão", top_options, key="sb_top_org")
    st.selectbox("Top Bairro", top_options, key="sb_top_bairro")
    st.selectbox("Top Situação", top_options, key="sb_top_status")
    st.divider()

    st.multiselect("Requerente", sorted(df['Requerente'].unique().tolist()), key="sb_req_sol")
    
    lista_orgaos = sorted(list(set(df['Órgão Demandado'].unique().tolist() + 
                                   (df['Órgão Demandado 2'].unique().tolist() if 'Órgão Demandado 2' in df.columns else []) + 
                                   (df['Órgão Demandado 3'].unique().tolist() if 'Órgão Demandado 3' in df.columns else []))))
    if 'NÃO INFORMADO' in lista_orgaos: lista_orgaos.remove('NÃO INFORMADO')
    st.multiselect("Órgão Demandado", lista_orgaos, key="sb_org_sol")
    
    st.multiselect("Bairro", sorted(df['Bairro'].unique().tolist()), key="sb_bairro_sol")
    st.multiselect("Situação", sorted(df['Status'].unique().tolist()), key="sb_status_sol")
    st.divider()
    
    estilo_mapa = st.selectbox("Mapa", ["carto-positron", "open-street-map", "carto-darkmatter"], key="sb_mapa_sol")
    st.divider()

# --- APLICAÇÃO FILTROS ---
df_f = df.copy()

# 1. Filtro de Ano
if 'sb_ano_sol' in st.session_state and st.session_state.sb_ano_sol: 
    df_f = df_f[df_f['Ano'].isin(st.session_state.sb_ano_sol)]

# --- CÁLCULO DE RANKING ABSOLUTO (PÓS-ANO) PARA MEDALHAS ---
top_3_req_global = df_f['Requerente'].value_counts().nlargest(3).index.tolist()
top_3_bairro_global = df_f[~df_f['Bairro'].isin(['NÃO INFORMADO', 'N/A', 'NA', '', '0', '0.0'])]['Bairro'].value_counts().nlargest(3).index.tolist()
org_stats_global = get_organ_stats(df_f)
top_3_org_global = org_stats_global['Orgao'].head(3).tolist()

# 2. Filtros TOP X
if st.session_state.get('sb_top_req') and st.session_state.sb_top_req != "TODOS":
# ... (rest of filtering logic)
    top_n = st.session_state.sb_top_req
    top_list = df_f['Requerente'].value_counts().nlargest(top_n).index.tolist()
    df_f = df_f[df_f['Requerente'].isin(top_list)]

if st.session_state.get('sb_top_org') and st.session_state.sb_top_org != "TODOS":
    top_n = st.session_state.sb_top_org
    # Para órgãos, precisamos de uma contagem especial já que existem 3 colunas
    org_cols = ['Órgão Demandado']
    if 'Órgão Demandado 2' in df_f.columns: org_cols.append('Órgão Demandado 2')
    if 'Órgão Demandado 3' in df_f.columns: org_cols.append('Órgão Demandado 3')
    org_counts = pd.concat([df_f[c] for c in org_cols]).value_counts()
    if 'NÃO INFORMADO' in org_counts: org_counts = org_counts.drop('NÃO INFORMADO')
    top_list = org_counts.nlargest(top_n).index.tolist()
    
    mask = (df_f['Órgão Demandado'].isin(top_list))
    if 'Órgão Demandado 2' in df_f.columns: mask |= (df_f['Órgão Demandado 2'].isin(top_list))
    if 'Órgão Demandado 3' in df_f.columns: mask |= (df_f['Órgão Demandado 3'].isin(top_list))
    df_f = df_f[mask]

if st.session_state.get('sb_top_bairro') and st.session_state.sb_top_bairro != "TODOS":
    top_n = st.session_state.sb_top_bairro
    top_list = df_f[~df_f['Bairro'].isin(['NÃO INFORMADO', 'N/A', 'NA', '', '0', '0.0'])]['Bairro'].value_counts().nlargest(top_n).index.tolist()
    df_f = df_f[df_f['Bairro'].isin(top_list)]

if st.session_state.get('sb_top_status') and st.session_state.sb_top_status != "TODOS":
    top_n = st.session_state.sb_top_status
    top_list = df_f['Status'].value_counts().nlargest(top_n).index.tolist()
    df_f = df_f[df_f['Status'].isin(top_list)]

# 3. Filtros Multiselect
if 'sb_req_sol' in st.session_state and st.session_state.sb_req_sol: 
    df_f = df_f[df_f['Requerente'].isin(st.session_state.sb_req_sol)]

if 'sb_org_sol' in st.session_state and st.session_state.sb_org_sol:
    org_sels = st.session_state.sb_org_sol
    mask = (df_f['Órgão Demandado'].isin(org_sels))
    if 'Órgão Demandado 2' in df_f.columns: mask |= (df_f['Órgão Demandado 2'].isin(org_sels))
    if 'Órgão Demandado 3' in df_f.columns: mask |= (df_f['Órgão Demandado 3'].isin(org_sels))
    df_f = df_f[mask]

if 'sb_bairro_sol' in st.session_state and st.session_state.sb_bairro_sol: 
    df_f = df_f[df_f['Bairro'].isin(st.session_state.sb_bairro_sol)]

if 'sb_status_sol' in st.session_state and st.session_state.sb_status_sol: 
    df_f = df_f[df_f['Status'].isin(st.session_state.sb_status_sol)]

# 4. Filtros por clique
if st.session_state.get('click_req_sol'): df_f = df_f[df_f['Requerente'] == st.session_state.click_req_sol]
if st.session_state.get('click_org_sol'):
    org_c = st.session_state.click_org_sol
    mask = (df_f['Órgão Demandado'] == org_c)
    if 'Órgão Demandado 2' in df_f.columns: mask |= (df_f['Órgão Demandado 2'] == org_c)
    if 'Órgão Demandado 3' in df_f.columns: mask |= (df_f['Órgão Demandado 3'] == org_c)
    df_f = df_f[mask]
if st.session_state.get('click_bairro_sol'): df_f = df_f[df_f['Bairro'] == st.session_state.click_bairro_sol]

# Título dinâmico
anos_lista = ", ".join([str(a) for a in sorted(st.session_state.sb_ano_sol)]) if 'sb_ano_sol' in st.session_state and st.session_state.sb_ano_sol else "Geral"
titulo_dinamico = f"CMRJ - Solicitações Legislativas ({anos_lista})"

with st.sidebar:
    if st.button("Preparar Relatório"):
        with st.spinner("Gerando..."):
            rel_html = exportar_html_cmrj(df_f.copy(), estilo_mapa, titulo_dinamico)
            st.download_button(label="📥 Baixar Relatório Solicitações", data=rel_html, file_name="relatorio_solicitacoes_cmrj.html", mime="text/html")

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
    fig = px.scatter_mapbox(map_ready, lat="lat", lon="lon", size="Quantidade", hover_name="Bairro", color="Quantidade", color_continuous_scale='Plasma', size_max=40, zoom=10, mapbox_style=st.session_state.sb_mapa_sol)
    fig.update_layout(height=550, margin={"r":0,"t":0,"l":0,"b":0}, clickmode='event+select')
    sel_map = st.plotly_chart(fig, width="stretch", on_select="rerun")
    if sel_map and sel_map["selection"]["points"]:
        st.session_state.click_bairro_sol = sel_map["selection"]["points"][0]["hovertext"]; st.rerun()

st.write("")
m = st.columns(5)
total_sol = len(df_f)
total_resp = int(df_f['Respondido'].sum())
perc_resp = (total_resp / total_sol * 100) if total_sol > 0 else 0
metrics = [
    ("Solicitações", total_sol), 
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

    sel = st.dataframe(
        stats[[col, "Exibição", 'Qtd', '% Respondido']].style.apply(style_top_3, axis=1), 
        column_config={
            col: None, # Esconde a coluna original usada para o estilo
            "Exibição": st.column_config.TextColumn(col, width="medium"), 
            "Qtd": st.column_config.ProgressColumn("Qtd", format="%d", min_value=0, max_value=int(stats['Qtd'].max()) if int(stats['Qtd'].max()) > 0 else 100, color=cor), 
            "% Respondido": st.column_config.ProgressColumn("% Respondido", format="%.0f%%", min_value=0, max_value=100, color=cor)
        }, 
        hide_index=True, width="stretch", on_select="rerun"
    )
    if sel and sel["selection"]["rows"]: 
        st.session_state[key] = stats.iloc[sel["selection"]["rows"][0]][col]
        st.rerun()

criar_tabela(df_f, 'Requerente', "Demandas por Vereador", "👤", 'click_req_sol', "blue")

org_stats = get_organ_stats(df_f)
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

sel_org = st.dataframe(
    org_stats[["Orgao", "Exibição", "Total", "% Respondido"]].style.apply(style_org_top_3, axis=1), 
    column_config={
        "Orgao": None,
        "Exibição": st.column_config.TextColumn("Órgão", width="medium"), 
        "Total": st.column_config.ProgressColumn("Total", format="%d", min_value=0, max_value=int(org_stats['Total'].max() if not org_stats.empty else 1), color="green"),
        "% Respondido": st.column_config.ProgressColumn("% Respondido", format="%.0f%%", min_value=0, max_value=100, color="green")
    }, 
    hide_index=True, width="stretch", on_select="rerun"
)
if sel_org and sel_org["selection"]["rows"]:
    st.session_state.click_org_sol = org_stats.iloc[sel_org["selection"]["rows"][0]]['Orgao']
    st.rerun()

criar_tabela(df_f[~df_f['Bairro'].isin(['NÃO INFORMADO', 'N/A', 'NA', '', '0', '0.0'])], 'Bairro', "Indicações por Bairro", "📍", 'click_bairro_sol', "violet")

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
        elif s_up in ['EM ANDAMENTO','PENDENTE', 'ABERTO' ]: cor = "#EEF65C"
        elif s_up in ['PARCIAL', 'AGUARDANDO']: cor = "#15E7FA"
        st.markdown(f"<div class='status-item'><div class='status-label-row'><span>{row['Status']}</span><span>{row['count']} ({p:.1f}%)</span></div><div class='status-bar-bg'><div class='status-bar-fill' style='width: {p}%; background: {cor};'></div></div></div>", unsafe_allow_html=True)
with st.expander("📄 Dados Detalhados CMRJ"): st.dataframe(df_f[['Data', 'Requerente', 'Bairro', 'Status', 'Assunto']], width="stretch")
