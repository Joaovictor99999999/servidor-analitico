import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
import sqlite3
import os
from dicionario_clientes import CATALOGO

st.set_page_config(
    page_title="Servidor OLS | Painel",
    page_icon="📊",
    layout="wide"
)

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
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2099/2099058.png", width=100)
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
    st.subheader("📈 Indicadores Operacionais Gerais")

    # ==========================================
    # 1. CÁLCULO DOS INDICADORES DE TOPO (KPIs)
    # ==========================================
    total_os = len(df_rel)
    total_horas = df_log['horas_totais'].sum() if not df_log.empty else 0
    media_horas = total_horas / total_os if total_os > 0 else 0
    clientes_unicos = df_rel['cliente'].nunique() if not df_rel.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Relatórios Gerados", f"{total_os}")
    col2.metric("Horas Totais Alocadas", f"{total_horas:.1f} h")
    col3.metric("Média de Horas / OS", f"{media_horas:.1f} h")
    col4.metric("Clientes Atendidos", f"{clientes_unicos}")

    st.markdown("---")

    # ==========================================
    # 2. LINHA 1: PRODUTIVIDADE E ESFORÇO
    # ==========================================
    col_graf1, col_graf2 = st.columns(2)
    esconder_menu = {'displayModeBar': False}

    with col_graf1:
        st.subheader("Consumo de Horas por Serviço")
        opcoes_servicos = [
            "1 - Trabalho Onshore", "2 - Trabalho Offshore", 
            "3 - Em Stand-By (Onshore)", "4 - Em Stand-By (Offshore)", 
            "5 - Deslocamento Terrestre", "6 - Deslocamento Aéreo", 
            "7 - Deslocamento Aéreo (Offshore)", "8 - Atividade no Escritório"
        ]
        servicos_selecionados = st.multiselect(
            "Selecione os códigos que deseja comparar:", 
            options=opcoes_servicos, 
            default=["1 - Trabalho Onshore", "2 - Trabalho Offshore", "5 - Deslocamento Terrestre"]
        )
        
        if not df_log.empty:
            # Filtra o banco só para os serviços selecionados
            df_filtrado = df_log[df_log['tipo_servico'].isin(servicos_selecionados)]
            # Agrupa (soma) as horas de cada serviço
            df_agrupado = df_filtrado.groupby('tipo_servico')['horas_totais'].sum().reset_index()
            
            fig1 = px.bar(
                df_agrupado, x="tipo_servico", y="horas_totais", 
                labels={'tipo_servico': 'Tipo de Serviço', 'horas_totais': 'Total de Horas'},
                color="tipo_servico", text_auto='.1f'
            )
            fig1.update_layout(dragmode=False, showlegend=False, xaxis_title="", yaxis_title="")
            st.plotly_chart(fig1, use_container_width=True, key="grafico_horas_servico", config=esconder_menu)
        else:
            st.info("Nenhum dado de horas registrado.")

    with col_graf2:
        st.subheader("Perfil de Atendimento")
        st.markdown("<p style='color:gray; font-size:14px; margin-bottom: 25px;'>Distribuição entre Instalação, Survey, Manutenção, etc.</p>", unsafe_allow_html=True)
        
        if not df_rel.empty:
            # Conta quantas vezes cada caixinha foi marcada (Soma a coluna de 1s e 0s)
            somas_servicos = {
                "Survey": df_rel['chk_survey'].sum(),
                "Instalação": df_rel['chk_instalacao'].sum(),
                "Comissionamento": df_rel['chk_comissionamento'].sum(),
                "Manutenção": df_rel['chk_manutencao'].sum(),
                "Mudança Locação": df_rel['chk_mudanca_locacao'].sum(),
                "Desinstalação": df_rel['chk_desinstalacao'].sum()
            }
            # Converte o dicionário para uma tabela Pandas
            df_perfil = pd.DataFrame(list(somas_servicos.items()), columns=['Serviço', 'Quantidade'])
            df_perfil = df_perfil[df_perfil['Quantidade'] > 0] # Esconde fatias zeradas
            
            fig2 = px.pie(df_perfil, names='Serviço', values='Quantidade', hole=0.3)
            fig2.update_layout(dragmode=False)
            st.plotly_chart(fig2, use_container_width=True, key="grafico_perfil_atendimento", config=esconder_menu)
        else:
            st.info("Nenhum dado de OS registrado.")

    st.markdown("---")

    # ==========================================
    # 3. LINHA 2: INTELIGÊNCIA DE NEGÓCIOS E CLIENTES
    # ==========================================
    col_graf3, col_graf4 = st.columns(2)

    with col_graf3:
        st.subheader("Demandas por Cliente")
        st.markdown("<p style='color:gray; font-size:14px; margin-bottom: 10px;'>Volume de requisições por operadora</p>", unsafe_allow_html=True)
        
        if not df_rel.empty:
            # Conta a quantidade de OS por cliente
            df_clientes = df_rel['cliente'].value_counts().reset_index()
            df_clientes.columns = ['Cliente', 'Quantidade de OS']
            
            fig3 = px.pie(df_clientes, names='Cliente', values='Quantidade de OS')
            fig3.update_traces(textposition='inside', textinfo='percent+label')
            fig3.update_layout(dragmode=False, showlegend=False)
            st.plotly_chart(fig3, use_container_width=True, key="grafico_demandas_cliente", config=esconder_menu)
        else:
            st.info("Nenhum dado de OS registrado.")

    with col_graf4:
        st.subheader("Eficiência Operacional")
        st.markdown("<p style='color:gray; font-size:14px; margin-bottom: 10px;'>Tempo Produtivo vs. Logística (Stand-by e Deslocamentos)</p>", unsafe_allow_html=True)
        
        if not df_log.empty:
            # Função rápida para classificar se o apontamento gerou valor ou não
            def classificar_eficiencia(tipo):
                if not isinstance(tipo, str): return "Outros"
                tipo_lower = tipo.lower()
                if "trabalho" in tipo_lower or "escritório" in tipo_lower:
                    return "Tempo Produtivo"
                else:
                    return "Logística / Stand-by"

            # Aplica a regra e cria uma coluna nova na tabela
            df_log['categoria_eficiencia'] = df_log['tipo_servico'].apply(classificar_eficiencia)
            df_eficiencia = df_log.groupby('categoria_eficiencia')['horas_totais'].sum().reset_index()
            
            fig4 = px.pie(
                df_eficiencia, names='categoria_eficiencia', values='horas_totais', hole=0.5,
                color='categoria_eficiencia', 
                color_discrete_map={"Tempo Produtivo": "#28a745", "Logística / Stand-by": "#dc3545"}
            )
            fig4.update_layout(dragmode=False)
            st.plotly_chart(fig4, use_container_width=True, key="grafico_eficiencia_op", config=esconder_menu)
        else:
            st.info("Nenhum dado de horas registrado.")
