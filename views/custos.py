from pathlib import Path

import pandas as pd
import streamlit as st

from core.custos import analisar_custos
from ui import estado, guardar, listar_achados, placar, rodape

EX = Path(__file__).resolve().parent.parent / "data" / "exemplos"
s = estado()

st.title("3. Verificação de custos")
st.caption("Compara o orçamento da proposta com preços de referência (Painel de Preços, SINAPI, SICRO ou "
           "contratações anteriores do órgão).")

c1, c2 = st.columns(2)
up_orc = c1.file_uploader("Orçamento da proposta (CSV)", type=["csv"],
                          help="Colunas: item, descricao, unidade, quantidade, valor_unitario[, codigo_ref]")
up_ref = c2.file_uploader("Tabela de referência (CSV)", type=["csv"],
                          help="Colunas: codigo, descricao, unidade, preco_referencia[, fonte, data_base]")
orc = pd.read_csv(up_orc) if up_orc else pd.read_csv(EX / "orcamento_proposta.csv")
ref = pd.read_csv(up_ref) if up_ref else pd.read_csv(EX / "precos_referencia.csv")
if not up_orc or not up_ref:
    st.info("Usando arquivos de exemplo para o que não foi enviado.")

c3, c4 = st.columns(2)
limite = c3.slider("Tolerância acima da referência", 0, 100, 20, 5, format="%d%%") / 100
sim = c4.slider("Similaridade mínima para casar descrições", 0.3, 0.95, 0.6, 0.05)

if st.button("Verificar custos", type="primary"):
    guardar(analisar_custos(orc, ref, limite, sim))

res = s["resultados"].get("Verificação de Custos")
if res:
    st.divider()
    placar(res)
    m1, m2 = st.columns(2)
    m1.metric("Total proposto", f"R$ {res.resumo['total_proposto']:,.2f}")
    m2.metric("Excesso estimado sobre a referência", f"R$ {res.resumo['excesso_estimado']:,.2f}")
    st.dataframe(res.resumo["tabela"], hide_index=True, use_container_width=True, column_config={
        "Unitário proposto": st.column_config.NumberColumn(format="R$ %.2f"),
        "Total proposto": st.column_config.NumberColumn(format="R$ %.2f"),
        "Preço ref.": st.column_config.NumberColumn(format="R$ %.2f"),
        "Desvio": st.column_config.NumberColumn(format="percent"),
    })
    st.caption("Casamento por 'similaridade' é aproximado: confira se a especificação é equivalente. "
               "Em produção, recomenda-se casar por código CATMAT/CATSER ou SINAPI.")
    listar_achados(res.achados)
rodape()
