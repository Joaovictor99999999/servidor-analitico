import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
import sqlite3
import os
from dicionario_clientes import CATALOGO
import plotly.graph_objects as go

st.set_page_config(
    page_title="Servidor OLS | Painel",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
div[data-testid="stMetric"] {
    background-color: #1a1f2e;
    border: 1px solid #2D2D3B;
    border-radius: 10px;
    padding: 15px 20px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.st-key-card_horas, .st-key-card_perfil, .st-key-card_eficiencia, .st-key-card_demandas {
    background-color: #161b26;
    border-radius: 12px;
    padding: 20px 15px 12px 15px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.st-key-card_tendencia {
    background-color: #161b26;
    border-radius: 12px;
    padding: 20px 15px 10px 15px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.st-key-visao_integrada {
    background-color: #161b26;
    border-radius: 12px;
    padding: 20px 15px 70px 15px;
    min-height: 480px
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.st-key-card_ranking_equip {
    background-color: #161b26;
    border-radius: 12px;
    padding: 20px 15px 30px 15px;
    min-height: 480px
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.st-key-card_mapeamento {
    background-color: #161b26;
    border-radius: 12px;
    padding: 20px 15px 70px 15px;
    min-height: 480px
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.st-key-visao_negocios {
    background-color: #161b26;
    border-radius: 12px;
    padding: 20px 15px 12px 15px;
}
</style>
""", unsafe_allow_html=True)

# Cabeçalho principal
st.title("📊 Painel de Gestão - OLS Offshore")
st.markdown("Visualização da interface do servidor local com Abas e Mock Data.")
st.markdown("---")

# ==========================================
# 1. CONEXÃO E COLETA DE OPÇÕES PARA OS FILTROS
# ==========================================
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
CAMINHO_BANCO = os.path.join(DIRETORIO_ATUAL, '..', 'banco_local', 'relatorios.db')

try:
    conn = sqlite3.connect(CAMINHO_BANCO)
    # Busca clientes, sites e técnicos únicos direto da fonte
    lista_clientes = ["Todos"] + [row[0] for row in conn.execute("SELECT DISTINCT cliente FROM relatorios WHERE cliente IS NOT NULL AND cliente != '' ORDER BY cliente").fetchall()]
    lista_sites = ["Todos"] + [row[0] for row in conn.execute("SELECT DISTINCT site FROM relatorios WHERE site IS NOT NULL AND site != '' ORDER BY site").fetchall()]
except Exception as e:
    st.error(f"⚠️ Erro ao conectar ao banco para gerar filtros: {e}")
    lista_clientes, lista_sites, lista_tecnicos = ["Todos"], ["Todos"], ["Todos"]

# ==========================================
# 2. BARRA LATERAL (SIDEBAR) E OS FILTROS
# ==========================================
st.sidebar.header("🔍 Filtros Globais")
st.sidebar.markdown("As seleções abaixo buscam os dados de forma otimizada direto no Banco de Dados.")

filtro_cliente = st.sidebar.selectbox("Cliente", lista_clientes)
filtro_site = st.sidebar.selectbox("Site / Navio", lista_sites)
filtro_data = st.sidebar.date_input("Período (Data de Conclusão)", []) 

# ==========================================
# 3. A CONSTRUÇÃO DA QUERY DINÂMICA
# ==========================================
query_base_rel = "SELECT * FROM relatorios WHERE 1=1"
condicoes = []
parametros = []

if filtro_cliente != "Todos":
    condicoes.append("cliente = ?")
    parametros.append(filtro_cliente)
    
if filtro_site != "Todos":
    condicoes.append("site = ?")
    parametros.append(filtro_site)

if condicoes:
    query_base_rel += " AND " + " AND ".join(condicoes)

# ==========================================
# 4. EXECUTANDO A BUSCA CIRÚRGICA
# ==========================================
try:
    # 1. Puxa os dados com base nos selects de texto
    df_rel = pd.read_sql_query(query_base_rel, conn, params=parametros)
    
    # 2. Filtro de Datas usando Inteligência do Pandas
    if len(filtro_data) == 2:
        data_inicio, data_fim = filtro_data
        
        # Tradutor rápido para o Pandas entender os dados falsos que criamos (Ex: 05/Ago/2026)
        meses_pt = {'Jan':'01', 'Fev':'02', 'Mar':'03', 'Abr':'04', 'Mai':'05', 'Jun':'06', 'Jul':'07', 'Ago':'08', 'Set':'09', 'Out':'10', 'Nov':'11', 'Dez':'12'}
        df_rel['data_temp'] = df_rel['data_termino'].replace(meses_pt, regex=True)
        df_rel['data_temp'] = pd.to_datetime(df_rel['data_temp'], errors='coerce', dayfirst=True)
        
        # Corta a tabela mantendo só o que está dentro do calendário
        df_rel = df_rel[(df_rel['data_temp'].dt.date >= data_inicio) & (df_rel['data_temp'].dt.date <= data_fim)]
        df_rel = df_rel.drop(columns=['data_temp'])

    # 3. O Efeito Dominó para as tabelas de Horas e Intervenções
    ids_validos = df_rel['id_os'].tolist()
    
    if ids_validos:
        # Puxa no banco SOMENTE os serviços e checklists que pertencem às OSs que sobreviveram aos filtros
        placeholders = ','.join(['?'] * len(ids_validos))
        
        query_log = f"SELECT * FROM service_log WHERE id_os IN ({placeholders})"
        df_log = pd.read_sql_query(query_log, conn, params=ids_validos)
        
        query_intervencoes = f"SELECT * FROM checklist_intervencoes WHERE id_os IN ({placeholders})"
        df_intervencoes = pd.read_sql_query(query_intervencoes, conn, params=ids_validos)
    else:
        # Se os filtros zeraram a tabela principal, zera as outras duas também
        df_log = pd.DataFrame()
        df_intervencoes = pd.DataFrame()

    conn.close()
    
except Exception as e:
    st.error(f"⚠️ Erro ao executar a busca otimizada no banco: {e}")
    df_rel, df_log, df_intervencoes = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# ==========================================
# A PARTIR DAQUI COMEÇAM AS SUAS ABAS NORMAIS
# ==========================================
aba1, aba2, aba3 = st.tabs(["📊 Visão Geral", "🔧 Inteligência de Falhas", "📁 Biblioteca de Relatórios"])

# ==========================================
# ABA 1: VISÃO GERAL (O seu código original de gráficos)
# ==========================================
with aba1:
    # 1. CABEÇALHO ELEGANTE
    st.markdown("### 📈 Indicadores Operacionais Gerais")
    st.markdown("<p style='color:#8C8C9A; font-size:15px; margin-bottom: 25px;'>Visão consolidada de produtividade, esforço logístico e perfil de atendimento.</p>", unsafe_allow_html=True)

    # ==========================================
    # 1. CÁLCULO DOS INDICADORES DE TOPO (KPIs)
    # ==========================================
    total_os = len(df_rel)
    total_horas = df_log['horas_totais'].sum() if not df_log.empty else 0
    media_horas = total_horas / total_os if total_os > 0 else 0
    clientes_unicos = df_rel['cliente'].nunique() if not df_rel.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Relatórios", f"{total_os}")
    col2.metric("Horas Totais Alocadas", f"{total_horas:.1f} h")
    col3.metric("Média de Horas / OS", f"{media_horas:.1f} h")
    col4.metric("Clientes Atendidos", f"{clientes_unicos}")

    st.markdown("<hr style='border:1px solid #2D2D3B; margin-top: 5px; margin-bottom: 25px;'>", unsafe_allow_html=True)

    esconder_menu = {'displayModeBar': False}

    # ==========================================
    # 2. LINHA 1: PRODUTIVIDADE E ESFORÇO 
    # ==========================================
    col_master_esq, col_master_dir = st.columns([2.2, 1])
    
    with col_master_esq:
        # --- CARD 1: CONSUMO DE HORAS (GRANDE) ---
        with st.container(key="card_horas"):
            st.markdown("<h5 style='text-align: center; color: #E0E0E0; margin-bottom: 25px;'>Consumo de Horas por Serviço</h5>", unsafe_allow_html=True)
        
            # Substituindo o multiselect por um popover moderno com checkboxes
            with st.popover("⚙️ Filtrar Serviços de Horas"):
                opcoes_servicos = [
                    "1 - Trabalho Onshore", "2 - Trabalho Offshore", 
                    "3 - Em Stand-By (Onshore)", "4 - Em Stand-By (Offshore)", 
                    "5 - Deslocamento Terrestre", "6 - Deslocamento Aéreo", 
                    "7 - Deslocamento Aéreo (Offshore)", "8 - Atividade no Escritório"
                ]
                
                servicos_selecionados = []
                for servico in opcoes_servicos:
                    # Todos começam marcados (value=True)
                    if st.checkbox(servico, value=True):
                        servicos_selecionados.append(servico)
            
            if not df_log.empty and servicos_selecionados:
                df_filtrado = df_log[df_log['tipo_servico'].isin(servicos_selecionados)].copy()
                
                # Limpeza visual: Tira o "1 - " da frente do nome para caber no eixo X
                df_filtrado['servico_limpo'] = df_filtrado['tipo_servico'].apply(lambda x: x.split(" - ")[0] if " - " in x else x)
                df_agrupado = df_filtrado.groupby('servico_limpo')['horas_totais'].sum().reset_index()
                
                # 1. GRÁFICO DE COLUNAS VERTICAIS
                fig1 = px.bar(df_agrupado, x="servico_limpo", y="horas_totais", text="horas_totais")
                
                fig1.update_traces(
                    marker_color='#3B82F6', 
                    marker_line_color='#2563EB', marker_line_width=1,
                    textposition='outside', texttemplate='%{text:.1f}h',
                    textfont=dict(color='#E0E0E0', size=14)
                )
                
                fig1.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=60, r=10, t=20, b=15), height=530,
                    bargap=0.4,
                    xaxis=dict(showgrid=False, title="", showticklabels=True, tickfont=dict(size=12, color='#A0A0B0')),
                    yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', title="", showticklabels=True), # Oculta números do eixo Y
                    showlegend=True
                )
                st.plotly_chart(fig1, use_container_width=True, config=esconder_menu, theme=None)
            else:
                st.info("Nenhum dado ou serviço selecionado.")

    with col_master_dir:
        with st.container(key="card_perfil"):
            st.markdown("<h6 style='text-align: center; color: #E0E0E0; margin-bottom: 5px;'>Perfil de Atendimento</h6>", unsafe_allow_html=True)
                
            if not df_rel.empty:
                # 2. Função auxiliar para extrair as somas separadas por tipo
                def somar_servicos(tipo_hora):
                    os_validas = df_log[df_log['tipo_servico'].str.contains(tipo_hora, na=False)]['id_os'].unique()
                    df_filtrado = df_rel[df_rel['id_os'].isin(os_validas)]
                    if df_filtrado.empty: return []
                    
                    return [
                        {"Serviço": "Survey", "Quantidade": df_filtrado['chk_survey'].sum(), "Tipo": tipo_hora},
                        {"Serviço": "Instalação", "Quantidade": df_filtrado['chk_instalacao'].sum(), "Tipo": tipo_hora},
                        {"Serviço": "Comissionamento", "Quantidade": df_filtrado['chk_comissionamento'].sum(), "Tipo": tipo_hora},
                        {"Serviço": "Manutenção", "Quantidade": df_filtrado['chk_manutencao'].sum(), "Tipo": tipo_hora},
                        {"Serviço": "Mudança Locação", "Quantidade": df_filtrado['chk_mudanca_locacao'].sum(), "Tipo": tipo_hora},
                        {"Serviço": "Desinstalação", "Quantidade": df_filtrado['chk_desinstalacao'].sum(), "Tipo": tipo_hora}
                    ]

                # Consolida os dados dependendo do que estiver marcado
                dados_radar = []
                dados_radar.extend(somar_servicos("Onshore"))
                dados_radar.extend(somar_servicos("Offshore"))
                
                df_perfil = pd.DataFrame(dados_radar)
                
                if not df_perfil.empty:
                    df_perfil = df_perfil[df_perfil['Quantidade'] > 0]
                
                if not df_perfil.empty:
                    # 3. Gráfico com separação por COR (cria a sobreposição)
                    fig2 = px.line_polar(
                        df_perfil, 
                        r='Quantidade', 
                        theta='Serviço', 
                        color='Tipo', # O segredo da sobreposição está aqui
                        line_close=True, 
                        text='Quantidade',
                        color_discrete_map={"Onshore": "#3B82F6", "Offshore": "#10B981"} # Azul e Verde
                    )
                    
                    fig2.update_traces(
                        fill='toself', 
                        opacity=0.5, # Aplica transparência para podermos ver a teia de trás
                        mode="lines+markers+text", 
                        textposition="top center",
                        textfont=dict(size=14)
                    )
                    
                    fig2.update_layout(
                        polar=dict(
                            gridshape='linear',
                            bgcolor='rgba(0,0,0,0)',
                            radialaxis=dict(
                                visible=True, showticklabels=True, 
                                tickfont=dict(size=10, color='#64748B'), 
                                gridcolor='rgba(255,255,255,0.1)', linecolor='rgba(255,255,255,0.1)'
                            ),
                            angularaxis=dict(
                                tickfont=dict(size=13, color='#E0E0E0'), 
                                gridcolor='rgba(255,255,255,0.1)', linecolor='rgba(255,255,255,0.1)'
                            )
                        ),
                        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                        margin=dict(l=80, r=60, t=30, b=30), height=330, 
                        showlegend=True, # Legenda ativada para sabermos quem é azul e quem é verde
                        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5, itemclick=False, itemdoubleclick=False  )
                    )
                    st.plotly_chart(fig2, use_container_width=True, config=esconder_menu, theme=None)
                else:
                    st.info("Nenhuma atividade específica registrada para este filtro.")
            else:
                st.info("Nenhum dado de OS registrado.")

        #st.markdown("<br>", unsafe_allow_html=True) # Dá um fôlego/espaço entre os dois cards da direita

        with st.container(key="card_eficiencia"):
            st.markdown("<h6 style='text-align: center; color: #E0E0E0; margin-bottom: 5px;'>Produtivo vs Logística</h6>", unsafe_allow_html=True)
        
            #st.markdown("<br>", unsafe_allow_html=True) # Espaçamento para alinhar com o seletor da coluna 3
                                    
            if not df_log.empty:
                def classificar_eficiencia(tipo):
                    if not isinstance(tipo, str): return "Outros"
                    tipo_lower = tipo.lower()
                    if "trabalho" in tipo_lower or "escritório" in tipo_lower:
                        return "Tempo Produtivo"
                    else:
                        return "Logística / Stand-by"

                df_log_ef = df_log.copy()
                df_log_ef['categoria_eficiencia'] = df_log_ef['tipo_servico'].apply(classificar_eficiencia)
                df_eficiencia = df_log_ef.groupby('categoria_eficiencia')['horas_totais'].sum().reset_index()
                
                # 1. Cores: Verde vibrante para produtivo, azul super escuro para logística
                mapa_cores = {"Tempo Produtivo": "#10B981", "Logística / Stand-by": "#1E293B"}
                
                # 2. Cálculo matemático do KPI
                total_h = df_eficiencia['horas_totais'].sum()
                if "Tempo Produtivo" in df_eficiencia['categoria_eficiencia'].values:
                    horas_produtivas = df_eficiencia[df_eficiencia['categoria_eficiencia'] == "Tempo Produtivo"]['horas_totais'].sum()
                else:
                    horas_produtivas = 0
                    
                perc_produtivo = (horas_produtivas / total_h * 100) if total_h > 0 else 0
                
                # 3. Gráfico com buraco maior (0.75) para virar um Anel
                fig4 = px.pie(
                    df_eficiencia, names='categoria_eficiencia', values='horas_totais', hole=0.75,
                    color='categoria_eficiencia', color_discrete_map=mapa_cores
                )
                
                fig4.update_traces(
                    textinfo='none', # Desativa o texto por cima para limpar o visual
                    marker=dict(line=dict(color='rgba(0,0,0,0)', width=0)), # Remove a borda padrão
                    hovertemplate="<b>%{label}</b><br>Horas: %{value:.1f}h<extra></extra>"
                )
                
                fig4.update_layout(
                    # Injeta o número percentual gigante no meio
                    annotations=[dict(text=f"{perc_produtivo:.1f}%", x=0.5, y=0.5, font_size=36, showarrow=False, font_color='#E0E0E0')],
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=0, r=0, t=10, b=10), height=190,
                    showlegend=True,
                    legend=dict(
                        orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5, 
                        font=dict(color='#A0A0B0', size=12),
                        itemclick=False, itemdoubleclick=False # Trava os botões
                    )
                )
                st.plotly_chart(fig4, use_container_width=True, config=esconder_menu, theme=None)
            else:
                st.info("Nenhum dado de horas registrado.")
    # ==========================================
    # 3. LINHA 2: INTELIGÊNCIA DE NEGÓCIOS E CLIENTES
    # ==========================================
    st.markdown("<br>", unsafe_allow_html=True) # Espaço antes da próxima linha
    with st.container(key="card_demandas"):
        st.markdown("<h5 style='text-align: center; color: #E0E0E0; margin-bottom: 10px;'>Ranking de Demandas por Cliente</h5>", unsafe_allow_html=True)
            
        if not df_rel.empty:
            # 1. DRILL-DOWN AUTOMÁTICO USANDO O SEU FILTRO GLOBAL
            if filtro_cliente == "Todos":
                df_plot = df_rel['cliente'].value_counts().reset_index()
                df_plot.columns = ['Eixo_Y', 'Quantidade de OS']
                titulo_x = "Operações por Empresa"
            else:
                # Como o filtro global já fatiou o dataframe, aqui só tem navios dessa empresa!
                df_plot = df_rel['site'].value_counts().reset_index()
                df_plot.columns = ['Eixo_Y', 'Quantidade de OS']
                titulo_x = f"Demandas nas Subestações: {filtro_cliente}"
            
            df_plot = df_plot.sort_values('Quantidade de OS', ascending=True)
            
            # 2. GRÁFICO COM BARRA PADRONIZADA
            fig3 = px.bar(df_plot, x='Quantidade de OS', y='Eixo_Y', orientation='h', text='Quantidade de OS')
            
            fig3.update_traces(
                marker_color='#8B5CF6', 
                marker_line_color='#7C3AED', marker_line_width=1,
                textposition='outside', textfont=dict(color='#E0E0E0', size=14),
                width=0.4 # Trava a largura da barra para não ficar gigante se houver 1 item
            )
            
            fig3.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=80, r=50, t=10, b=40), height=320,
                xaxis=dict(
                    showgrid=True, gridcolor='rgba(255,255,255,0.1)',
                    showticklabels=True, 
                    title=dict(text=titulo_x, font=dict(size=12, color='#A0A0B0')), 
                    tickfont=dict(size=11, color='#A0A0B0')
                ),
                yaxis=dict(
                    showgrid=False, title="", 
                    tickfont=dict(size=13, color='#E0E0E0'), 
                    ticks="outside", ticklen=10, tickcolor='rgba(0,0,0,0)'
                ),
                showlegend=False
            )
            st.plotly_chart(fig3, use_container_width=True, config=esconder_menu, theme=None)
        else:
            st.info("Nenhum dado de OS registrado.")

with aba2:
    # 1. CABEÇALHO ELEGANTE
    st.markdown("### 🔧 Inteligência de Falhas e Intervenções")
    st.markdown("<p style='color:#8C8C9A; font-size:15px; margin-bottom: 25px;'>Análise avançada de ofensores de hardware e rastreamento de causas raiz.</p>", unsafe_allow_html=True)

    if df_intervencoes.empty:
        st.info("Nenhuma intervenção registrada com os filtros globais atuais.")
    else:
        # 2. FILTRO LOCAL (Agora ele comanda a tela toda, inclusive os KPIs)
        opcoes_atv = ["Todas as Atividades"] + list(df_intervencoes['atividade'].unique())
        filtro_atv = st.selectbox("Filtrar Visão por Atividade:", opcoes_atv)
        
        # A tabela que vai alimentar os gráficos E os KPIs:
        df_grafico = df_intervencoes[df_intervencoes['atividade'] == filtro_atv] if filtro_atv != "Todas as Atividades" else df_intervencoes

        # 3. MINI-KPIs (Agora 100% dinâmicos)
        total_intervencoes = len(df_grafico)
        equip_critico = df_grafico['equipamento'].mode()[0] if not df_grafico.empty else "N/A"
        
        df_causas_limpo = df_grafico[df_grafico['causa'] != "N/A (Não se aplica)"]
        causa_comum = df_causas_limpo['causa'].mode()[0] if not df_causas_limpo.empty else "N/A"

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Total de Intervenções", total_intervencoes)
        col_m2.metric("⚠️ Ofensor Principal", equip_critico)
        col_m3.metric("🎯 Causa Mais Comum", causa_comum)

        st.markdown("<hr style='border:1px solid #2D2D3B; margin-top: 5px; margin-bottom: 25px;'>", unsafe_allow_html=True)

        # 4. OS GRÁFICOS PREMIUM
        col_graf5, col_graf6 = st.columns(2)
        esconder_menu = {'displayModeBar': False}
        
        # Paleta de cores moderna (Inspirada em painéis de tecnologia - Azul, Esmeralda, Laranja, Roxo, etc.)
        cores_modernas = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#14B8A6', '#F43F5E', '#6366F1']
        
        with col_graf5:
            with st.container(key="card_ranking_equip"):
                st.markdown("<h5 style='text-align: center; color: #E0E0E0; margin-bottom: 20px;'>Ranking de Equipamentos</h5>", unsafe_allow_html=True)
                
                if not df_grafico.empty:
                    df_equip = df_grafico['equipamento'].value_counts().reset_index()
                    df_equip.columns = ['Equipamento', 'Volume']
                    
                    fig5 = px.bar(
                        df_equip, x='Volume', y='Equipamento', orientation='h', 
                        text='Volume', color='Equipamento', 
                        color_discrete_sequence=cores_modernas
                    )
                    
                    fig5.update_traces(
                        textposition='outside',
                        textfont=dict(color='#E0E0E0', size=14),
                        marker=dict(line=dict(color='#0E1117', width=1))
                    )
                    
                    fig5.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        margin=dict(l=70, r=0, t=0, b=60),
                        height=420,
                        xaxis=dict(showgrid=False,  showticklabels=True, title="", zeroline=True),
                        yaxis=dict(showgrid=False, title="", categoryorder='total ascending', tickfont=dict(size=14, color='#E0E0E0'), ticks="outside", ticklen=10, tickcolor='rgba(0,0,0,0)'),
                        showlegend=False
                    )
                    st.plotly_chart(fig5, use_container_width=True, config=esconder_menu, theme=None)
                else:
                    st.warning("Sem dados para este filtro.")
            
        with col_graf6:
            with st.container(key="card_mapeamento"):
                st.markdown("<h5 style='text-align: center; color: #E0E0E0; margin-bottom: 20px;'>Mapeamento de Causas e Gatilhos</h5>", unsafe_allow_html=True)
                
                if not df_causas_limpo.empty:
                    df_causas = df_causas_limpo['causa'].value_counts().reset_index()
                    df_causas.columns = ['Causa', 'Ocorrências']
                    
                    fig6 = px.pie(df_causas, names='Causa', values='Ocorrências', hole=0.6, color_discrete_sequence=cores_modernas)
                    
                    fig6.update_traces(
                        textposition='inside',
                        textinfo='percent',
                        insidetextorientation='horizontal',
                        #marker=dict(line=dict(color='#0E1117', width=3)), # Borda preta elegante separando as cores
                        hovertemplate="<b>%{label}</b><br>Ocorrências: %{value}<extra></extra>"
                    )
                    
                    fig6.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        margin=dict(l=0, r=0, t=0, b=0),
                        height=380,
                        showlegend=True,
                        legend=dict(
                            orientation="h",
                            yanchor="top", y=-0.1, 
                            xanchor="center", x=0.5, 
                            font=dict(color='#A0A0B0', size=12)
                        )
                    )
                    st.plotly_chart(fig6, use_container_width=True, config=esconder_menu, theme=None)
                else:
                    st.success("🎉 Nenhuma falha raiz registrada com o filtro atual!")
                
   # 5. GRÁFICO DE CURVA (TENDÊNCIA TEMPORAL MULTI-LINHAS)
        with st.container(key="card_tendencia"):
            st.markdown("<hr style='border:1px solid #2D2D3B; margin-top: 30px; margin-bottom: 30px;'>", unsafe_allow_html=True)
            st.markdown("<h5 style='text-align: center; color: #E0E0E0; margin-bottom: 20px;'>📈 Tendência de Intervenções no Tempo</h5>", unsafe_allow_html=True)

            if not df_grafico.empty and not df_rel.empty:
                df_tempo = pd.merge(df_grafico, df_rel[['id_os', 'data_termino']], on='id_os', how='inner')
                meses_pt = {'Jan':'01', 'Fev':'02', 'Mar':'03', 'Abr':'04', 'Mai':'05', 'Jun':'06', 'Jul':'07', 'Ago':'08', 'Set':'09', 'Out':'10', 'Nov':'11', 'Dez':'12'}
                df_tempo['data_formatada'] = df_tempo['data_termino'].replace(meses_pt, regex=True)
                df_tempo['data_formatada'] = pd.to_datetime(df_tempo['data_formatada'], format='%d/%m/%Y', errors='coerce')
                
                df_agrupado = df_tempo.groupby('data_formatada').size().reset_index(name='Volume')
                df_agrupado = df_agrupado.sort_values('data_formatada')

                df_causas = df_tempo[df_tempo['causa'] != "N/A (Não se aplica)"]
                df_causas_agrupado = df_causas.groupby(['data_formatada', 'causa']).size().reset_index(name='Volume')

                # ==========================================
                # CÁLCULO ADAPTATIVO — REAPROVEITANDO O FILTRO GLOBAL 
                # ==========================================
                try:
                    if len(filtro_data) == 2:
                        dias_filtro = (data_fim - data_inicio).days
                        range_eixo_x = [data_inicio, data_fim]
                    else:
                        dias_filtro = (df_agrupado['data_formatada'].max() - df_agrupado['data_formatada'].min()).days
                        range_eixo_x = [df_agrupado['data_formatada'].min(), df_agrupado['data_formatada'].max()]
                except NameError:
                    dias_filtro = (df_agrupado['data_formatada'].max() - df_agrupado['data_formatada'].min()).days
                    range_eixo_x = [df_agrupado['data_formatada'].min(), df_agrupado['data_formatada'].max()]

                if dias_filtro <= 14:
                    dtick_x = "D1"
                    formato_x = "%d/%b"
                elif dias_filtro <= 45:
                    dtick_x = "D7"
                    formato_x = "%d/%b"
                else:
                    dtick_x = "M1"
                    formato_x = "%b/%Y"

                volume_max = df_agrupado['Volume'].max()
                if volume_max <= 20:
                    dtick_y = 2
                elif volume_max <= 100:
                    dtick_y = 10
                elif volume_max <= 500:
                    dtick_y = 50
                else:
                    dtick_y = 100

                # ==========================================
                # CONSTRUÇÃO DO GRÁFICO (CAMADA POR CAMADA)
                # ==========================================
                fig7 = go.Figure()

                # 1. TOTAL GERAL (A linha real entra ANTES para o Plotly ler as datas)
                fig7.add_trace(go.Scatter(
                    x=df_agrupado['data_formatada'], y=df_agrupado['Volume'],
                    mode='lines', name='Total Geral', legendgroup='Total', showlegend=False,
                    line=dict(color='#10B981', width=2, shape='linear'),
                    fill='tozeroy', fillcolor='rgba(16, 185, 129, 0.1)' 
                ))
                # Fantasma do Total (entra depois só para gerar a caixinha)
                fig7.add_trace(go.Scatter(
                    x=[None], y=[None], mode='markers',
                    marker=dict(symbol='square', size=15, color='#10B981', line=dict(width=0)),
                    name='Total Geral', legendgroup='Total', showlegend=True
                ))

                # 2. AS CAUSAS (Ocultas por padrão)
                cores_causas = ['#3B82F6', '#F59E0B', '#8B5CF6', '#EF4444', '#14B8A6', '#F43F5E']
                causas_unicas = df_causas_agrupado['causa'].unique()

                for i, causa in enumerate(causas_unicas):
                    df_c = df_causas_agrupado[df_causas_agrupado['causa'] == causa].sort_values('data_formatada')
                    cor = cores_causas[i % len(cores_causas)]
                    
                    # Linha real da Causa
                    fig7.add_trace(go.Scatter(
                        x=df_c['data_formatada'], y=df_c['Volume'],
                        mode='lines', name=causa, legendgroup=causa, showlegend=False, visible='legendonly',
                        line=dict(color=cor, width=2, shape='linear'),
                    ))
                    # Fantasma da Causa
                    fig7.add_trace(go.Scatter(
                        x=[None], y=[None], mode='markers',
                        marker=dict(symbol='square', size=15, color=cor, line=dict(width=0)),
                        name=causa, legendgroup=causa, showlegend=True, visible='legendonly'
                    ))

                # ==========================================
                # LAYOUT FINO DO GRÁFICO
                # ==========================================
                fig7.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=70, r=200, t=10, b=90), # Margem corrigida para o Eixo Y aparecer
                    height=380,
                    showlegend=True,
                    legend=dict(
                        orientation="v", 
                        yanchor="middle", y=0.5, 
                        xanchor="left", x=1.02, 
                        font=dict(color='#A0A0B0', size=12),
                        itemwidth=30 # Força as linhas da legenda a ficarem curtas parecendo caixas
                    ),
                    xaxis=dict(
                        showgrid=False, 
                        title=dict(text="Período", font=dict(color='#A0A0B0', size=12)), 
                        tickfont=dict(color='#A0A0B0'), 
                        dtick=dtick_x,
                        tickformat=formato_x,
                        range=range_eixo_x
                    ),
                    yaxis=dict(
                        showgrid=True, gridcolor='rgba(255,255,255,0.05)', 
                        title=dict(text="Volume de Ocorrências", font=dict(color='#A0A0B0', size=12)), 
                        tickfont=dict(color='#A0A0B0'),
                        dtick=dtick_y,
                        tick0=0,
                        rangemode='tozero'
                    )
                )
                
                st.plotly_chart(fig7, use_container_width=True, config=esconder_menu, theme=None)
with aba3:
    st.subheader("📁 Biblioteca de Relatórios")
    st.markdown("<p style='color:gray; font-size:14px; margin-bottom: 25px;'>Acesse e baixe os documentos finalizados da operação.</p>", unsafe_allow_html=True)

    # 1. MAPEAMENTO DA PASTA DE ARQUIVOS FÍSICOS
    DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
    PASTA_REPOSITORIO = os.path.join(DIRETORIO_ATUAL, 'repositorio_arquivos')

    # Como usamos a "Query Dinâmica" no topo do código, a variável 'df_rel' 
    # já chega aqui prontinha e filtrada pela barra lateral!
    
    if df_rel.empty:
        st.info("Nenhum relatório finalizado encontrado com os filtros atuais.")
    else:
        # 2. SISTEMA DE BUSCA LOCAL (Apenas para achar a OS mais rápido)
        pesquisa_projeto = st.text_input("🔍 Buscar por Código do Projeto (Ex: CCV2625)", "")

        # Aplicando a inteligência da busca por texto
        df_filtrado = df_rel.copy()
        if pesquisa_projeto:
            df_filtrado = df_filtrado[df_filtrado['projeto'].str.contains(pesquisa_projeto, case=False, na=False)]

        st.markdown("---")
        
        # 3. TABELA VISUAL (Ocultamos colunas internas para ficar limpo)
        # Ordenamos pela data de termino (simulando o ORDER BY DESC do SQL)
        if not df_filtrado.empty:
            df_visual = df_filtrado[['projeto', 'cliente', 'site', 'data_termino']].sort_values(by='data_termino', ascending=False)
            
            st.dataframe(
                df_visual, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "projeto": "Projeto (OS)",
                    "cliente": "Cliente",
                    "site": "Site / Navio",
                    "data_termino": "Data de Conclusão"
                }
            )

            st.markdown("#### 📥 Central de Download")
            
            # 4. LÓGICA DE DOWNLOAD
            opcoes_download = df_filtrado['id_os'].tolist()
            
            # Cria um rótulo amigável no selectbox (Ex: "CCV1234 - Petrobras (P-52)")
            formatacao_nomes = {
                row['id_os']: f"{row['projeto']} - {row['cliente']} ({row['site']})" 
                for _, row in df_filtrado.iterrows()
            }

            if opcoes_download:
                os_selecionada = st.selectbox("Selecione o relatório que deseja baixar:", opcoes_download, format_func=lambda x: formatacao_nomes[x])
                
                # Encontra o nome do arquivo Word correspondente ao ID selecionado
                nome_arquivo = df_filtrado[df_filtrado['id_os'] == os_selecionada]['nome_arquivo_word'].values[0]
                caminho_arquivo = os.path.join(PASTA_REPOSITORIO, nome_arquivo)

                # Verifica se o arquivo Word físico realmente existe na pasta do servidor
                if os.path.exists(caminho_arquivo):
                    with open(caminho_arquivo, "rb") as file:
                        st.download_button(
                            label=f"📥 Baixar Documento (.docx)",
                            data=file,
                            file_name=nome_arquivo,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            type="primary"
                        )
                else:
                    st.warning(f"O arquivo '{nome_arquivo}' está registrado no banco de dados, mas o documento físico não foi encontrado na pasta 'repositorio_arquivos'. (Pode ser um relatório de simulação).")
        else:
            st.warning("Nenhum projeto encontrado com esse código.")