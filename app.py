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
    
    with st.spinner("Executando pipeline ETL (Extração e Transformação)..."):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(_arquivo_pdf.getvalue())
                caminho_temporario = tmp.name

            # --- EXTRAÇÃO ---
            lista_tabelas = tabula.read_pdf(caminho_temporario, pages='1', stream=True)
            df_bruto = lista_tabelas[0]
            df_bruto = df_bruto.dropna(how='all')

            # --- TRANSFORMAÇÃO ---
            df_limpo = df_bruto.iloc[3:].copy()
            df_limpo.columns = [
                'item', 'nov_23', 'out_24', 'nov_24', 
                'var_percentual_mes', 'var_percentual_ano', 
                'acumulado_sujo', 'var_percentual_acumulado'
            ]

            if 'acumulado_sujo' in df_limpo.columns:
                df_limpo[['acumulado_2023', 'acumulado_2024']] = df_limpo['acumulado_sujo'].str.split(expand=True)
                df_limpo = df_limpo.drop(columns=['acumulado_sujo'])
            
            df_limpo = df_limpo.dropna(subset=['item'])
            os.unlink(caminho_temporario)

            # --- VISUALIZAÇÃO E EXPORTAÇÃO ---
            st.markdown("### 📊 Tabela Estruturada de Dados Fiscais")
            st.dataframe(df_limpo, use_container_width=True)

            dados_json = df_limpo.to_json(orient="records", force_ascii=False, indent=4)

            st.markdown("### 📥 Exportar Resultados")
            st.download_button(
                label="Clique aqui para baixar a tabela em JSON",
                data=dados_json,
                file_name=f"{_arquivo_pdf.name.replace('.pdf', '')}_estruturado.json",
                mime="application/json",
                type="primary"
            )

        except Exception as e:
            st.error(f"Erro ao processar o layout do PDF: {e}")
