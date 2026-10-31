"""AnalisaEmendas – protótipo de IA para apoiar a análise de propostas
oriundas de emendas parlamentares (formalização e acompanhamento).
Interface no padrão visual do Design System gov.br.

Executar:  streamlit run app.py
"""
import streamlit as st

import ds_govbr as ds

st.set_page_config(page_title="AnalisaEmendas", page_icon="🏛️", layout="wide",
                   menu_items={"About": "AnalisaEmendas – protótipo aberto (MIT) de apoio à análise de emendas."})
ds.aplicar_tema()
ds.cabecalho()

paginas = st.navigation({
    "Início": [st.Page("views/inicio.py", title="Visão geral", icon=":material/home:", default=True)],
    "Destinação · piloto": [
        st.Page("views/banco_mapa.py", title="Mapa de lacunas", icon=":material/map:"),
        st.Page("views/banco_cadastro.py", title="Cadastro de projetos", icon=":material/add_box:"),
        st.Page("views/banco_curadoria.py", title="Curadoria do ministério", icon=":material/task_alt:"),
        st.Page("views/banco_vitrine.py", title="Vitrine para gabinetes", icon=":material/storefront:"),
        st.Page("views/banco_painel.py", title="Painel público", icon=":material/visibility:"),
    ],
    "Formalização": [
        st.Page("views/plano_trabalho.py", title="1. Plano de Trabalho", icon=":material/assignment:"),
        st.Page("views/documentos.py", title="2. Checklist documental", icon=":material/folder_open:"),
        st.Page("views/custos.py", title="3. Verificação de custos", icon=":material/payments:"),
        st.Page("views/assinatura.py", title="4. Assinatura digital", icon=":material/verified:"),
    ],
    "Acompanhamento": [
        st.Page("views/acompanhamento.py", title="5. Execução físico-financeira", icon=":material/monitoring:"),
    ],
    "Resultado": [
        st.Page("views/parecer.py", title="6. Parecer e auditoria", icon=":material/description:"),
        st.Page("views/fila.py", title="Fila de triagem (lote)", icon=":material/stacks:"),
    ],
    "Governança": [
        st.Page("views/qualidade.py", title="Qualidade das regras", icon=":material/fact_check:"),
        st.Page("views/sobre.py", title="Regras e parâmetros", icon=":material/rule:"),
    ],
}, expanded=True)
paginas.run()
