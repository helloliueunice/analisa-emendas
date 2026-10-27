"""AnalisaEmendas – protótipo de IA para apoiar a análise de propostas
oriundas de emendas parlamentares (formalização e acompanhamento).

Executar:  streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="AnalisaEmendas", page_icon="🏛️", layout="wide")

paginas = st.navigation({
    "Início": [st.Page("views/inicio.py", title="Visão geral", icon=":material/home:", default=True)],
    "Análise da proposta": [
        st.Page("views/plano_trabalho.py", title="1. Plano de Trabalho", icon=":material/assignment:"),
        st.Page("views/documentos.py", title="2. Checklist documental", icon=":material/folder_open:"),
        st.Page("views/custos.py", title="3. Verificação de custos", icon=":material/payments:"),
        st.Page("views/assinatura.py", title="4. Assinatura digital", icon=":material/verified:"),
    ],
    "Resultado": [
        st.Page("views/parecer.py", title="5. Minuta de parecer", icon=":material/description:"),
        st.Page("views/fila.py", title="Fila de triagem (lote)", icon=":material/stacks:"),
    ],
})
paginas.run()
