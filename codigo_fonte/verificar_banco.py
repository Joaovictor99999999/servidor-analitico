import sqlite3
import os

# Caminho para o banco de dados
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
CAMINHO_BANCO = os.path.join(DIRETORIO_ATUAL, '..', 'banco_local', 'relatorios.db')

def checar_status():
    if not os.path.exists(CAMINHO_BANCO):
        print("❌ Banco de dados não encontrado no caminho especificado.")
        return

    try:
        conn = sqlite3.connect(CAMINHO_BANCO)
        cursor = conn.cursor()

        print("\n📊 STATUS DO BANCO DE DADOS OLS 📊")
        print("-" * 35)

        # Checando Tabela 1
        cursor.execute("SELECT COUNT(*) FROM relatorios")
        qtd_relatorios = cursor.fetchone()[0]
        print(f"📄 Relatórios (OS): {qtd_relatorios} linhas")

        # Checando Tabela 2
        cursor.execute("SELECT COUNT(*) FROM service_log")
        qtd_horas = cursor.fetchone()[0]
        print(f"⏱️ Apontamentos de Horas: {qtd_horas} linhas")

        # Checando Tabela 3
        cursor.execute("SELECT COUNT(*) FROM checklist_intervencoes")
        qtd_intervencoes = cursor.fetchone()[0]
        print(f"🔧 Intervenções e Peças: {qtd_intervencoes} linhas")
        
        print("-" * 35)
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao ler o banco: {e}")

if __name__ == "__main__":
    checar_status()