import json
from pathlib import Path

import pandas as pd
import streamlit as st

from core import llm
from core.extracao import extrair_texto
from core.plano_trabalho import analisar_plano
from ui import estado, guardar, listar_achados, placar, rodape

EX = Path(__file__).resolve().parent.parent / "data" / "exemplos"
s = estado()

st.title("1. Análise do Plano de Trabalho")
st.caption("Regras determinísticas (auditáveis) + camada opcional de IA para aspectos qualitativos.")

origem = st.radio("Origem do plano", ["Exemplo com problemas", "Exemplo adequado", "Enviar arquivo"],
                  horizontal=True)
plano, texto_livre = None, ""
if origem.startswith("Exemplo"):
    arq = "plano_trabalho_com_problemas.json" if "problemas" in origem else "plano_trabalho_adequado.json"
    plano = json.loads((EX / arq).read_text(encoding="utf-8"))
else:
    up = st.file_uploader("Plano de trabalho (JSON no padrão do app, PDF ou DOCX)",
                          type=["json", "pdf", "docx", "txt"])
    if up:
        dados = up.getvalue()
        if up.name.lower().endswith(".json"):
            plano = json.loads(dados.decode("utf-8"))
        else:
            texto_livre = extrair_texto(up.name, dados)
            st.text_area("Texto extraído", texto_livre[:5000], height=180)
            if llm.disponivel():
                if st.button("🤖 Estruturar com IA"):
                    with st.spinner("Estruturando o plano..."):
                        st.session_state["plano_estruturado"] = llm.estruturar_plano_ia(texto_livre)
                plano = st.session_state.get("plano_estruturado")
            else:
                st.info("Para PDF/DOCX livres, ative a IA para converter o texto em campos estruturados, "
                        "ou exporte o plano do Transferegov.br em formato estruturado.")

if plano:
    with st.expander("Ver dados do plano", expanded=False):
        st.json(plano)

    usar_ia = st.toggle("Incluir análise qualitativa por IA", value=False, disabled=not llm.disponivel(),
                        help="Requer chave de API ou modelo local configurado.")
    orient = ""
    if usar_ia:
        orient = st.text_area("Orientações internas do órgão para a IA (opcional)",
                              placeholder="Ex.: Para a subfunção 13.392, exigir contrapartida social ...")

    if st.button("Analisar", type="primary"):
        res = analisar_plano(plano)
        guardar(res)
        s["meta"] = {
            "proposta": plano.get("numero_proposta", "—"),
            "proponente": (plano.get("proponente") or {}).get("nome", "—"),
            "emenda": f"{(plano.get('emenda') or {}).get('numero', '—')} – "
                      f"{(plano.get('emenda') or {}).get('autor', '')}",
            "objeto": plano.get("objeto", "—"),
            "tipo_proponente": "osc" if "osc" in str((plano.get("proponente") or {}).get("tipo", "")).lower()
            else "ente_publico",
        }
        s["achados_ia"], s["sintese_ia"] = [], ""
        if usar_ia:
            with st.spinner("Consultando o modelo de linguagem..."):
                try:
                    s["achados_ia"], s["sintese_ia"] = llm.analisar_plano_ia(plano, orient)
                except Exception as exc:
                    st.error(f"Falha na IA (seguindo só com regras): {exc}")

    res = s["resultados"].get("Plano de Trabalho")
    if res:
        st.divider()
        placar(res)
        r = res.resumo
        st.dataframe(pd.DataFrame([
            {"Conferência": "Valor global", "Valor": r["valor_global"]},
            {"Conferência": "Soma das metas", "Valor": r["soma_metas"]},
            {"Conferência": "Soma do desembolso", "Valor": r["soma_desembolso"]},
            {"Conferência": "Soma do plano de aplicação", "Valor": r["soma_plano_aplicacao"]},
        ]), hide_index=True, column_config={"Valor": st.column_config.NumberColumn(format="R$ %.2f")})
        st.subheader("Apontamentos das regras")
        listar_achados(res.achados)
        if s["achados_ia"] or s["sintese_ia"]:
            st.subheader("🤖 Sugestões da IA (validar)")
            if s["sintese_ia"]:
                st.info(s["sintese_ia"])
            listar_achados(s["achados_ia"])
rodape()
