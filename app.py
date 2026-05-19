import streamlit as st
import pandas as pd
import tabula
import tempfile
import os

st.set_page_config(page_title="Pipeline ETL Previdência", layout="wide")

st.title("🏛️ Extrator de Tabelas da Previdência Social")
st.markdown("Faça o upload do relatório em PDF para extrair, estruturar e baixar os dados em formato JSON.")

arquivo_pdf = st.file_uploader("Selecione o arquivo PDF governamental", type=["pdf"])

if _arquivo_pdf := arquivo_pdf:
    st.success(f"Arquivo '{_arquivo_pdf.name}' carregado com sucesso!")
    
    with st.spinner("Executando pipeline ETL..."):
        try:
            # PREPARAÇÃO DO ARQUIVO
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(_arquivo_pdf.getvalue())
                caminho_temporario = tmp.name

            # EXTRAÇÃO
            lista_tabelas = tabula.read_pdf(caminho_temporario, pages='all', stream=True)
            tabelas_limpas = []

            # TRANSFORMAÇÃO
            for df_bruto in lista_tabelas:
                df_limpo = df_bruto.dropna(how='all', axis=0).dropna(how='all', axis=1)
                
                if not df_limpo.empty:
                    df_limpo.columns = [str(col).strip().replace('\r', ' ').replace('\n', ' ') for col in df_limpo.columns]
                    tabelas_limpas.append(df_limpo)

            os.unlink(caminho_temporario)

            # CONCATENAÇÃO E CARGA (EXPORTAÇÃO)
            if tabelas_limpas:
                df_final = pd.concat(tabelas_limpas, ignore_index=True)
                
                st.markdown("### 📊 Tabela Extraída")
                st.dataframe(df_final, use_container_width=True)

                dados_json = df_final.to_json(orient="records", force_ascii=False, indent=4)

                st.markdown("### 📥 Exportar Resultados")
                st.download_button(
                    label="Clique aqui para baixar a tabela em JSON",
                    data=dados_json,
                    file_name=f"{_arquivo_pdf.name.replace('.pdf', '')}_estruturado.json",
                    mime="application/json",
                    type="primary"
                )
            else:
                st.warning("Não foi possível extrair nenhuma tabela válida deste arquivo PDF.")

        except Exception as e:
            st.error(f"Erro ao processar o arquivo PDF: {e}")
