import streamlit as st
import google.generativeai as genai
import json
import pandas as pd

st.set_page_config(page_title="Pipeline ETL Previdência (Série Histórica)", layout="wide")

st.title("🏛️ Construtor de Série Histórica do RGPS")
st.markdown("Faça o upload de **vários** relatórios em PDF. A IA irá analisar visualmente cada documento, extrair a tabela com renúncias e montar uma tabela consolidada no tempo, pareando as variáveis automaticamente.")

# --- CONFIGURAÇÃO E DESCOBERTA DINÂMICA DE MODELOS ---
modelo = None
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    # Pergunta à API quais modelos estão disponíveis
    modelos_disponiveis = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    # Filtra EXCLUSIVAMENTE para a família 'flash', que possui cota gratuita de alto volume
    modelos_flash = [m for m in modelos_disponiveis if 'flash' in m.lower()]
    
    if modelos_flash:
        modelo_escolhido = modelos_flash[0]
        # Força a IA a devolver sempre o formato JSON matematicamente validado
        modelo = genai.GenerativeModel(
            modelo_escolhido,
            generation_config={"response_mime_type": "application/json"}
        )
        st.caption(f"🤖 IA conectada com sucesso ao modelo visual rápido: `{modelo_escolhido}`")
    else:
        st.error("Nenhum modelo da família 'Flash' compatível foi encontrado. Verifique sua chave.")
except Exception as e:
    st.error(f"Erro ao conectar com a API do Google: {e}")

# Upload múltiplo habilitado
arquivos_pdf = st.file_uploader("Selecione os arquivos PDF (pode selecionar vários simultaneamente)", type=["pdf"], accept_multiple_files=True)

if arquivos_pdf and modelo:
    st.info(f"📁 {len(arquivos_pdf)} arquivo(s) na fila para processamento.")
    
    if st.button("🚀 Processar e Consolidar Série Histórica", type="primary"):
        
        # Dicionário mestre que agrupará todos os meses
        dados_consolidados = {}
        barra_progresso = st.progress(0)
        
        for i, arquivo in enumerate(arquivos_pdf):
            with st.spinner(f"Analisando visualmente o layout de: {arquivo.name}..."):
                try:
                    # O documento é enviado em seu formato binário original para o "olho" da IA
                    documento_pdf = {
                        "mime_type": "application/pdf",
                        "data": arquivo.getvalue()
                    }

                    # Prompt multimodal focado na extração do quadro de Renúncias
                    prompt = """
                    Você é um Engenheiro de Dados com visão computacional avançada.
                    Analise este documento PDF de forma visual.
                    
                    ATENÇÃO VISUAL AO ALVO: 
                    Encontre a tabela que possui as exatas palavras "Com Renúncias LEI Nº 14.360/22" (geralmente dentro de um quadro no canto superior esquerdo da tabela) e o título "RESULTADO DO RGPS EM R$ MILHÕES NOMINAIS TOTAL".
                    
                    Sua tarefa:
                    1. Identifique qual é o mês e ano de referência PRINCIPAL desta tabela (ex: "dez/25"). É a coluna de dados que fica logo antes das colunas de "Var. %".
                    2. Extraia os itens da primeira coluna e os valores EXATOS correspondentes à coluna desse mês de referência.
                    3. Certifique-se de incluir os itens específicos desta tabela, como "2. Renúncias Previdenciárias", "2.1 Simples Nacional" e "4. Resultado do RGPS com Renúncias (1 + 2 - 3)".
                    4. Retorne APENAS um JSON estruturado com as chaves "mes_referencia" e "dados".
                    
                    Exemplo do formato exigido:
                    {
                        "mes_referencia": "dez/25",
                        "dados": {
                            "1. Arrecadação Líquida Total": 92045.3,
                            "1.1 Arrecadação Líquida Urbana": 91080.7,
                            "1.2 Arrecadação Líquida Rural": 948.7,
                            "1.3 Comprev": 15.8,
                            "2. Renúncias Previdenciárias": 6417.2,
                            "2.1 Simples Nacional": 1586.3,
                            "3. Despesa com Benefícios Previdenciários": 80928.8,
                            "4. Resultado do RGPS com Renúncias (1 + 2 - 3)": 17533.7
                        }
                    }
                    """

                    # Executa a chamada da API passando o texto e o arquivo PDF simultaneamente
                    resposta_ia = modelo.generate_content([prompt, documento_pdf])
                    extracao = json.loads(resposta_ia.text.strip())
                    
                    mes = extracao.get("mes_referencia", f"Desconhecido_{arquivo.name}")
                    valores = extracao.get("dados", {})
                    
                    dados_consolidados[mes] = valores

                except Exception as e:
                    st.error(f"Erro ao processar o arquivo {arquivo.name}. Detalhes: {e}")
            
            # Atualiza o carregamento na interface
            barra_progresso.progress((i + 1) / len(arquivos_pdf))

        # --- ETAPA DE CONSOLIDAÇÃO DOS DADOS ---
        if dados_consolidados:
            st.success("✨ Processamento concluído com sucesso!")
            
            # O Pandas cruza todas as variáveis e as empilha no tempo
            df_historico = pd.DataFrame(dados_consolidados)
            
            st.markdown("### 📊 Série Histórica Consolidada (Com Renúncias)")
            st.markdown("As colunas representam os meses. Caso uma rubrica financeira não exista em determinado mês, o valor foi preenchido com `NaN` de forma automática.")
            st.dataframe(df_historico, use_container_width=True)

            csv = df_historico.to_csv()
            
            st.download_button(
                label="📥 Baixar Série Histórica em CSV",
                data=csv,
                file_name="rgps_serie_historica_com_renuncias.csv",
                mime="text/csv",
                type="primary"
            )
