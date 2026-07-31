import sqlite3
import os

# ==========================================
# 1. MAPEAMENTO DE PASTAS
# ==========================================
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
PASTA_BANCO = os.path.join(DIRETORIO_ATUAL, '..', 'banco_local')
CAMINHO_BANCO = os.path.join(PASTA_BANCO, 'relatorios.db')

# ==========================================
# 2. FUNÇÃO DE CRIAÇÃO DO BANCO E TABELAS
# ==========================================
def inicializar_banco():
    if not os.path.exists(PASTA_BANCO):
        os.makedirs(PASTA_BANCO)

    conn = sqlite3.connect(CAMINHO_BANCO)
    cursor = conn.cursor()

    # --- TABELA 1: INFORMAÇÕES E TIPO DE SERVIÇO (Blocos 1 e 2) ---
    # A Chave Primária será o próprio nome/ID do arquivo (Ex: OS-2026-07-001)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS relatorios (
            id_os TEXT PRIMARY KEY, -- Ex: CCV-5555_Data_Hora (Garante que nunca vai sobrepor)
            nome_arquivo_word TEXT,
            
            projeto TEXT, -- Aqui vai o CCV puro. Pode repetir quantas vezes quiser!
            local TEXT,
            ticket_noc TEXT,
            cliente TEXT,
            site TEXT,
            tecnico TEXT,
            data_inicio TEXT,
            data_termino TEXT,
            
            chk_survey INTEGER DEFAULT 0,
            chk_instalacao INTEGER DEFAULT 0,
            chk_comissionamento INTEGER DEFAULT 0,
            chk_manutencao INTEGER DEFAULT 0,
            chk_mudanca_locacao INTEGER DEFAULT 0,
            chk_desinstalacao INTEGER DEFAULT 0
        )
    ''')

    # --- TABELA 2: SERVICE LOG (Bloco 5) ---
    # Relação de N para 1 (Vários logs de horas podem pertencer a uma mesma id_os)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS service_log (
            id_log INTEGER PRIMARY KEY AUTOINCREMENT,
            id_os TEXT,
            
            -- Bloco 5: Service Log (Apontamento de Horas)
            tipo_servico TEXT,
            data_apontamento TEXT,
            hora_inicio TEXT,
            hora_fim TEXT,   
            horas_totais REAL, 
            descricao_curta TEXT,
            
            FOREIGN KEY (id_os) REFERENCES relatorios(id_os) ON DELETE CASCADE
        )
    ''')
    
    # --- TABELA 3: INTERVENÇÕES E CAUSAS (Aba 2) ---
    # Relação de N para 1 (Vários equipamentos mexidos podem pertencer a uma mesma id_os)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS checklist_intervencoes (
            id_intervencao INTEGER PRIMARY KEY AUTOINCREMENT,
            id_os TEXT,
            
            atividade TEXT,
            categoria TEXT,
            equipamento TEXT,
            causa TEXT,
            
            FOREIGN KEY (id_os) REFERENCES relatorios(id_os) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()
    print(f"✅ Sucesso! Banco de dados estruturado com os inputs OLS em: {CAMINHO_BANCO}")

if __name__ == "__main__":
    inicializar_banco()