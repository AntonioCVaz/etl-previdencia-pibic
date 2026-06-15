import streamlit as st
import PyPDF2
import google.generativeai as genai
import json

st.set_page_config(page_title="Pipeline ETL Previdência (IA)", layout="wide")

st.title("🏛️ Extrator de Tabelas com Deep Learning")
st.markdown("Faça o upload do relatório em PDF. A Inteligência Artificial irá extrair e estruturar os dados num formato JSON.")

# --- CONFIGURAÇÃO E DESCOBERTA DINÂMICA DE MODELOS ---
modelo = None
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    # Pergunta à API quais modelos estão disponíveis
    modelos_disponiveis = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    # Filtra EXCLUSIVAMENTE para a família 'flash', que possui cota gratuita de alto volume
    modelos_flash = [m for m in modelos_disponiveis if 'flash' in m.lower()]
    
    if modelos_flash:
        # Pega o primeiro modelo Flash disponível na lista
        modelo_escolhido = modelos_flash[0]
        modelo = genai.GenerativeModel(
        modelo_escolhido,
        generation_config={"response_mime_type": "application/json"}
        )
        st.caption(f"🤖 IA conectada com sucesso ao modelo leve: `{modelo_escolhido}`")
    else:
        st.error("Nenhum modelo da família 'Flash' compatível foi encontrado. Verifique sua chave.")
except Exception as e:
    st.error(f"Erro ao conectar com a API do Google: {e}")

arquivo_pdf = st.file_uploader("Selecione o arquivo PDF governamental", type=["pdf"])

if arquivo_pdf and modelo:
    st.success(f"Arquivo '{arquivo_pdf.name}' carregado com sucesso!")
    
    with st.spinner("A IA está processando e estruturando os dados. Por favor, aguarde..."):
        try:
            # --- 1. EXTRAÇÃO BRUTA ---
            leitor_pdf = PyPDF2.PdfReader(arquivo_pdf)
            texto_completo = ""
            for pagina in leitor_pdf.pages:
                texto_completo += pagina.extract_text() + "\n"

            # --- 2. TRANSFORMAÇÃO VIA LLM ---
            prompt = f"""
            Atue como um Engenheiro de Dados especialista em processamento de dados fiscais.
            Analise o texto abaixo, extraído de um relatório governamental.
            Identifique todas as tabelas de dados presentes e estruture-as.
            
            Regras rigorosas:
            1. Devolva EXCLUSIVAMENTE um arquivo JSON válido.
            2. Não inclua texto explicativo antes nem depois.
            3. Não inclua formatação markdown como ```json. Apenas as chaves e valores.
            4. Estruture de forma que cada página ou seção identificada seja uma chave no dicionário JSON principal.
            
            Texto do PDF:
            {texto_completo}
            """

            resposta_ia = modelo.generate_content(prompt)
            
            # Limpeza preventiva caso a IA adicione formatação markdown
            texto_limpo = resposta_ia.text.strip()
            if texto_limpo.startswith("```json"):
                texto_limpo = texto_limpo[7:]
            if texto_limpo.endswith("```"):
                texto_limpo = texto_limpo[:-3]
                
            dados_json = json.loads(texto_limpo.strip())
            json_formatado = json.dumps(dados_json, ensure_ascii=False, indent=4)

            # --- 3. EXIBIÇÃO E EXPORTAÇÃO ---
            st.markdown("### 📊 Dados Estruturados pela IA")
            st.json(dados_json)

            st.markdown("### 📥 Exportar Resultados")
            st.download_button(
                label="Clique aqui para baixar o arquivo JSON",
                data=json_formatado,
                file_name=f"{arquivo_pdf.name.replace('.pdf', '')}_ia_estruturado.json",
                mime="application/json",
                type="primary"
            )

        except json.JSONDecodeError:
            st.error("A IA não conseguiu formatar os dados perfeitamente em JSON. Tente enviar novamente.")
            with st.expander("Ver a resposta bruta do modelo para depuração"):
                st.write(resposta_ia.text)
        except Exception as e:
            st.error(f"Ocorreu um erro no processamento: {e}")