# ==========================================
# ABA 2: INTELIGÊNCIA DE FALHAS (Futuro BI)
# ==========================================
with aba2:
    st.subheader("🔧 Inteligência de Falhas e Intervenções")
    st.markdown("<p style='color:gray; font-size:14px; margin-bottom: 25px;'>Análise de ofensores de hardware e causas raiz</p>", unsafe_allow_html=True)

    if df_intervencoes.empty:
        st.info("Nenhum dado de intervenção em equipamento registrado ainda.")
    else:
        # 1. FILTRO DINÂMICO
        # Permite ao gestor ver só as falhas, tirando as Instalações da frente
        opcoes_atv = ["Todas as Atividades"] + list(df_intervencoes['atividade'].unique())
        filtro_atv = st.selectbox("Filtrar por Atividade:", opcoes_atv)
        
        if filtro_atv != "Todas as Atividades":
            df_grafico = df_intervencoes[df_intervencoes['atividade'] == filtro_atv]
        else:
            df_grafico = df_intervencoes

        st.markdown("---")
        
        # 2. CONSTRUÇÃO DOS GRÁFICOS
        col_graf5, col_graf6 = st.columns(2)
        
        with col_graf5:
            st.markdown("**Top Equipamentos com Intervenção**")
            
            # Conta quantas vezes cada equipamento aparece
            df_equip = df_grafico['equipamento'].value_counts().reset_index()
            df_equip.columns = ['Equipamento', 'Volume']
            
            # Gráfico de Barras Horizontais (melhor para ler nomes de peças)
            fig5 = px.bar(
                df_equip, x='Volume', y='Equipamento', orientation='h', 
                text_auto=True, color='Equipamento'
            )
            # Ordena do maior pro menor automaticamente
            fig5.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'}, dragmode=False)
            st.plotly_chart(fig5, use_container_width=True, config=esconder_menu)
            
        with col_graf6:
            st.markdown("**Mapeamento de Causas e Gatilhos**")
            
            # Ignora a causa "N/A" para o gráfico de falhas ficar mais limpo
            df_causas_limpo = df_grafico[df_grafico['causa'] != "N/A (Não se aplica)"]
            
            if not df_causas_limpo.empty:
                df_causas = df_causas_limpo['causa'].value_counts().reset_index()
                df_causas.columns = ['Causa Raiz', 'Ocorrências']
                
                fig6 = px.pie(df_causas, names='Causa Raiz', values='Ocorrências', hole=0.4)
                fig6.update_traces(textposition='inside', textinfo='percent+label')
                fig6.update_layout(showlegend=False, dragmode=False)
                st.plotly_chart(fig6, use_container_width=True, config=esconder_menu)
            else:
                st.success("🎉 Nenhuma falha ou problema registrado no filtro atual!")
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