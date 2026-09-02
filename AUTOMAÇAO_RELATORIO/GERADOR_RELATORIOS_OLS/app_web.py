import streamlit as st
import os
from automacoes.gerador_relatorio import montar_relatorio_word
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import numpy as np
from automacoes.blocos.bloco_assinaturas import injetar_assinaturas_finais
from automacoes.blocos.bloco_assinaturas import injetar_assinatura_tecnico
import qrcode
import socket
from io import BytesIO
import time
import shutil
import json
from docx import Document
from automacoes.blocos.dicionario_clientes import CATALOGO

# =========================================================
# CONFIGURAÇÃO DA PÁGINA (Sempre a primeira linha do Streamlit!)
# =========================================================
st.set_page_config(page_title="OLS - Gerador de Relatórios", page_icon="📄", layout="wide")

os.makedirs("../cache", exist_ok=True)

# =========================================================
# BLOCO 0: CONEXÃO MOBILE (POP-UP)
# =========================================================

# 1. Função inteligente para descobrir o IP do notebook na rede
def descobrir_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Não precisa ter internet, ele só usa isso para forçar a rota de rede local
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# 2. Criando o Pop-up (Dialog)
@st.dialog("📱 Acesso pelo Celular")
def mostrar_qr_code():
    ip = descobrir_ip()
    url = f"http://{ip}:8501"
    
    st.markdown("Escaneie o código abaixo com a câmera do seu celular para preencher o relatório na palma da mão.")
    
    # Gerando a imagem do QR Code
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    
    # Convertendo para o Streamlit ler
    buf = BytesIO()
    img_qr.save(buf, format="PNG")
    
    # Exibindo no meio do pop-up
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(buf, use_container_width=True)
        
    st.info(f"🔗 Link direto: {url}")

# 3. O botão chamativo na tela principal
if st.button("📲 Usar no Smartphone", type="primary"):
    mostrar_qr_code()

st.markdown("---")
# Configuração da página para ocupar a tela toda do celular/PC
#st.set_page_config(page_title="OLS - Gerador de Relatórios", page_icon="📄", layout="wide")
st.title("📄 Gerador de Field Service Report")
st.markdown("---")

# um único número de identificação nasce e não muda mais
if "carimbo_tempo" not in st.session_state:
    st.session_state.carimbo_tempo = int(time.time())

# =========================================================
# 🌟 O GRANDE SEPARADOR: ABAS DO SISTEMA
# =========================================================
aba1, aba2 = st.tabs(["📄 Relatório do Cliente", "⚙️ Checklist de Intervenções (Banco de Dados)"])

