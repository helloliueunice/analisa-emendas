import altair as alt
import streamlit as st

import ds_govbr as ds
from banco_ui import aviso_piloto, banco
from core import banco as B
from ui import rodape

b = banco()
ds.titulo("Mapa de lacunas",
          "Onde falta o equipamento de cada programa, e onde já existe projeto para supri-lo.",
          "Destinação", "Mapa de lacunas")
aviso_piloto()

progs = b["programas"].set_index("id")["nome"].to_dict()
pid = st.radio("Programa", list(progs), format_func=lambda k: progs[k], horizontal=True)
df = B.mapa_lacunas(b, pid)
sem = df[df["lacuna"] == "Sem o equipamento"]
sem_proj = sem[~sem["tem_projeto"]]

c = st.columns(4)
c[0].metric("Municípios na UF", len(df))
c[1].metric("Sem o equipamento", len(sem))
c[2].metric("Lacunas já com projeto", int(sem["tem_projeto"].sum()))
c[3].metric("Lacunas sem projeto", len(sem_proj))

df["Situação"] = df.apply(lambda r: "Sem equipamento, com projeto" if r["lacuna"] == "Sem o equipamento"
                          and r["tem_projeto"] else ("Sem equipamento, sem projeto"
                                                     if r["lacuna"] == "Sem o equipamento" else "Já tem"), axis=1)
cores = alt.Scale(domain=["Sem equipamento, sem projeto", "Sem equipamento, com projeto", "Já tem"],
                  range=["#1351B4", "#81AEFC", "#CCCCCC"])
graf = alt.Chart(df).mark_circle(opacity=0.9, stroke="#ffffff", strokeWidth=1).encode(
    x=alt.X("lon:Q", axis=None, scale=alt.Scale(zero=False)),
    y=alt.Y("lat:Q", axis=None, scale=alt.Scale(zero=False)),
    size=alt.Size("populacao:Q", scale=alt.Scale(range=[60, 1600]), legend=None),
    color=alt.Color("Situação:N", scale=cores, legend=alt.Legend(orient="bottom", title=None, labelLimit=320, labelFontSize=13)),
    tooltip=[alt.Tooltip("municipio:N", title="Município"),
             alt.Tooltip("populacao:Q", title="População", format=",.0f"),
             alt.Tooltip("pct_pobreza_cadunico:Q", title="% pobreza (CadÚnico)"),
             alt.Tooltip("Situação:N"), alt.Tooltip("necessidade:Q", title="Necessidade (0–1)", format=".2f")],
).properties(height=440, title=f"{len(sem_proj)} municípios sem {progs[pid].split(' –')[0].lower()} e sem projeto")
st.altair_chart(graf, use_container_width=True)
st.caption("Mapa esquemático (posições fictícias, sem fundo cartográfico). Tamanho do círculo = população.")

st.subheader("Lacunas sem projeto: onde a assistência técnica rende mais")
ds.mensagem("info", "Para que serve esta lista:",
            " municípios que precisam do equipamento mas não apresentaram projeto costumam ser os de menor "
            "capacidade técnica. É aqui que projetos-padrão e apoio de consórcios evitam que o banco reproduza a "
            "desigualdade.")
st.dataframe(sem_proj.sort_values("necessidade", ascending=False)[
    ["municipio", "populacao", "porte", "pct_pobreza_cadunico", "plano_municipal_cultura", "necessidade"]],
    hide_index=True, use_container_width=True, column_config={
        "municipio": "Município", "populacao": st.column_config.NumberColumn("População", format="localized"),
        "porte": "Porte", "pct_pobreza_cadunico": st.column_config.NumberColumn("% pobreza", format="%.0f%%"),
        "plano_municipal_cultura": st.column_config.CheckboxColumn("Plano de cultura"),
        "necessidade": st.column_config.ProgressColumn("Necessidade", min_value=0, max_value=1, format="%.2f")})
st.caption("Necessidade = 70% ausência do equipamento (MUNIC/IBGE, autodeclarada) + 30% pobreza (CadÚnico).")
rodape()
