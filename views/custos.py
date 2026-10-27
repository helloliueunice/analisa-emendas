from pathlib import Path

import pandas as pd
import streamlit as st

import ds_govbr as ds
from core.auditoria import sha256
from core.config import p
from core.custos import analisar_custos
from core.formato import brl
from ui import moeda, estado, guardar, listar_achados, placar, rodape

EX = Path(__file__).resolve().parent.parent / "data" / "exemplos"
s = estado()

ds.titulo("3. Verificação de custos",
          "Compara o orçamento da proposta com preços de referência (Painel de Preços, SINAPI, SICRO ou "
          "contratações anteriores do órgão).", "Formalização", "Verificação de custos")

c1, c2 = st.columns(2)
up_orc = c1.file_uploader("Orçamento da proposta (CSV)", type=["csv"],
                          help="Colunas: item, descricao, unidade, quantidade, valor_unitario[, codigo_ref]")
up_ref = c2.file_uploader("Tabela de referência (CSV)", type=["csv"],
                          help="Colunas: codigo, descricao, unidade, preco_referencia[, fonte, data_base]")
b_orc = up_orc.getvalue() if up_orc else (EX / "orcamento_proposta.csv").read_bytes()
b_ref = up_ref.getvalue() if up_ref else (EX / "precos_referencia.csv").read_bytes()
import io  # noqa: E402

orc, ref = pd.read_csv(io.BytesIO(b_orc)), pd.read_csv(io.BytesIO(b_ref))
if not up_orc or not up_ref:
    ds.mensagem("info", "Usando arquivos de exemplo para o que não foi enviado.")

c3, c4, c5 = st.columns(3)
limite = c3.slider("Tolerância acima da referência", 0, 100, int(p("custos", "limite_sobrepreco", .2) * 100), 5,
                   format="%d%%") / 100
sim = c4.slider("Similaridade mínima de descrição", 0.3, 0.95, float(p("custos", "similaridade_minima", .6)), 0.05)
plano = s.get("plano")
valor_plano = c5.number_input("Valor do plano para conciliação (R$)", min_value=0.0, step=1000.0,
                              value=float(plano["valor_global"]) if plano else 0.0,
                              help="0 = não conciliar. Preenchido a partir do Plano de Trabalho analisado.")

if st.button("Verificar custos", type="primary"):
    guardar(analisar_custos(orc, ref, limite, sim, valor_plano or None))
    s["entradas"]["orcamento"] = sha256(b_orc)
    s["entradas"]["precos_referencia"] = sha256(b_ref)

res = s["resultados"].get("Verificação de Custos")
if res:
    st.divider()
    placar(res)
    m1, m2, m3 = st.columns(3)
    tab = res.resumo["tabela"]
    m1.metric("Total proposto", brl(res.resumo["total_proposto"]))
    m2.metric("Excesso estimado sobre a referência", brl(res.resumo["excesso_estimado"]))
    m3.metric("Itens com indício de sobrepreço", int((tab["Situação"] == "Indício de sobrepreço").sum()))
    aba1, aba2, aba3 = st.tabs(["Itens", "Desvio por item", "Apontamentos"])
    with aba1:
        st.dataframe(tab, hide_index=True, use_container_width=True, column_config={
            "Unitário proposto": moeda("Unitário proposto"),
            "Total proposto": moeda("Total proposto"),
            "Preço ref.": moeda("Preço ref."),
            "Desvio": st.column_config.NumberColumn(format="percent"),
        })
        ds.mensagem("warning", "Casamento por similaridade é aproximado.",
                    " Confira a equivalência da especificação. Em produção, case por código CATMAT/CATSER ou SINAPI.")
    with aba2:
        g = tab.dropna(subset=["Desvio"]).assign(**{"Desvio (%)": lambda d: d["Desvio"] * 100})
        st.bar_chart(g, x="Descrição", y="Desvio (%)", color="#1351B4", horizontal=True, height=360)
        st.caption(f"Linha de corte: {limite:.0%} acima da referência.")
    with aba3:
        listar_achados(res.achados)
rodape()
