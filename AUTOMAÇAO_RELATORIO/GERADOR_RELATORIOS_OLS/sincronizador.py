import os
import time
import json
import shutil

# ==========================================
# 1. MAPEAMENTO DE PASTAS (O CAMINHO DA ENTREGA)
# ==========================================
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))

# Pasta local na máquina do técnico (Sala de Espera)
PASTA_ENVIAR_BD = os.path.join(DIRETORIO_ATUAL, '..', 'ENVIAR_BD')

# Caminho direto para a Caixa de Correio no Servidor (Onde a mágica acontece)
CAIXA_DE_CORREIO = r"C:\Users\joao\OneDrive\Desktop\OLS_servidor\CAIXA_DE_CORREIO"

# ==========================================
# 2. VERIFICAÇÃO DE CONEXÃO (A "VPN")
# ==========================================
def vpn_conectada():
    """
    Verifica se a pasta de destino no servidor está acessível.
    Se o Windows enxergar a pasta, significa que a rota (ou VPN) está ligada.
    """
    return os.path.exists(CAIXA_DE_CORREIO)

# ==========================================
# 3. O "PINGUIM ENTREGADOR" (PROCESSADOR DA FILA)
# ==========================================
def processar_fila():
    # Verifica se a pasta local existe
    if not os.path.exists(PASTA_ENVIAR_BD):
        return

    arquivos = os.listdir(PASTA_ENVIAR_BD)
    arquivos_json = [f for f in arquivos if f.endswith('.json')]

    if not arquivos_json:
        return # Nada para enviar na fila

    print(f"📦 Encontrados {len(arquivos_json)} relatórios na fila. Iniciando transferência...")

    for arquivo_json in arquivos_json:
        caminho_json_origem = os.path.join(PASTA_ENVIAR_BD, arquivo_json)
        
        try:
            # Lemos o JSON apenas para descobrir o nome exato do arquivo Word associado
            with open(caminho_json_origem, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            
            nome_docx = dados.get("nome_arquivo_word")
            caminho_docx_origem = os.path.join(PASTA_ENVIAR_BD, nome_docx)
            
            # Prepara os caminhos de destino lá no Servidor
            caminho_json_destino = os.path.join(CAIXA_DE_CORREIO, arquivo_json)
            caminho_docx_destino = os.path.join(CAIXA_DE_CORREIO, nome_docx)
            
            # 1. Transfere o arquivo Word (move e apaga da origem)
            if os.path.exists(caminho_docx_origem):
                shutil.move(caminho_docx_origem, caminho_docx_destino)
            
            # 2. Transfere o arquivo JSON (move e apaga da origem)
            shutil.move(caminho_json_origem, caminho_json_destino)
            
            print(f"✅ Pacote da OS {nome_docx} entregue com sucesso na Caixa de Correio!")

        except Exception as e:
            print(f"❌ Erro ao transferir o pacote {arquivo_json}: {e}")

# ==========================================
# 4. O LOOP ETERNO DO PINGUIM
# ==========================================
if __name__ == "__main__":
    print("🐧 Pinguim Entregador Iniciado. Aguardando relatórios offline...")
    while True:
        # Só tenta transferir se enxergar a Caixa de Correio do Servidor
        if vpn_conectada():
            processar_fila()
        
        # Dorme por 10 segundos antes de checar a rede e a fila de novo
        time.sleep(10)