# =========================================================
# ABA 1: TODO O SEU GERADOR DE WORD FICA AQUI DENTRO
# =========================================================
with aba1:
# =========================================================
# BLOCO 1: CABEÇALHO BÁSICO
# =========================================================
    st.subheader("1. Informações do Serviço")

    # Criamos colunas para ficar organizado lado a lado (no celular, ele empilha automático!)
    col1, col2 = st.columns(2)

    with col1:
        # 1. A caixinha inteligente de Clientes
        cliente_selecionado = st.selectbox("Cliente", list(CATALOGO.keys()))
        
        # Se ele escolher "Outro...", abre um campo para ele digitar o nome novo
        if cliente_selecionado == "Outro...":
            cliente = st.text_input("Digite o nome do Cliente (Novo)")
        else:
            cliente = cliente_selecionado
            
        projeto = st.text_input("Projeto", placeholder="Ex: CCV2508-1099")
        ticket = st.text_input("Ticket do NOC")
        telefone = st.text_input("Telefone")
        inicio = st.text_input("Início", placeholder="DD-MMM-AA")

    with col2:
        # 2. A caixinha de Site puxa a lista baseada no Cliente escolhido!
        site_selecionado = st.selectbox("Site", CATALOGO[cliente_selecionado])
        
        # Válvula de escape para navios novos
        if site_selecionado == "Outro...":
            site = st.text_input("Digite o nome do Site/Navio (Novo)")
        else:
            site = site_selecionado
            
        local = st.text_input("Local", placeholder="Ex: Bacia de Campos-RJ")
        contato = st.text_input("Contato", placeholder="Ex: Johnny Astine")
        tecnico = st.text_input("Técnico(s)", placeholder="Ex: Cesar/André")
        termino = st.text_input("Término", placeholder="DD-MMM-AA")

    st.markdown("---")
    # =========================================================
    # BLOCO 2: TIPO DE SERVIÇO
    # =========================================================
    st.subheader("2. Tipo de Serviço")

    # Vamos usar 3 colunas para as caixinhas não ficarem uma tripa gigante para baixo
    col_s1, col_s2, col_s3 = st.columns(3)

    with col_s1:
        serv_inst = st.checkbox("Survey")
        serv_prev = st.checkbox("Manutenção")

    with col_s2:
        serv_corr = st.checkbox("Instalação")
        serv_com = st.checkbox("Mudança de locação")

    with col_s3:
        serv_desmob = st.checkbox("Comissionamento")
        serv_outro = st.checkbox("Desinstalação")

    st.markdown("---")
    # =========================================================
    # BLOCO 3: ATIVIDADES (Dinâmico com Memória)
    # =========================================================
    st.subheader("3. Relato de Atividades")

    # 1. Criamos a "memória" para a lista de atividades (se ela ainda não existir)
    if "lista_atividades" not in st.session_state:
        # Já começa com uma linha em branco por padrão
        st.session_state.lista_atividades = [{"data": "", "descricao": "", "status": "Concluído"}]

    # 2. Desenhamos cada atividade que está na memória
    for i, atividade in enumerate(st.session_state.lista_atividades):
        st.markdown(f"**Atividade {i+1}**")
        
        # Colunas com tamanhos diferentes (A descrição ganha mais espaço)
        col1, col2, col3 = st.columns([2, 5, 2])
        
        with col1:
            atividade["data"] = st.text_input("Data", value=atividade["data"], key=f"data_{i}")
        with col2:
            atividade["descricao"] = st.text_input("Descrição", value=atividade["descricao"], key=f"desc_{i}")
        with col3:
            # Selectbox já padronizado para evitar erros de digitação
            atividade["status"] = st.selectbox("Status", ["Concluído", "Pendente", "Em Andamento"], index=["Concluído", "Pendente", "Em Andamento"].index(atividade["status"]), key=f"status_{i}")

    # 3. Botão para adicionar nova linha
    if st.button("➕ Adicionar Linha de Atividade"):
        # Adiciona uma nova linha vazia na memória
        st.session_state.lista_atividades.append({"data": "", "descricao": "", "status": "Concluído"})
        st.rerun() # Recarrega a página para a nova linha aparecer na hora

    st.markdown("---")
    # =========================================================
    # BLOCO 4: MATERIAIS / EQUIPAMENTOS
    # =========================================================
    st.subheader("4. Materiais / Equipamentos")

    # 1. Memória atualizada com os campos exatos da sua interface
    if "lista_materiais" not in st.session_state:
        st.session_state.lista_materiais = [{"qtd": "", "descricao": "", "sn": "", "asset": "", "acao": "Adicionado"}]

    # 2. Desenhando as 5 colunas baseadas na sua imagem
    for i, material in enumerate(st.session_state.lista_materiais):
        st.markdown(f"**Item {i+1}**")
        
        # Ajustando a largura das 5 colunas (A Descrição ganha o maior espaço)
        col1, col2, col3, col4, col5 = st.columns([1, 3, 2, 2, 2])
        
        with col1:
            material["qtd"] = st.text_input("Qtd", value=material["qtd"], key=f"mat_qtd_{i}")
        with col2:
            material["descricao"] = st.text_input("Descrição do Equipamento", value=material["descricao"], key=f"mat_desc_{i}")
        with col3:
            material["sn"] = st.text_input("Serial Number", value=material["sn"], key=f"mat_sn_{i}")
        with col4:
            material["asset"] = st.text_input("Asset Tag", value=material["asset"], key=f"mat_asset_{i}")
        with col5:
            # A caixa de seleção com as suas opções exatas
            opcoes_acao = ["Adicionado", "Removido", "N/A"]
            
            # Garante que ele vai lembrar qual opção o técnico escolheu se a página recarregar
            idx = opcoes_acao.index(material["acao"]) if material["acao"] in opcoes_acao else 0
            material["acao"] = st.selectbox("Ação", opcoes_acao, index=idx, key=f"mat_acao_{i}")

    # 3. Botão para adicionar nova linha
    if st.button("➕ Adicionar Material", key="btn_add_mat"):
        st.session_state.lista_materiais.append({"qtd": "", "descricao": "", "sn": "", "asset": "", "acao": "Adicionado"})
        st.rerun()

    st.markdown("---")
    # =========================================================
    # BLOCO 5: SERVICE LOG (APONTAMENTO DE HORAS)
    # =========================================================
    st.subheader("5. Service Log (Apontamento de Horas)")

    # 1. Memória para a lista de horas
    if "lista_horas" not in st.session_state:
        st.session_state.lista_horas = [{"tipo": "1 - Trabalho Onshore", "data": "", "inicio": "", "fim": "", "descricao": ""}]

    # 2. Desenhando as colunas conforme o seu layout
    for i, apontamento in enumerate(st.session_state.lista_horas):
        st.markdown(f"**Apontamento {i+1}**")
        
        # Proporção: Dropdown médio, 3 campos curtos de data/hora, e a descrição ganha o maior espaço
        col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 4])
        
        with col1:
            opcoes_tipo = [
                "1 - Trabalho Onshore",
                "2 - Trabalho Offshore",
                "3 - Stand-By (On)",
                "4 - Stand-By (Off)",
                "5 - Deslocamento Terrestre",
                "6 - Deslocamento Aéreo",
                "7 - Voo Offshore",
                "8 - Escritório/Warehouse"
            ]
            # Salva a escolha do técnico na memória
            idx = opcoes_tipo.index(apontamento["tipo"]) if apontamento["tipo"] in opcoes_tipo else 0
            apontamento["tipo"] = st.selectbox("Tipo", opcoes_tipo, index=idx, key=f"hora_tipo_{i}")
            
        with col2:
            apontamento["data"] = st.text_input("Data", value=apontamento["data"], key=f"hora_data_{i}")
        with col3:
            apontamento["inicio"] = st.text_input("Início (00:00)", value=apontamento["inicio"], key=f"hora_inicio_{i}")
        with col4:
            apontamento["fim"] = st.text_input("Fim (00:00)", value=apontamento["fim"], key=f"hora_fim_{i}")
        with col5:
            apontamento["descricao"] = st.text_input("Descrição curta da atividade", value=apontamento["descricao"], key=f"hora_desc_{i}")

    # 3. Botão para adicionar nova linha de apontamento
    if st.button("➕ Adicionar Apontamento", key="btn_add_hora"):
        st.session_state.lista_horas.append({"tipo": "1 - Trabalho Onshore", "data": "", "inicio": "", "fim": "", "descricao": ""})
        st.rerun()

    st.markdown("---")
    # =========================================================
    # BLOCO 6: ANEXO FOTOGRÁFICO (Com Legendas)
    # =========================================================
    st.subheader("6. Anexo Fotográfico")

    aba_galeria, aba_camera = st.tabs(["📁 Galeria / Arquivos", "📸 Usar Câmera"])

    # Essa lista vai guardar as fotos "brutas" que vieram das abas
    fotos_brutas = []

    with aba_galeria:
        fotos_carregadas = st.file_uploader(
            "Selecione ou arraste as fotos (JPG, PNG)", 
            type=["jpg", "jpeg", "png"], 
            accept_multiple_files=True
        )
        if fotos_carregadas:
            fotos_brutas.extend(fotos_carregadas)

    with aba_camera:
        foto_tirada = st.camera_input("Tire uma foto do equipamento/serviço")
        if foto_tirada:
            fotos_brutas.append(foto_tirada)

    # --- ÁREA DAS LEGENDAS ---
    # Lista final que vai guardar a foto associada à sua legenda
    fotos_com_legenda = []

    if len(fotos_brutas) > 0:
        st.markdown("#### 📝 Adicionar Legendas")
        
        # Para cada foto carregada, criamos uma miniatura e um campo de texto ao lado
        for i, arquivo_foto in enumerate(fotos_brutas):
            col_img, col_txt = st.columns([1, 3])
            
            with col_img:
                # Mostra a miniatura da foto na tela
                st.image(arquivo_foto, use_container_width=True)
                
            with col_txt:
                # Campo de texto para a legenda (usamos um key único para não dar erro)
                legenda_digitada = st.text_input(f"Legenda da Foto {i+1}", key=f"leg_foto_{i}")
            
            # Guardamos a foto da memória e a legenda digitada juntos
            fotos_com_legenda.append({
                "arquivo_memoria": arquivo_foto,
                "legenda": legenda_digitada
            })

    st.markdown("---")
    # =========================================================
    # BLOCO 7: DADOS E ASSINATURA DA BASE
    # =========================================================
    st.subheader("7. Dados de Assinatura")

    st.markdown("**Dados do Técnico:**")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        nome_tecnico_ass = st.text_input("Nome do Técnico:", placeholder="Ex: João Victor", key="tec_nome")
    with col_t2:
        data_tecnico_ass = st.text_input("Data (Técnico):", placeholder="DD/MMM/AA", key="tec_data")

    st.markdown("**Quadro de Assinatura (Técnico):**")
    # 1. AS ABAS DO TÉCNICO
    aba_tec_desenho, aba_tec_upload = st.tabs(["🖌️ Desenhar na Tela", "📁 Upload de Imagem"])

    with aba_tec_desenho:
        canvas_tecnico = st_canvas(
            stroke_width=2, stroke_color="#000000", background_color="rgba(0, 0, 0, 0)",
            height=150, width=400, drawing_mode="freedraw", key="canvas_tec",
        )
    with aba_tec_upload:
        upload_ass_tec = st.file_uploader("Ou envie a foto da assinatura", type=["png", "jpg"], key="up_tec")

    # --- NOVA LÓGICA: O BOTÃO SILENCIOSO DO TÉCNICO ---
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Aplicar Assinatura do Técnico", type="secondary", use_container_width=True):
        caminho_ass_tec = "../cache/temp_ass_tec.png"
        # Faz a faxina do lixo antigo antes de qualquer coisa
        if os.path.exists(caminho_ass_tec):
            try:
                os.remove(caminho_ass_tec)
            except Exception as e:
                pass # Ignora se o Windows estiver bloqueando o arquivo no momento
        assinatura_capturada = False
        
        # 1. Prioriza o Upload, se existir
        if upload_ass_tec is not None:
            with open(caminho_ass_tec, "wb") as f:
                f.write(upload_ass_tec.getbuffer())
            assinatura_capturada = True
            
        # 2. Caso contrário, pega o desenho do Canvas (TRAVA DE SEGURANÇA APLICADA)
        elif canvas_tecnico is not None and canvas_tecnico.image_data is not None:
            # Verifica se o usuário REALMENTE fez algum traço no quadro
            if canvas_tecnico.json_data is not None and len(canvas_tecnico.json_data.get("objects", [])) > 0:
                imagem_pil = Image.fromarray(canvas_tecnico.image_data.astype('uint8'), 'RGBA')
                imagem_pil.save(caminho_ass_tec)
                assinatura_capturada = True
            
        # 3. Dá o feedback visual sem gerar download
        if assinatura_capturada:
            st.success("✅ Assinatura do técnico salva na memória! Continue o preenchimento ou vá para o Bloco 8.")
            # Registra no cérebro do Streamlit que a assinatura existe
            st.session_state['caminho_ass_tec'] = caminho_ass_tec
        else:
            st.warning("⚠️ Por favor, desenhe ou envie a assinatura antes de clicar em aplicar.")
    st.markdown("---")

    # =========================================================
    # BLOCO 8: ESTAÇÃO DE ASSINATURAS (PÓS-PROCESSAMENTO)
    # =========================================================
    st.markdown("---")
    st.subheader("8. Assinatura do Cliente (Pós-Processamento)")
    st.info("💡 Etapa feita APÓS a geração do relatório acima. O cliente revisa o documento e assina digitalmente.")

    st.markdown("##### Passo 1: Relatório Base")
    # 1. AQUI O TÉCNICO SOBE O ARQUIVO QUE VEIO PELO BLUETOOTH (OU DO PRÓPRIO PC)
    relatorio_pronto = st.file_uploader("Anexe o relatório (.docx) recém-gerado", type=["docx"], key="upload_docx")

    st.markdown("**Dados do Cliente:**")
    col_c1, col_c2 = st.columns(2)

    with col_c1:
        nome_cliente_ass = st.text_input("Nome do Cliente:", placeholder="Ex: Johnny Astine", key="cli_nome_base")
    with col_c2:
        data_cliente_ass = st.text_input("Data (Cliente):", placeholder="DD/MMM/AA", key="cli_data_base")

    # --- CAMPOS DE IDENTIFICAÇÃO DO CLIENTE ---
    st.markdown("**Documentação do Cliente:**")
    col_doc1, col_doc2 = st.columns(2)
    with col_doc1:
        imo_cliente = st.text_input("IMO:", placeholder="Nº IMO", key="cli_imo")
    with col_doc2:
        ab_cliente = st.text_input("AB:", placeholder="Nº AB", key="cli_ab")

    col_doc3, col_doc4 = st.columns(2)
    with col_doc3:
        cir_cliente = st.text_input("CIR:", placeholder="Nº CIR", key="cli_cir")
    with col_doc4:
        sdpo_cliente = st.text_input("SDPO:", placeholder="Nº SDPO", key="cli_sdpo")
    # ------------------------------------------------

    st.markdown("##### Passo 2: Assinatura do Cliente")
    # AS ABAS DO CLIENTE
    aba_cli_desenho, aba_cli_upload = st.tabs(["🖌️ Desenhar na Tela", "📁 Upload de Imagem"])

    with aba_cli_desenho:
        canvas_cliente = st_canvas(
            stroke_width=2, stroke_color="#000000", background_color="rgba(0, 0, 0, 0)",
            height=150, width=400, drawing_mode="freedraw", key="canvas_cli",
        )
        
    with aba_cli_upload:
        upload_ass_cli = st.file_uploader("Ou envie a foto da assinatura do cliente", type=["png", "jpg"], key="up_cli")
        
    st.markdown("<br>", unsafe_allow_html=True)

    # =========================================================
    # O BOTÃO GATILHO (O MAESTRO DA OPERAÇÃO)
    # =========================================================
    if st.button("Aplicar Assinaturas e Baixar Relatório", type="secondary", use_container_width=True):
            if relatorio_pronto:
                
                caminho_ass_cli = None
                
                # 1. Verifica se o cliente fez UPLOAD ou DESENHOU
                if upload_ass_cli is not None:
                    caminho_ass_cli = "../cache/temp_ass_cli.png"
                    with open(caminho_ass_cli, "wb") as f:
                        f.write(upload_ass_cli.getbuffer())
                        
                elif canvas_cliente is not None and canvas_cliente.image_data is not None:
                    imagem_pil = Image.fromarray(canvas_cliente.image_data.astype('uint8'), 'RGBA')
                    caminho_ass_cli = "../cache/temp_ass_cli.png"
                    imagem_pil.save(caminho_ass_cli)

                # 2. RECUPERA A ASSINATURA DO TÉCNICO DA MEMÓRIA
                # Verifica se o técnico apertou o "Botão Silencioso" lá no Bloco 7
                caminho_ass_tec = st.session_state.get('caminho_ass_tec', None)
                
                # (Segurança extra: se a página recarregou mas o arquivo ainda está na pasta cache)
                import os
                if not caminho_ass_tec and os.path.exists("../cache/temp_ass_tec.png"):
                    caminho_ass_tec = "../cache/temp_ass_tec.png"

                # 3. Salva o Word que foi feito upload temporariamente
                caminho_docx_temp = "../cache/temp_relatorio_base.docx"
                with open(caminho_docx_temp, "wb") as f:
                    f.write(relatorio_pronto.getbuffer())

                try:
                    # 4. CHAMA O NOVO MOTOR UNIVERSAL
                    docx_finalizado = injetar_assinaturas_finais(
                        caminho_docx_temp,
                        caminho_imagem_cliente=caminho_ass_cli,
                        caminho_imagem_tecnico=caminho_ass_tec,
                        nome_cliente=nome_cliente_ass,
                        data_cliente=data_cliente_ass,
                        imo_cliente=imo_cliente,
                        ab_cliente=ab_cliente,
                        cir_cliente=cir_cliente,
                        sdpo_cliente=sdpo_cliente,
                        nome_tecnico=nome_tecnico_ass, 
                        data_tecnico=data_tecnico_ass
                    )
                    
                    st.success("✅ Relatório finalizado! Todas as assinaturas pendentes foram consolidadas.")
                    
                    # 5. Cria o botão de download FINAL
                    with open(docx_finalizado, "rb") as file:
                        st.download_button(
                            label="📥 Baixar Relatório Final Assinado",
                            data=file,
                            file_name="Relatorio_OLS_Finalizado.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key="btn_down_final"
                        )
                except Exception as e:
                    st.error(f"Erro ao aplicar assinaturas: {e}")
                    
            else:
                st.warning("⚠️ Por favor, anexe o relatório (.docx) base para prosseguir.")
    # =========================================================
    # BOTÃO DE GERAR E DOWNLOAD
    # =========================================================
    if st.button("🚀 GERAR RELATÓRIO OLS", use_container_width=True, type="primary"):
        
        # 1. Empacotando o Bloco 1 (Exatamente como fazíamos no desktop)
        pacote_cabecalho = {
            "Projeto": projeto, "Local": local, "Ticket": ticket, "Cliente": cliente,
            "Site": site, "Contato": contato, "Telefone": telefone, "Técnico(s)": tecnico,
            "Início": inicio, "Término": termino
        }
        
        # Pacotes vazios por enquanto só para não quebrar a função do motor
        # 2. Empacotando o Bloco 2 (Caixinhas de Serviço)
        pacote_servicos = {
            "Survey": serv_inst,
            "Manutenção": serv_prev,
            "Instalação": serv_corr,
            "Mudança de locação": serv_com,
            "Comissionamento": serv_desmob,
            "Desinstalação": serv_outro
        }
        pacote_atividades = st.session_state.lista_atividades
        pacote_materiais = st.session_state.lista_materiais
        pacote_horas = st.session_state.lista_horas
        # =======================================================
        # LÓGICA DE CAPTURA DA ASSINATURA DO TÉCNICO
        # =======================================================
        caminho_ass_tec = None

        # 1. Verifica se o técnico fez UPLOAD de uma imagem
        if upload_ass_tec is not None:
            caminho_ass_tec = "../cache/temp_ass_tec.png"
            with open(caminho_ass_tec, "wb") as f:
                f.write(upload_ass_tec.getbuffer())
                
        # 2. Se não fez upload, extrai o desenho do QUADRO DIGITAL
        elif canvas_tecnico is not None and canvas_tecnico.image_data is not None:
            # Transforma os pixels do quadro em uma imagem de verdade usando a biblioteca PIL
            imagem_pil = Image.fromarray(canvas_tecnico.image_data.astype('uint8'), 'RGBA')
            caminho_ass_tec = "../cache/temp_ass_tec.png"
            imagem_pil.save(caminho_ass_tec)

        # 8. Empacotando as informações do Técnico (Agora com a imagem!)
        # 8. Empacotando as informações (Técnico + Textos do Cliente)
        # 8. Empacotando as informações (Técnico + Textos do Cliente)
        pacote_assinaturas = {
            "nome_tecnico": nome_tecnico_ass,
            "data": data_tecnico_ass,
            "caminho_assinatura": caminho_ass_tec,
            
            "nome_cliente": nome_cliente_ass, 
            "data_cliente": data_cliente_ass,
            
            # --- NOVOS DADOS ENVIADOS PARA O MOTOR ---
            "imo_cliente": imo_cliente,
            "ab_cliente": ab_cliente,
            "cir_cliente": cir_cliente,
            "sdpo_cliente": sdpo_cliente
        }
        pacote_fotos = []
        
        for i, item in enumerate(fotos_com_legenda):
            nome_temp = f"../cache/temp_foto_{i}.jpg"
            
            # Salva fisicamente
            with open(nome_temp, "wb") as f:
                f.write(item["arquivo_memoria"].getbuffer())
                
            # Adiciona um DICIONÁRIO no pacote, com o caminho e a legenda
            pacote_fotos.append({
                "caminho": nome_temp,
                "legenda": item["legenda"]
            })

        try:    
            # 1. Chama a linha de montagem e CAPTURA O NOME EXATO DO ARQUIVO
            with st.spinner("Gerando o relatório no motor de engenharia..."):
                nome_arquivo_gerado = montar_relatorio_word(pacote_cabecalho, pacote_servicos, pacote_atividades, pacote_materiais, pacote_horas, pacote_assinaturas, pacote_fotos)
            
            # --- NOVO: injeta a assinatura do técnico (se já tiver sido preenchida) ---
            doc_com_tecnico = Document(nome_arquivo_gerado)
            doc_com_tecnico = injetar_assinatura_tecnico(
                doc_com_tecnico,
                caminho_imagem_tecnico=caminho_ass_tec,
                nome_tecnico=nome_tecnico_ass,
                data_tecnico=data_tecnico_ass
                )
            doc_com_tecnico.save(nome_arquivo_gerado)
            # =======================================================
            # NOVA LÓGICA: PREPARAÇÃO PARA O BANCO DE DADOS (ENVIAR_BD)
            # =======================================================
            # A. Cria um ID Único baseado no Projeto e no Relógio do PC (ex: CCV2508-1722108500)
            nome_projeto = projeto.replace(" ", "") if projeto else "SemProjeto"
            id_unico_os = f"{nome_projeto}-{st.session_state.carimbo_tempo}"
            
            novo_nome_docx = f"Relatorio_{id_unico_os}.docx"
            pasta_enviar_bd = "../ENVIAR_BD" 
            os.makedirs(pasta_enviar_bd, exist_ok=True)
            
            caminho_docx_espera = os.path.join(pasta_enviar_bd, novo_nome_docx)
            shutil.copy(nome_arquivo_gerado, caminho_docx_espera)
            
            # 2. ---> A LIMPEZA ENTRA EXATAMENTE AQUI <---
            for foto_temp in pacote_fotos:
                # Pega o caminho do arquivo e apaga do HD
                if os.path.exists(foto_temp["caminho"]):
                    os.remove(foto_temp["caminho"])
            if caminho_ass_tec and os.path.exists(caminho_ass_tec):
                os.remove(caminho_ass_tec)        
            # 3. Prepara o botão de Download com o NOME REAL do arquivo
            with open(nome_arquivo_gerado, "rb") as file:
                btn_download = st.download_button(
                    label="✅ Relatório Pronto! Clique para Baixar",
                    data=file,
                    file_name=os.path.basename(nome_arquivo_gerado),
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                
        except Exception as e:
            st.error(f"❌ Ocorreu um erro no motor: {e}")
            

with aba2:
    st.subheader("⚙️ Coleta de Dados Estratégicos (Banco de Dados)")
    st.info("💡 Adicione os equipamentos modificados abaixo. Isso não vai para o Word, serve exclusivamente para alimentar os gráficos do nosso servidor.")

    # 1. Memória do "Carrinho"
    if "lista_intervencoes" not in st.session_state:
        st.session_state.lista_intervencoes = []

    # =========================================================
    # A MÁGICA DA LISTA DINÂMICA (Ponteiro da Aba 1)
    # =========================================================
    opcoes_atividade_dinamica = []
    
    # Ele só adiciona a opção na lista se a caixinha correspondente foi marcada lá em cima
    if serv_prev: 
        opcoes_atividade_dinamica.append("Manutenção")
    if serv_corr: 
        opcoes_atividade_dinamica.append("Instalação")
    if serv_outro: 
        opcoes_atividade_dinamica.append("Desinstalação")
    if serv_com: 
        opcoes_atividade_dinamica.append("Mudança de Locação")
    # (Survey e Comissionamento geralmente não levam peças de hardware, mas podem ser adicionados se quiser)

    # =========================================================
    # TRAVA DE SEGURANÇA
    # =========================================================
    if len(opcoes_atividade_dinamica) == 0:
        # Se a lista estiver vazia, ele esconde o formulário e mostra o aviso
        st.warning("⚠️ Nenhum serviço de intervenção física (Manutenção, Instalação, etc.) foi marcado na Aba 1.")
        st.markdown("Volte ao **Bloco 2 (Tipo de Serviço)** e marque as atividades realizadas para liberar o registro de equipamentos.")
        
    else:
        # Se tem algo marcado, o formulário é exibido normalmente!
        catalogo_equipamentos = {
            "Rack / Infraestrutura": ["Switch", "Probe", "Modem", "Nobreak", "Juniper"],
            "CFTV": ["Câmera", "Encoder"],
            "Antenas LEO (Baixa Órbita)": ["Intellian", "Kymeta", "Starlink"],
            "Antenas GEO (Geoestacionária)": ["Antena VSAT"],
            "Outro...": ["Outro..."]
        }
        
        opcoes_causas = [
            "N/A (Não se aplica)",
            "Mal funcionamento do aparelho",
            "Falha de configuração",
            "Falta de Energia (Apagão)",
            "Oscilação na Rede (Surtos/Picos)",
            "Problema de Infraestrutura",
            "Solicitação do Cliente",
            "Fim de Contrato"
        ]

        st.markdown("#### 🛒 Adicionar Equipamento ao Registro")
        
        col_atv, col_cat, col_eq = st.columns(3)
        
        with col_atv:
            # A caixinha agora puxa APENAS o que foi marcado na Aba 1
            atividade_sel = st.selectbox("Atividade", opcoes_atividade_dinamica, key="add_atv")
        
        with col_cat:
            categoria_sel = st.selectbox("Categoria", list(catalogo_equipamentos.keys()), key="add_cat")
            
        with col_eq:
            equipamento_sel = st.selectbox("Equipamento", catalogo_equipamentos[categoria_sel], key="add_eq")
            
        col_causa, col_add = st.columns([3, 1])
        
        with col_causa:
            indice_padrao = 0 if atividade_sel == "Instalação" else 1
            causa_sel = st.selectbox("Motivo / Causa da Intervenção", opcoes_causas, index=indice_padrao, key="add_causa")
            
        with col_add:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ Adicionar", type="primary", use_container_width=True):
                st.session_state.lista_intervencoes.append({
                    "atividade": atividade_sel,
                    "categoria": categoria_sel,
                    "equipamento": equipamento_sel,
                    "causa": causa_sel if atividade_sel != "Instalação" else "N/A (Não se aplica)"
                })
                st.rerun()

    # (O restante do código da Aba 2 com a listagem e o botão de Enviar JSON continua normalmente abaixo)

    st.markdown("---")
    
    # 4. Exibição da Tabela de Itens Adicionados
    st.markdown("#### 📋 Itens Registrados nesta OS")
    
    if len(st.session_state.lista_intervencoes) == 0:
        st.warning("Nenhum equipamento registrado para o banco de dados ainda.")
    else:
        # Cabeçalho da listagem
        hc1, hc2, hc3, hc4, hc5 = st.columns([2, 2, 2, 3, 1])
        hc1.write("**Atividade**")
        hc2.write("**Categoria**")
        hc3.write("**Equipamento**")
        hc4.write("**Causa**")
        hc5.write("")
        
        st.markdown("---")
        
        # Desenhando cada linha adicionada com botão de excluir
        for i, item in enumerate(st.session_state.lista_intervencoes):
            c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 3, 1])
            c1.write(item['atividade'])
            c2.write(item['categoria'])
            c3.write(item['equipamento'])
            
            # Destaca se for um problema/falha
            icone_causa = "🚨" if item['causa'] != "N/A (Não se aplica)" else "✅"
            c4.write(f"{icone_causa} {item['causa']}")
            
            if c5.button("🗑️ Remover", key=f"del_item_{i}"):
                st.session_state.lista_intervencoes.pop(i)
                st.rerun()
                
    st.markdown("---")
    st.markdown("#### 🚀 Sincronização com o Servidor")
    st.info("Certifique-se de que todas as informações na Aba 1 (Projeto, Horas, etc.) estão preenchidas antes de enviar.")
    
    if st.button("Enviar Dados para o Servidor (JSON)", type="primary", use_container_width=True):
        
        nome_projeto = projeto.replace(" ", "") if projeto else "SemProjeto"
        id_unico_os = f"{nome_projeto}-{st.session_state.carimbo_tempo}"
        
        # 2. O "Ponteiro": Monta o pacote puxando as variáveis lá da Aba 1
        pacote_banco = {
            "id_os": id_unico_os,
            "nome_arquivo_word": f"Relatorio_{id_unico_os}.docx",
            "cabecalho": {
                "Projeto": projeto, "Local": local, "Ticket": ticket, "Cliente": cliente,
                "Site": site, "Contato": contato, "Telefone": telefone, "Técnico": tecnico,
                "Início": inicio, "Término": termino
            },
            "servicos": {
                "Survey": serv_inst, "Manutenção": serv_prev, "Instalação": serv_corr,
                "Mudança de locação": serv_com, "Comissionamento": serv_desmob, "Desinstalação": serv_outro
            },
            "horas": st.session_state.get("lista_horas", []),
            "intervencoes": st.session_state.get("lista_intervencoes", [])
        }
        
        # 3. Salva SÓ o JSON na pasta ENVIAR_BD
        pasta_enviar_bd = "../ENVIAR_BD"
        os.makedirs(pasta_enviar_bd, exist_ok=True)
        
        caminho_json = os.path.join(pasta_enviar_bd, f"Dados_{id_unico_os}.json")
        with open(caminho_json, "w", encoding="utf-8") as f:
            json.dump(pacote_banco, f, ensure_ascii=False, indent=4)
            
        st.success(f"✅ Dados da OS {nome_projeto} enviados para processamento no servidor!")