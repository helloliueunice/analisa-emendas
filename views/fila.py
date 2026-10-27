"""Triagem em lote: analisa vários planos de uma vez e ordena por risco,
para o gestor distribuir a carga e priorizar o que precisa de olhar humano."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

import ds_govbr as ds
from core.avaliacao import gerar_base
from core.formato import brl
from core.modelos import Severidade
from core.plano_trabalho import analisar_plano
from ui import moeda, rodape

EX = Path(__file__).resolve().parent.parent / "data" / "exemplos"

ds.titulo("Fila de triagem em lote",
          "Analisa várias propostas de uma vez e sugere o encaminhamento de cada uma, para priorizar a força "
          "de trabalho.", "Resultado", "Fila de triagem")

ups = st.file_uploader("Planos de trabalho (JSON)", type=["json"], accept_multiple_files=True)
planos = [(u.name, json.loads(u.getvalue().decode("utf-8"))) for u in ups or []]
if not planos:
    n = st.slider("Sem arquivos: simular uma carga de propostas sintéticas", 10, 300, 60, 10)
    planos = [(p.name, json.loads(p.read_text(encoding="utf-8"))) for p in sorted(EX.glob("plano_*.json"))]
    planos += [(c["plano"]["numero_proposta"], c["plano"]) for c in gerar_base(n, semente=7)]

linhas = []
for nome, p in planos:
    r = analisar_plano(p)
    crit = sum(a.severidade == Severidade.CRITICA for a in r.achados)
    alta = sum(a.severidade == Severidade.ALTA for a in r.achados)
    linhas.append({
        "Proposta": p.get("numero_proposta", nome),
        "Proponente": (p.get("proponente") or {}).get("nome", "—"),
        "Valor global": r.resumo["valor_global"],
        "Risco": r.nota_risco, "Críticos": crit, "Altos": alta,
        "Encaminhamento": "Diligência" if crit else ("Análise detalhada" if alta else "Análise simplificada"),
        "Principais pendências": "; ".join(a.regra for a in r.achados if a.severidade in
                                           (Severidade.CRITICA, Severidade.ALTA))[:120] or "—",
    })
df = pd.DataFrame(linhas).sort_values(["Risco", "Valor global"], ascending=False)
cont = df["Encaminhamento"].value_counts()
c = st.columns(4)
c[0].metric("Propostas", len(df))
c[1].metric("Diligência", int(cont.get("Diligência", 0)))
c[2].metric("Análise detalhada", int(cont.get("Análise detalhada", 0)))
c[3].metric("Análise simplificada", int(cont.get("Análise simplificada", 0)))
ds.mensagem("info", "Como usar:", f" {int(cont.get('Análise simplificada', 0))} proposta(s) sem pendência "
            "relevante podem seguir um rito simplificado, liberando analistas para os casos de maior risco. "
            f"Valor total na fila: {brl(df['Valor global'].sum())}.")
filtro = st.multiselect("Encaminhamento", list(cont.index), default=list(cont.index))
st.dataframe(df[df["Encaminhamento"].isin(filtro)], hide_index=True, use_container_width=True, height=420,
             column_config={"Valor global": moeda("Valor global"),
                            "Risco": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d")})
st.download_button("Exportar fila (CSV)", df.to_csv(index=False).encode("utf-8-sig"), "fila_triagem.csv")
rodape()
