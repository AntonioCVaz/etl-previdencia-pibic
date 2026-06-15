import streamlit as st
import PyPDF2
import google.generativeai as genai
import json
import pandas as pd

st.set_page_config(page_title="Pipeline ETL Previdência (Série Histórica)", layout="wide")

st.title("🏛️ Construtor de Série Histórica do RGPS")
st.markdown("Faça o upload de **vários** relatórios em PDF. A IA irá extrair o mês de referência de cada um e montar uma tabela consolidada no tempo, pareando as variáveis automaticamente.")

# --- CONFIGURAÇÃO E DESCOBERTA DINÂMICA DE MODELOS ---
modelo = None
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    modelos_disponiveis = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    modelos_flash = [m for m in modelos_disponiveis if 'flash' in m.lower()]
    
    if modelos_flash:
        modelo_escolhido = modelos_flash[0]
        # Forçando a IA a devolver sempre um JSON válido
        modelo = genai.GenerativeModel(
            modelo_escolhido,
            generation_config={"response_mime_type": "application/json"}
        )
        st.caption(f"🤖 IA conectada com sucesso ao modelo rápido: `{modelo_escolhido}`")
    else:
        st.error("Nenhum modelo da família 'Flash' compatível foi encontrado. Verifique sua chave.")
except Exception as e:
    st.error(f"Erro ao conectar com a API do Google: {e}")

# MUDANÇA 1: Permite selecionar múltiplos arquivos de uma vez
arquivos_pdf = st.file_uploader("Selecione os arquivos PDF (pode selecionar vários)", type=["pdf"], accept_multiple_files=True)

if arquivos_pdf and modelo:
    st.info(f"📁 {len(arquivos_pdf)} arquivo(s) na fila para processamento.")
    
    if st.button("🚀 Processar e Consolidar Série Histórica", type="primary"):
        
        # Este dicionário vai guardar os dados de todos os meses. Ex: {'dez/25': {'Var A': 10}, 'nov/25': {'Var A': 12, 'Var B': 5}}
        dados_consolidados = {}
        
        barra_progresso = st.progress(0)
        
        for i, arquivo in enumerate(arquivos_pdf):
            with st.spinner(f"Extraindo dados de: {arquivo.name}..."):
                try:
                    # Leitura do PDF
                    leitor_pdf = PyPDF2.PdfReader(arquivo)
                    texto_completo = ""
                    for pagina in leitor_pdf.pages:
                        texto_completo += pagina.extract_text() + "\n"

                    # MUDANÇA 2: Prompt focado em extrair apenas a coluna do mês de referência
                    prompt = f"""
                    Atue como um Engenheiro de Dados. Analise o texto do relatório do RGPS abaixo.
                    Encontre a tabela principal de "RESULTADO DO RGPS EM R$ MILHÕES NOMINAIS".
                    
                    Sua tarefa:
                    1. Identifique qual é o mês e ano de referência PRINCIPAL do relatório (ex: "dez/25", "nov/25"). Geralmente é a coluna de dados mais recente antes das colunas de variação (Var. %).
                    2. Extraia os nomes dos itens (primeira coluna) e APENAS os valores correspondentes a este mês de referência.
                    3. Retorne um JSON com duas chaves: "mes_referencia" (string) e "dados" (dicionário de chave-valor numérico).
                    
                    Exemplo do formato exigido:
                    {{
                        "mes_referencia": "dez/25",
                        "dados": {{
                            "1. Arrecadação Líquida Total": 92045.3,
                            "1.1 Arrecadação Líquida Urbana": 91080.7
                        }}
                    }}
                    
                    Texto do PDF:
                    {texto_completo}
                    """

                    resposta_ia = modelo.generate_content(prompt)
                    extracao = json.loads(resposta_ia.text.strip())
                    
                    mes = extracao.get("mes_referencia", f"Desconhecido_{i}")
                    valores = extracao.get("dados", {})
                    
                    # Guarda os valores daquele mês no dicionário mestre
                    dados_consolidados[mes] = valores

                except Exception as e:
                    st.error(f"Erro ao processar o arquivo {arquivo.name}: {e}")
            
            # Atualiza a barra de progresso
            barra_progresso.progress((i + 1) / len(arquivos_pdf))

        # MUDANÇA 3: Transforma os dados numa tabela pareada
        if dados_consolidados:
            st.success("✨ Processamento concluído com sucesso!")
            
            # O Pandas pega o dicionário e alinha todas as chaves perfeitamente. Onde não houver dado, ele põe NaN.
            df_historico = pd.DataFrame(dados_consolidados)
            
            st.markdown("### 📊 Série Histórica Consolidada")
            st.markdown("As colunas representam os meses e as linhas representam as variáveis. O sistema inseriu `NaN` automaticamente caso alguma variável não exista em um determinado mês.")
            st.dataframe(df_historico, use_container_width=True)

            # Exportação em CSV (Formato ideal para séries temporais e para importar no Excel/R/Python)
            csv = df_historico.to_csv()
            
            st.download_button(
                label="📥 Baixar Série Histórica em CSV",
                data=csv,
                file_name="rgps_serie_historica.csv",
                mime="text/csv",
                type="primary"
            )
