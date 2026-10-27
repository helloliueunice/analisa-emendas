import io
import json
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

import ds_govbr as ds
from core.acompanhamento import analisar_execucao
from core.auditoria import sha256
from core.formato import brl
from ui import moeda, estado, guardar, listar_achados, placar, rodape

EX = Path(__file__).resolve().parent.parent / "data" / "exemplos"
s = estado()

ds.titulo("5. Acompanhamento da execução",
          "Confronta pagamentos e execução física com o plano aprovado: o que foi pago, para quê, quando e "
          "quanto já foi entregue.", "Acompanhamento", "Execução físico-financeira")

fonte = st.radio("Plano de referência", ["Exemplo celebrado (EXEMPLO-001/2026)", "Plano analisado no módulo 1"],
                 horizontal=True, disabled=s.get("plano") is None)
if fonte.startswith("Plano analisado") and s.get("plano"):
    plano = s["plano"]
else:
    plano = json.loads((EX / "plano_trabalho_adequado.json").read_text(encoding="utf-8"))
st.caption(f"Plano: {plano.get('numero_proposta')} · {(plano.get('proponente') or {}).get('nome')} · "
           f"vigência {(plano.get('vigencia') or {}).get('inicio')} a {(plano.get('vigencia') or {}).get('fim')}")

c1, c2, c3 = st.columns(3)
up_pag = c1.file_uploader("Pagamentos / notas fiscais (CSV)", type=["csv"],
                          help="data, fornecedor_cnpj, fornecedor_nome, nf_numero, valor, meta")
up_fis = c2.file_uploader("Execução física (CSV)", type=["csv"], help="meta, quantidade_executada")
up_cred = c3.file_uploader("Créditos na conta (CSV, opcional)", type=["csv"], help="data, valor")
b_pag = up_pag.getvalue() if up_pag else (EX / "execucao_pagamentos.csv").read_bytes()
b_fis = up_fis.getvalue() if up_fis else (EX / "execucao_fisica.csv").read_bytes()
b_cred = up_cred.getvalue() if up_cred else (EX / "execucao_creditos.csv").read_bytes()
hoje = st.date_input("Data de referência da análise", value=date(2027, 12, 15), format="DD/MM/YYYY",
                     help="No exemplo, simula uma fiscalização após o fim da vigência.")

if st.button("Analisar execução", type="primary"):
    guardar(analisar_execucao(plano, pd.read_csv(io.BytesIO(b_pag)), pd.read_csv(io.BytesIO(b_fis)),
                              pd.read_csv(io.BytesIO(b_cred)), hoje=hoje))
    s["entradas"].update({"pagamentos": sha256(b_pag), "execucao_fisica": sha256(b_fis),
                          "creditos": sha256(b_cred)})

res = s["resultados"].get("Acompanhamento da Execução")
if res:
    st.divider()
    placar(res)
    m = st.columns(3)
    m[0].metric("Total pago", brl(res.resumo["total_pago"]))
    m[1].metric("Execução financeira", f"{res.resumo['perc_financeiro']:.0f}%")
    m[2].metric("Pagamentos analisados", res.resumo["n_pagamentos"])
    aba1, aba2 = st.tabs(["Físico × financeiro por meta", "Apontamentos"])
    with aba1:
        tab = res.resumo["tabela"]
        st.dataframe(tab, hide_index=True, use_container_width=True, column_config={
            "Previsto (R$)": moeda("Previsto (R$)"),
            "Gasto (R$)": moeda("Gasto (R$)"),
            "% financeiro": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f%%"),
            "% físico": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f%%"),
            "Descompasso (pp)": st.column_config.NumberColumn(format="%.0f pp"),
        })
        graf = tab.melt(id_vars="Descrição", value_vars=["% financeiro", "% físico"], var_name="Execução",
                        value_name="%")
        st.bar_chart(graf, x="Descrição", y="%", color="Execução", stack=False, horizontal=True, height=260)
    with aba2:
        listar_achados(res.achados)
rodape()
