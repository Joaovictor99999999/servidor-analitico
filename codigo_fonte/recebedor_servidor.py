import os
import time
import json
import sqlite3
import shutil
from datetime import datetime

# ==========================================
# 1. MAPEAMENTO DE PASTAS (O LADO DO SERVIDOR)
# ==========================================
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))

# As pastas oficiais do seu servidor
CAIXA_DE_CORREIO = os.path.join(DIRETORIO_ATUAL, 'CAIXA_DE_CORREIO')
REPOSITORIO = os.path.join(DIRETORIO_ATUAL, 'repositorio_arquivos')
CAMINHO_BANCO = os.path.join(DIRETORIO_ATUAL, 'banco_local', 'relatorios.db')

# Garante que a infraestrutura física exista
os.makedirs(CAIXA_DE_CORREIO, exist_ok=True)
os.makedirs(REPOSITORIO, exist_ok=True)

# ==========================================
# 2. FERRAMENTAS DE DADOS (Cálculos)
# ==========================================
def calcular_horas(inicio, fim):
    """Calcula as horas decimais. (Ex: 08:00 às 12:30 = 4.5)"""
    try:
        t1 = datetime.strptime(inicio, "%H:%M")
        t2 = datetime.strptime(fim, "%H:%M")
        diferenca = (t2 - t1).total_seconds() / 3600.0
        if diferenca < 0: diferenca += 24.0
        return round(diferenca, 2)
    except:
        return 0.0

# ==========================================
# 3. MÓDULOS DE INSERÇÃO (O Padrão de Crescimento)
# ==========================================
# 🧱 BLOCO 1: Tabela Principal (Relatórios)
def inserir_dados_principais(cursor, id_os, nome_docx, cabecalho, servicos):
    cursor.execute('''
        INSERT OR IGNORE INTO relatorios (
            id_os, projeto, local, ticket_noc, cliente, site, contato, telefone, 
            tecnico, data_inicio, data_termino, chk_survey, chk_instalacao, 
            chk_comissionamento, chk_manutencao, chk_mudanca_locacao, chk_desinstalacao,
            nome_arquivo_word
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        id_os, cabecalho.get("Projeto"), cabecalho.get("Local"), cabecalho.get("Ticket"), 
        cabecalho.get("Cliente"), cabecalho.get("Site"), cabecalho.get("Contato"), 
        cabecalho.get("Telefone"), cabecalho.get("Técnico(s)"), cabecalho.get("Início"), 
        cabecalho.get("Término"),
        1 if servicos.get("Survey") else 0, 1 if servicos.get("Instalação") else 0, 
        1 if servicos.get("Comissionamento") else 0, 1 if servicos.get("Manutenção") else 0, 
        1 if servicos.get("Mudança de locação") else 0, 1 if servicos.get("Desinstalação") else 0,
        nome_docx
    ))

# 🧱 BLOCO 2: Tabela Service Log (Horas)
def inserir_service_log(cursor, id_os, lista_horas):
    for apontamento in lista_horas:
        horas_totais = calcular_horas(apontamento.get("inicio"), apontamento.get("fim"))
        cursor.execute('''
            INSERT INTO service_log (
                id_os, tipo_servico, data_apontamento, hora_inicio, hora_fim, horas_totais, descricao_curta
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            id_os, apontamento.get("tipo"), apontamento.get("data"), 
            apontamento.get("inicio"), apontamento.get("fim"), horas_totais, apontamento.get("descricao")
        ))
        
# 🧱 BLOCO 3: Tabela Checklist de Intervenções (Aba 2)
def inserir_intervencoes(cursor, id_os, lista_intervencoes):
    for item in lista_intervencoes:
        cursor.execute('''
            INSERT INTO checklist_intervencoes (
                id_os, atividade, categoria, equipamento, causa
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            id_os, item.get("atividade"), item.get("categoria"), 
            item.get("equipamento"), item.get("causa")
        ))

# ==========================================
# 4. O "ESTOQUISTA" (Processador da Caixa)
# ==========================================
def varrer_caixa_de_correio():
    arquivos = os.listdir(CAIXA_DE_CORREIO)
    arquivos_json = [f for f in arquivos if f.endswith('.json')]

    if not arquivos_json:
        return # Caixa vazia, continua dormindo

    print(f"📥 Recebidos {len(arquivos_json)} relatórios! Processando...")

    # Abre a porta do Banco de Dados
    conn = sqlite3.connect(CAMINHO_BANCO)
    cursor = conn.cursor()

    for arquivo_json in arquivos_json:
        caminho_json = os.path.join(CAIXA_DE_CORREIO, arquivo_json)
        
        try:
            # 1. Lê o pacote que o técnico mandou
            with open(caminho_json, 'r', encoding='utf-8') as f:
                dados = json.load(f)

            id_os = dados.get("id_os")
            nome_docx = dados.get("nome_arquivo_word")
            
            # 2. ⚡ CHAMADA DOS MÓDULOS DE BANCO DE DADOS ⚡
            # É aqui que você chama os blocos (Lego) que criamos lá em cima
            inserir_dados_principais(cursor, id_os, nome_docx, dados.get("cabecalho", {}), dados.get("servicos", {}))
            inserir_service_log(cursor, id_os, dados.get("horas", []))
            inserir_intervencoes(cursor, id_os, dados.get("intervencoes", [])) # <--- AQUI ESTÁ A NOVA LINHA
            # No futuro: inserir_materiais(cursor, id_os, dados.get("materiais", []))

            # 3. Transfere o Word da Caixa para a Biblioteca (Repositorio)
            caminho_docx_origem = os.path.join(CAIXA_DE_CORREIO, nome_docx)
            caminho_docx_destino = os.path.join(REPOSITORIO, nome_docx)
            
            if os.path.exists(caminho_docx_origem):
                shutil.move(caminho_docx_origem, caminho_docx_destino)

            # 4. Sucesso! Salva no banco e apaga o JSON lido
            conn.commit()
            os.remove(caminho_json)
            print(f"✅ Relatório {id_os} guardado com sucesso!")

        except Exception as e:
            conn.rollback() # Se der erro em alguma tabela, ele desfaz tudo para não corromper
            print(f"❌ Erro ao processar o pacote {arquivo_json}: {e}")

    # Fecha a porta do Banco
    conn.close()

# ==========================================
# 5. O LOOP DE TRABALHO 24H
# ==========================================
if __name__ == "__main__":
    print("📡 Recebedor OLS Iniciado. Monitorando a Caixa de Correio...")
    while True:
        varrer_caixa_de_correio()
        time.sleep(10) # Checa a pasta a cada 10 segundos