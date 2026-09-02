from docx import Document
import os
from automacoes.blocos.bloco_cabecalho import desenhar_cabecalho
from automacoes.blocos.bloco_atividades import desenhar_atividades
from automacoes.blocos.bloco_materiais import desenhar_materiais
from automacoes.blocos.bloco_horas import desenhar_service_log
from automacoes.blocos.bloco_assinaturas import desenhar_assinaturas
from automacoes.blocos.motor_fotos_locais import anexar_fotos_do_bloco

def montar_relatorio_word(pacote_cabecalho, pacote_servicos, pacote_atividades, pacote_materiais, pacote_horas_limpo, pacote_assinaturas, pacote_fotos ):
    print("Iniciando linha de montagem do Word...")
    
    # Pega o documento base (Template) ou cria um vazio se não achar
    caminho_template = "templates/template_relatorio.docx"
    doc = Document(caminho_template) if os.path.exists(caminho_template) else Document()
    
    # --- LINHA DE MONTAGEM ---
    doc = desenhar_cabecalho(doc, pacote_cabecalho, pacote_servicos)
    
    if pacote_atividades:
        doc = desenhar_atividades(doc, pacote_atividades)
        
    if pacote_materiais:
        doc = desenhar_materiais(doc, pacote_materiais)
        
    if pacote_horas_limpo:
        doc = desenhar_service_log(doc, pacote_horas_limpo)
        
    # ⬅️ Desenha o novo bloco de assinaturas no final do documento
    doc = desenhar_assinaturas(doc, pacote_assinaturas)

    doc = anexar_fotos_do_bloco(doc, pacote_fotos)
        
  # 1. Pega o nome do site. Se for vazio ("") ou não existir, força o nome "OLS"
    nome_site = pacote_cabecalho.get('Site', '')
    if not nome_site.strip():  
        nome_site = "OLS"
        
    # 2. Salva o arquivo final apontando para a pasta cache
    nome_base = f"Relatorio_{nome_site}.docx"
    caminho_salvo = f"../cache/{nome_base}" 
    
    doc.save(caminho_salvo)
    print(f"Documento {caminho_salvo} salvo com sucesso!")

    return caminho_salvo