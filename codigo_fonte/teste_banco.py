import sqlite3
import os
import random
from datetime import datetime, timedelta
import time

# ==========================================
# MAPEAMENTO DO BANCO (O mesmo do banco_dados.py)
# ==========================================
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
CAMINHO_BANCO = os.path.join(DIRETORIO_ATUAL, '..', 'banco_local', 'relatorios.db')

def gerar_dados_falsos(quantidade=50):
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

    print(f"🚀 Iniciando injeção de {quantidade} OSs no banco de dados...")

    for i in range(1, quantidade + 1):
        # ---------------------------------------------------------
        # 1. GERANDO O CABEÇALHO (Tabela relatorios)
        # ---------------------------------------------------------
        projeto = f"CCV26{str(i).zfill(2)}-{random.randint(1000, 9999)}"
        timestamp = int(time.time()) - random.randint(86400, 15000000) # Datas retroativas aleatórias
        id_os = f"{projeto}-{timestamp}"
        nome_docx = f"Relatorio_{id_os}.docx"
        
        # Sorteia quais checkboxes foram marcadas (0 ou 1)
        chk_man = random.choice([0, 1])
        chk_inst = random.choice([0, 1]) if chk_man == 0 else 0 # Evita marcar tudo de uma vez
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
            "01/Ago/2026", "05/Ago/2026", 
            0, chk_inst, 0, chk_man, 0, chk_desinst
        ))

        # ---------------------------------------------------------
        # 2. GERANDO AS HORAS (Tabela service_log)
        # ---------------------------------------------------------
        # Cria de 1 a 3 apontamentos de horas por OS
        for _ in range(random.randint(1, 3)):
            tipo_hr = random.choice(["1 - Trabalho Onshore", "2 - Trabalho Offshore", "5 - Deslocamento Terrestre"])
            inicio_hr = f"{random.randint(7,10):02d}:00"
            fim_hr = f"{random.randint(14,18):02d}:30"
            
            # Cálculo rápido de horas decimais pro banco não ficar vazio
            h1 = datetime.strptime(inicio_hr, "%H:%M")
            h2 = datetime.strptime(fim_hr, "%H:%M")
            total = (h2 - h1).total_seconds() / 3600.0

            cursor.execute('''
                INSERT INTO service_log (
                    id_os, tipo_servico, data_apontamento, hora_inicio, hora_fim, horas_totais, descricao_curta
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                id_os, tipo_hr, "02/Ago/2026", inicio_hr, fim_hr, total, "Atividade de campo"
            ))

        # ---------------------------------------------------------
        # 3. GERANDO O CHECKLIST (Tabela checklist_intervencoes)
        # ---------------------------------------------------------
        # Se a OS teve Manutenção ou Instalação, gera equipamentos mexidos
        atividades_os = []
        if chk_man == 1: atividades_os.append("Manutenção")
        if chk_inst == 1: atividades_os.append("Instalação")
        if chk_desinst == 1: atividades_os.append("Desinstalação")

        if atividades_os:
            for _ in range(random.randint(1, 4)): # Mexeu em 1 a 4 equipamentos
                atv_sorteada = random.choice(atividades_os)
                cat_sorteada = random.choice(list(catalogo_eq.keys()))
                eq_sorteado = random.choice(catalogo_eq[cat_sorteada])
                
                # Regra de ouro da causa
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
    print("✅ Sucesso! O banco de dados agora está lotado de informações falsas e pronto para o BI.")

if __name__ == "__main__":
    gerar_dados_falsos(50)