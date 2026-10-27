import json
from pathlib import Path

import pandas as pd
import streamlit as st

import ds_govbr as ds
from core import llm
from core.auditoria import sha256
from core.extracao import extrair_texto
from core.plano_trabalho import analisar_plano
from ui import moeda, estado, guardar, listar_achados, placar, rodape

EX = Path(__file__).resolve().parent.parent / "data" / "exemplos"
s = estado()

ds.titulo("1. Análise do Plano de Trabalho",
          "Regras determinísticas e auditáveis, com camada opcional de IA para aspectos qualitativos.",
          "Formalização", "Plano de Trabalho")

origem = st.radio("Origem do plano", ["Exemplo com problemas", "Exemplo adequado", "Enviar arquivo"],
                  horizontal=True)
plano, bruto = None, b""
if origem.startswith("Exemplo"):
    arq = "plano_trabalho_com_problemas.json" if "problemas" in origem else "plano_trabalho_adequado.json"
    bruto = (EX / arq).read_bytes()
    plano = json.loads(bruto.decode("utf-8"))
else:
    up = st.file_uploader("Plano de trabalho (JSON no padrão do app, PDF ou DOCX)",
                          type=["json", "pdf", "docx", "txt"])
    if up:
        bruto = up.getvalue()
        if up.name.lower().endswith(".json"):
            plano = json.loads(bruto.decode("utf-8"))
        else:
            texto_livre = extrair_texto(up.name, bruto)
            st.text_area("Texto extraído", texto_livre[:5000], height=180)
            if llm.disponivel():
                if st.button("Estruturar com IA"):
                    with st.spinner("Estruturando o plano..."):
                        st.session_state["plano_estruturado"] = llm.estruturar_plano_ia(texto_livre)
                plano = st.session_state.get("plano_estruturado")
                if plano:
                    ds.mensagem("warning", "Campos extraídos por IA.",
                                " Confira os valores antes de analisar: erros de extração viram falsos apontamentos.")
            else:
                ds.mensagem("info", "PDF/DOCX livre requer a camada de IA para virar campos estruturados.",
                            " Alternativa: exportar o plano do Transferegov.br em formato estruturado.")

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
        s["plano"] = plano
        s["entradas"]["plano_de_trabalho"] = sha256(bruto or json.dumps(plano, sort_keys=True))
        prop = plano.get("proponente") or {}
        s["meta"] = {
            **s["meta"],
            "proposta": plano.get("numero_proposta", "—"),
            "proponente": prop.get("nome", "—"),
            "cnpj": prop.get("cnpj", ""),
            "emenda": f"{(plano.get('emenda') or {}).get('numero', '—')} – "
                      f"{(plano.get('emenda') or {}).get('autor', '')}",
            "objeto": plano.get("objeto", "—"),
            "tipo_proponente": "osc" if "osc" in str(prop.get("tipo", "")).lower() else "ente_publico",
        }
        s["achados_ia"], s["sintese_ia"] = [], ""
        if usar_ia:
            with st.spinner("Consultando o modelo de linguagem..."):
                try:
                    s["achados_ia"], s["sintese_ia"] = llm.analisar_plano_ia(plano, orient)
                except Exception as exc:
                    ds.mensagem("danger", "Falha na IA – seguindo só com as regras.", f" {exc}")

    res = s["resultados"].get("Plano de Trabalho")
    if res:
        st.divider()
        placar(res)
        r = res.resumo
        aba1, aba2 = st.tabs(["Apontamentos", "Conferência financeira"])
        with aba1:
            listar_achados(res.achados)
            if s["achados_ia"] or s["sintese_ia"]:
                st.subheader("Sugestões da IA (validar)")
                if s["sintese_ia"]:
                    ds.mensagem("info", "Síntese gerada por IA", " " + s["sintese_ia"])
                listar_achados(s["achados_ia"])
        with aba2:
            vg = r["valor_global"]
            st.dataframe(pd.DataFrame([
                {"Conferência": "Valor global (repasse + contrapartida)", "Valor": vg, "Fecha?": "—"},
                {"Conferência": "Soma das metas", "Valor": r["soma_metas"],
                 "Fecha?": "Sim" if abs(r["soma_metas"] - vg) < .01 else "Não"},
                {"Conferência": "Soma do desembolso", "Valor": r["soma_desembolso"],
                 "Fecha?": "Sim" if min(abs(r["soma_desembolso"] - vg),
                                        abs(r["soma_desembolso"] - r["valor_repasse"])) < .01 else "Não"},
                {"Conferência": "Soma do plano de aplicação", "Valor": r["soma_plano_aplicacao"],
                 "Fecha?": "Sim" if abs(r["soma_plano_aplicacao"] - vg) < .01 else "Não"},
            ]), hide_index=True, use_container_width=True,
                column_config={"Valor": moeda("Valor")})
rodape()
