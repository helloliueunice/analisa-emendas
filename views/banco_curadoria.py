import json

import pandas as pd
import streamlit as st

import ds_govbr as ds
from banco_ui import aviso_piloto, banco, barra, legenda, tag_faixa
from core import banco as B
from core.auditoria import sha256
from ui import rodape

b = banco()
ds.titulo("Curadoria do ministério",
          "Certificação por checklist objetivo. O ministério certifica viabilidade; não recomenda destino nem "
          "parlamentar.", "Destinação", "Curadoria")
aviso_piloto()

fila = [p for p in b["projetos"] if p["status"] == "em_curadoria"]
c = st.columns(3)
c[0].metric("Na fila de curadoria", len(fila))
c[1].metric("Certificados", sum(p["status"] == "certificado" for p in b["projetos"]))
c[2].metric("Devolvidos para ajuste", sum(p["status"] == "devolvido" for p in b["projetos"]))

if not fila:
    ds.mensagem("success", "Fila vazia.")
    rodape()
    st.stop()

avals = [B.avaliar(b, p) for p in fila]
resumo = pd.DataFrame([{"id": a["projeto"]["id"], "Projeto": a["projeto"]["titulo"],
                        "Elegível": a["elegivel"], "Checklist completo": all(i["ok"] for i in a["checklist"]),
                        "Pode certificar": a["certificavel"]} for a in avals])
st.dataframe(resumo, hide_index=True, use_container_width=True)

pid = st.selectbox("Analisar projeto", [a["projeto"]["id"] for a in avals],
                   format_func=lambda k: f"{k} · " + next(a["projeto"]["titulo"] for a in avals
                                                          if a["projeto"]["id"] == k))
a = next(x for x in avals if x["projeto"]["id"] == pid)
p = a["projeto"]

st.markdown(f"### {p['titulo']}  \n{tag_faixa(a['faixa'], a['estavel'])}", unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Elegibilidade e linhas vermelhas** (regras determinísticas)")
    for i in a["elegibilidade"]:
        st.markdown(f"{'✅' if i['ok'] else '⛔'} {i['item']}" + ("" if i["ok"] else f"  \n<small>{i['motivo']}</small>"),
                    unsafe_allow_html=True)
with col2:
    st.markdown("**Checklist objetivo de certificação**")
    for i in a["checklist"]:
        st.markdown(f"{'✅' if i['ok'] else '❌'} {i['item']}")

st.markdown("**Composição da nota** (informativa; não decide a certificação)")
st.markdown(barra(a["componentes"]) + legenda(), unsafe_allow_html=True)
st.dataframe(pd.DataFrame([{"Critério": B.NOMES[k], "Valor (0–1)": a["componentes"][k][0],
                            "Base": a["componentes"][k][1]} for k in B.PESOS]),
             hide_index=True, use_container_width=True,
             column_config={"Valor (0–1)": st.column_config.NumberColumn(format="%.2f")})

ds.mensagem("info", "Proteção do servidor:",
            " a certificação atesta só os itens do checklist. Pelo art. 28 da LINDB, o agente responde apenas por "
            "dolo ou erro grosseiro; a certificação não garante o resultado da obra ou serviço.")
motivo = st.text_input("Motivo da devolução (obrigatório para devolver)")
b1, b2 = st.columns(2)
if b1.button("Certificar", type="primary", disabled=not a["certificavel"], use_container_width=True):
    p["status"] = "certificado"
    ev = B.registrar(b, "MinC (curadoria)", "certificou", pid,
                     {"checklist_sha256": sha256(json.dumps(a["checklist"], sort_keys=True))})
    p["historico"].append({"quando": ev["quando"], "quem": "MinC (curadoria)", "acao": "certificado"})
    st.rerun()
if b2.button("Devolver para ajuste", use_container_width=True, disabled=not motivo.strip()):
    p["status"] = "devolvido"
    B.registrar(b, "MinC (curadoria)", "devolveu", pid, {"motivo": motivo.strip()[:300]})
    st.rerun()
if not a["certificavel"]:
    st.caption("O botão Certificar só é liberado quando todos os itens de elegibilidade e do checklist estão atendidos.")
rodape()
