import sqlite3
import os
import random
from datetime import datetime, timedelta
import time

# ==========================================
# MAPEAMENTO DO BANCO
# ==========================================
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
CAMINHO_BANCO = os.path.join(DIRETORIO_ATUAL, '..', 'banco_local', 'relatorios.db')

def gerar_dados_falsos(quantidade=100): # Aumentei para 100 para o gráfico ficar com uma curva bem legal
    if not os.path.exists(CAMINHO_BANCO):
        print("❌ Banco não encontrado! Rode o banco_dados.py primeiro.")
        return

    conn = sqlite3.connect(CAMINHO_BANCO)
    cursor = conn.cursor()

    # Dicionários para sortear dados realistas
    clientes = ["Petrobras", "Shell", "Equinor", "PRIO", "Modec"]
    sites = ["P-52", "P-55", "FPSO Carioca", "Valente", "P-48", "Flotel"]
    tecnicos = ["João Victor", "Cesar", "André", "Carlos", "Thiago"]
    
    catalogo_eq = {
        "Rack / Infraestrutura": ["Switch", "Probe", "Modem", "Nobreak", "Juniper"],
        "CFTV": ["Câmera", "Encoder"],
        "Antenas LEO (Baixa Órbita)": ["Intellian", "Kymeta", "Starlink"]
    }
    
    causas_falha = [
        "Mal funcionamento do aparelho", "Falha de configuração", 
        "Falta de Energia (Apagão)", "Oscilação na Rede (Surtos/Picos)", 
        "Problema de Infraestrutura"
    ]
    
    meses_pt = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 
                7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}

    print(f"🚀 Iniciando injeção de {quantidade} OSs no banco de dados com datas dinâmicas...")

    # Data base para começar a gerar relatórios (ex: 01 de Julho de 2026)
    data_base = datetime(2026, 1, 1)

    for i in range(1, quantidade + 1):
        # ---------------------------------------------------------
        # LÓGICA DE DATAS DINÂMICAS E TEMPORAIS
        # ---------------------------------------------------------
        # Sorteia um início da OS entre 0 e 150 dias após a data base
        dias_deslocamento = random.randint(0, 150)
        dt_inicio = data_base + timedelta(days=dias_deslocamento)
        
        # A OS dura entre 1 e 15 dias
        duracao_os = random.randint(1, 15)
        dt_termino = dt_inicio + timedelta(days=duracao_os)
        
        # Formatação das datas com o mês em Português
        str_inicio = f"{dt_inicio.day:02d}/{meses_pt[dt_inicio.month]}/{dt_inicio.year}"
        str_termino = f"{dt_termino.day:02d}/{meses_pt[dt_termino.month]}/{dt_termino.year}"

        # ---------------------------------------------------------
        # 1. GERANDO O CABEÇALHO (Tabela relatorios)
        # ---------------------------------------------------------
        projeto = f"CCV26{str(i).zfill(2)}-{random.randint(1000, 9999)}"
        timestamp = int(dt_termino.timestamp()) 
        id_os = f"{projeto}-{timestamp}"
        nome_docx = f"Relatorio_{id_os}.docx"
        
        chk_survey = random.choice([0, 1])
        chk_man = random.choice([0, 1])
        chk_inst = random.choice([0, 1]) if chk_man == 0 else 0 
        chk_comiss = random.choice([0, 1]) if chk_inst == 1 else 0 # Torna comum comissionar quando há instalação
        chk_desinst = random.choice([0, 1])

        cursor.execute('''
            INSERT INTO relatorios (
                id_os, nome_arquivo_word, projeto, local, ticket_noc, cliente, site, 
                tecnico, data_inicio, data_termino, chk_survey, chk_instalacao, 
                chk_comissionamento, chk_manutencao, chk_mudanca_locacao, chk_desinstalacao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            id_os, nome_docx, projeto, "Bacia de Campos", f"INC{random.randint(10000,99999)}", 
            random.choice(clientes), random.choice(sites), random.choice(tecnicos), 
            str_inicio, str_termino, 
            chk_survey, chk_inst, chk_comiss, chk_man, 0, chk_desinst
        ))

        # ---------------------------------------------------------
        # 2. GERANDO AS HORAS (Tabela service_log)
        # ---------------------------------------------------------
        for _ in range(random.randint(1, 3)):
            # Garante que o apontamento de horas acontece dentro da janela da OS
            dias_apontamento = random.randint(0, duracao_os)
            dt_apont = dt_inicio + timedelta(days=dias_apontamento)
            str_apont = f"{dt_apont.day:02d}/{meses_pt[dt_apont.month]}/{dt_apont.year}"

            tipo_hr = random.choice(["1 - Trabalho Onshore", "2 - Trabalho Offshore", "3 - Em Stand-By (Onshore)", "4 - Em Stand-By (Offshore)", "5 - Deslocamento Terrestre", "6 - Deslocamento Aéreo", "7 - Deslocamento Aéreo (Offshore)", "8 - Atividade no Escritório"])
            inicio_hr = f"{random.randint(7,10):02d}:00"
            fim_hr = f"{random.randint(14,18):02d}:30"
            
            h1 = datetime.strptime(inicio_hr, "%H:%M")
            h2 = datetime.strptime(fim_hr, "%H:%M")
            total = (h2 - h1).total_seconds() / 3600.0

            cursor.execute('''
                INSERT INTO service_log (
                    id_os, tipo_servico, data_apontamento, hora_inicio, hora_fim, horas_totais, descricao_curta
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                id_os, tipo_hr, str_apont, inicio_hr, fim_hr, total, "Atividade de campo"
            ))

        # ---------------------------------------------------------
        # 3. GERANDO O CHECKLIST (Tabela checklist_intervencoes)
        # ---------------------------------------------------------
        atividades_os = []
        if chk_man == 1: atividades_os.append("Manutenção")
        if chk_inst == 1: atividades_os.append("Instalação")
        if chk_desinst == 1: atividades_os.append("Desinstalação")

        if atividades_os:
            for _ in range(random.randint(1, 4)): 
                atv_sorteada = random.choice(atividades_os)
                cat_sorteada = random.choice(list(catalogo_eq.keys()))
                eq_sorteado = random.choice(catalogo_eq[cat_sorteada])
                
                if atv_sorteada == "Instalação":
                    causa = "N/A (Não se aplica)"
                elif atv_sorteada == "Desinstalação":
                    causa = random.choice(["Solicitação do Cliente", "Fim de Contrato"])
                else:
                    causa = random.choice(causas_falha)

                cursor.execute('''
                    INSERT INTO checklist_intervencoes (
                        id_os, atividade, categoria, equipamento, causa
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    id_os, atv_sorteada, cat_sorteada, eq_sorteado, causa
                ))

    conn.commit()
    conn.close()
    print("✅ Sucesso! O banco de dados agora está com uma linha do tempo realista para testes.")

if __name__ == "__main__":
    gerar_dados_falsos(100)