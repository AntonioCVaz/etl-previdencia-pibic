import streamlit as st
import PyPDF2
import google.generativeai as genai
import json

st.set_page_config(page_title="Pipeline ETL Previdência (IA)", layout="wide")

st.title("🏛️ Extrator de Tabelas com Deep Learning")
st.markdown("Faça o upload do relatório em PDF. A Inteligência Artificial irá extrair e estruturar os dados num formato JSON.")

# Ligação ao modelo LLM usando o cofre seguro do Streamlit
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # O modelo 1.5 Flash é ideal e muito rápido para tarefas de extração
    modelo = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error("Aviso: Chave da API do Gemini não foi encontrada nas definições (Secrets) do Streamlit.")

arquivo_pdf = st.file_uploader("Selecione o ficheiro PDF governamental", type=["pdf"])

if arquivo_pdf:
    st.success(f"Ficheiro '{arquivo_pdf.name}' carregado com sucesso!")
    
    with st.spinner("O LLM está a processar a matriz de dados. Por favor, aguarde..."):
        try:
            # --- 1. EXTRAÇÃO BRUTA ---
            leitor_pdf = PyPDF2.PdfReader(arquivo_pdf)
            texto_completo = ""
            for pagina in leitor_pdf.pages:
                texto_completo += pagina.extract_text() + "\n"

            # --- 2. TRANSFORMAÇÃO VIA LLM ---
            # Prompt de engenharia meticuloso para garantir apenas o retorno do JSON
            prompt = f"""
            Atue como um Engenheiro de Dados especialista em processamento de dados fiscais.
            Analise o texto abaixo, extraído de um relatório governamental.
            Identifique todas as tabelas de dados presentes e estruture-as.
            
            Regras rigorosas:
            1. Devolva EXCLUSIVAMENTE um ficheiro JSON válido.
            2. Não inclua texto explicativo antes nem depois.
            3. Não inclua formatação markdown como ```json. Apenas as chaves e valores.
            4. Estruture de forma que cada página ou secção identificada seja uma chave no dicionário JSON principal.
            
            Texto do PDF:
            {texto_completo}
            """

            resposta_ia = modelo.generate_content(prompt)
            
            # Limpeza preventiva caso o LLM insira formatações de bloco de código
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
                label="Clique aqui para descarregar o ficheiro JSON",
                data=json_formatado,
                file_name=f"{arquivo_pdf.name.replace('.pdf', '')}_ia_estruturado.json",
                mime="application/json",
                type="primary"
            )

        except json.JSONDecodeError:
            st.error("O modelo não conseguiu formatar os dados perfeitamente. Por favor, tente submeter o ficheiro novamente.")
            with st.expander("Ver a resposta em bruto (Raw) do modelo para depuração"):
                st.write(resposta_ia.text)
        except Exception as e:
            st.error(f"Ocorreu um erro no processamento: {e}")
