import re

import pandas as pd
import streamlit as st

import ds_govbr as ds
from banco_ui import aviso_piloto, banco, cartao, legenda
from core import banco as B
from core.parecer import gerar_docx
from ui import rodape

b = banco()
ds.titulo("Vitrine para gabinetes",
          "Projetos certificados, ordenados em faixas dentro de cada programa. A escolha é livre e fica registrada.",
          "Destinação", "Vitrine")
aviso_piloto()
ds.mensagem("info", "Como ler a vitrine.",
            " As faixas comparam projetos do mesmo programa e são informativas: não vinculam a escolha nem geram "
            "impedimento técnico. A plataforma não ranqueia parlamentares nem recomenda destinos.")

progs = b["programas"].set_index("id")["nome"].to_dict()
c1, c2, c3 = st.columns([2, 1.3, 1.3])
pid = c1.selectbox("Programa (obrigatório: não há comparação entre programas)", list(progs), format_func=progs.get)
faixas = c2.multiselect("Faixas", ["Alta", "Média", "Baixa"], default=["Alta", "Média", "Baixa"])
porte = c3.multiselect("Porte do município", ["Pequeno", "Médio", "Grande"], default=["Pequeno", "Médio", "Grande"])

certificados = [p for p in b["projetos"] if p["programa"] == pid and p["status"] == "certificado"]
avals = [B.avaliar(b, p) for p in certificados]


def porte_de(pop):
    return "Pequeno" if pop < 20000 else ("Médio" if pop < 100000 else "Grande")


avals = [a for a in avals if a["faixa"] in faixas and porte_de(a["municipio"]["populacao"]) in porte]
ordem = {"Alta": 0, "Média": 1, "Baixa": 2}
avals.sort(key=lambda a: (ordem[a["faixa"]], a["municipio"]["municipio"]))  # dentro da faixa: ordem alfabética

alertas = B.alertas(b)
alerta_mun = {}
for al in alertas:
    if al["tipo"].startswith("Concentração"):
        alerta_mun.setdefault(al["detalhe"].split(" recebeu")[0], []).append("concentração de emendas")

aba1, aba2 = st.tabs([f"Projetos certificados ({len(avals)})", "Robustez das faixas"])
with aba1:
    if not avals:
        ds.mensagem("info", "Nenhum projeto certificado com esses filtros.")
    st.markdown(legenda(), unsafe_allow_html=True)
    st.caption("Dentro de cada faixa a ordem é alfabética: posições finas seriam falsa precisão.")
    for a in avals:
        p = a["projeto"]
        st.markdown(cartao(a, alerta_mun.get(a["municipio"]["municipio"])), unsafe_allow_html=True)
        with st.expander(f"Detalhes e ações · {p['id']}"):
            st.dataframe(pd.DataFrame([{"Critério": B.NOMES[k], "Valor (0–1)": a["componentes"][k][0],
                                        "Base": a["componentes"][k][1]} for k in B.PESOS]),
                         hide_index=True, use_container_width=True,
                         column_config={"Valor (0–1)": st.column_config.NumberColumn(format="%.2f")})
            md = B.resumo_markdown(a)
            nome = re.sub(r"[^A-Za-z0-9]+", "_", p["id"])
            st.download_button("Baixar resumo de uma página (DOCX)", gerar_docx(md), f"resumo_{nome}.docx",
                               "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               key=f"dl_{p['id']}")
            if a["indicado"]:
                ds.mensagem("success", f"Já vinculado à emenda {a['indicado']}.")
            else:
                with st.form(f"ind_{p['id']}"):
                    st.markdown("**Registrar indicação** (a indicação oficial é feita no SIOP; aqui ela é vinculada "
                                "ao projeto e publicada)")
                    f1, f2 = st.columns(2)
                    emenda = f1.text_input("Número da emenda", placeholder="2027.0000.0000")
                    gab = f2.text_input("Gabinete", placeholder="Gabinete (fictício)")
                    if st.form_submit_button("Vincular emenda ao projeto", type="primary"):
                        if emenda.strip() and gab.strip():
                            b["indicacoes"].append({"emenda": emenda.strip(), "gabinete": gab.strip(),
                                                    "codigo_municipio": p["codigo_municipio"], "programa": pid,
                                                    "valor": p["custo"], "projeto_id": p["id"], "reconciliada": 1,
                                                    "situacao": "indicada"})
                            B.registrar(b, gab.strip(), "vinculou emenda", p["id"],
                                        {"emenda": emenda.strip(), "faixa_no_momento": a["faixa"]})
                            st.rerun()
                        else:
                            st.error("Informe o número da emenda e o gabinete.")

with aba2:
    st.markdown("Cada peso foi variado em ±0,05 (12 combinações). Se a faixa de um projeto muda em alguma delas, "
                "ele aparece como **sensível aos pesos** e a faixa deve ser lida com cautela.")
    todos = [B.avaliar(b, p) for p in b["projetos"] if p["programa"] == pid]
    rob = pd.DataFrame([{"Projeto": a["projeto"]["id"], "Município": a["municipio"]["municipio"],
                         "Faixa": a["faixa"], "Faixas possíveis": ", ".join(sorted(a["faixas_possiveis"])),
                         "Estável": a["estavel"]} for a in todos])
    if not rob.empty:
        st.metric("Projetos com faixa estável", f"{rob['Estável'].mean():.0%}")
        st.dataframe(rob, hide_index=True, use_container_width=True)
rodape()
