"""Triagem em lote: analisa vários planos de uma vez e ordena por risco,
para o gestor distribuir a carga e priorizar o que precisa de olhar humano."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from core.modelos import Severidade
from core.plano_trabalho import analisar_plano
from ui import rodape

EX = Path(__file__).resolve().parent.parent / "data" / "exemplos"

st.title("Fila de triagem (lote)")
st.caption("Envie vários planos (JSON) para obter uma fila priorizada por risco.")

ups = st.file_uploader("Planos de trabalho (JSON)", type=["json"], accept_multiple_files=True)
planos = [(u.name, json.loads(u.getvalue().decode("utf-8"))) for u in ups or []]
if not planos:
    planos = [(p.name, json.loads(p.read_text(encoding="utf-8"))) for p in sorted(EX.glob("plano_*.json"))]
    st.info("Mostrando os planos de exemplo.")

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
    })
df = pd.DataFrame(linhas).sort_values(["Risco", "Valor global"], ascending=False)
c1, c2, c3 = st.columns(3)
c1.metric("Propostas", len(df))
c2.metric("Para diligência", int((df["Encaminhamento"] == "Diligência").sum()))
c3.metric("Valor total", f"R$ {df['Valor global'].sum():,.2f}")
st.dataframe(df, hide_index=True, use_container_width=True, column_config={
    "Valor global": st.column_config.NumberColumn(format="R$ %.2f"),
    "Risco": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
})
st.download_button("⬇️ Exportar fila (CSV)", df.to_csv(index=False).encode("utf-8-sig"), "fila_triagem.csv")
rodape()
