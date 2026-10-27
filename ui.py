"""Componentes de interface compartilhados entre as páginas (padrão gov.br)."""
from __future__ import annotations

import html

import pandas as pd
import streamlit as st

import ds_govbr as ds
from core.modelos import Achado, ResultadoModulo, Severidade

CLASSE = {Severidade.CRITICA: "critica", Severidade.ALTA: "alta", Severidade.MEDIA: "media",
          Severidade.INFO: "info"}
BORDA = {Severidade.CRITICA: "#E52207", Severidade.ALTA: "#C05600", Severidade.MEDIA: "#FFCD07",
         Severidade.INFO: "#1351B4"}


def estado():
    """Resultados ficam na sessão para alimentar o parecer consolidado."""
    st.session_state.setdefault("resultados", {})
    st.session_state.setdefault("achados_ia", [])
    st.session_state.setdefault("sintese_ia", "")
    st.session_state.setdefault("meta", {})
    st.session_state.setdefault("entradas", {})   # hashes para trilha de auditoria
    st.session_state.setdefault("plano", None)
    return st.session_state


def guardar(resultado: ResultadoModulo):
    estado()["resultados"][resultado.modulo] = resultado


def placar(res: ResultadoModulo):
    cont = {s: sum(1 for a in res.achados if a.severidade == s) for s in Severidade}
    cols = st.columns(5)
    cols[0].metric("Índice de risco (0–100)", res.nota_risco)
    for c, s in zip(cols[1:], Severidade):
        c.metric(s.value, cont[s])
    if res.tem_impeditivo:
        ds.mensagem("danger", "Há pendências impeditivas.",
                    " A proposta não deve seguir sem diligência ao proponente.")
    elif any(a.severidade == Severidade.ALTA for a in res.achados):
        ds.mensagem("warning", "Há pendências relevantes.", " Recomenda-se diligência antes da aprovação.")
    else:
        ds.mensagem("success", "Sem pendências relevantes nas verificações automatizadas.",
                    " Prossiga com a análise técnica de mérito.")


def _item(a: Achado) -> str:
    e = html.escape
    tags = ds.tag(a.severidade.value, CLASSE[a.severidade])
    if a.origem == "ia":
        tags += ds.tag("Sugerido por IA – validar", "ia")
    corpo = f"<div style='margin:6px 0 4px 0;font-size:15.5px'>{e(a.mensagem)}</div>"
    if a.recomendacao:
        corpo += f"<div style='font-size:14px'><b>Providência:</b> {e(a.recomendacao)}</div>"
    if a.fundamento:
        corpo += f"<div style='font-size:13.5px;color:#636363'><b>Fundamento a conferir:</b> {e(a.fundamento)}</div>"
    if a.evidencia:
        corpo += f"<div style='font-size:13px;color:#636363'><b>Evidência:</b> {e(a.evidencia)}</div>"
    return (f"<div style='background:#fff;border:1px solid #e6e6e6;border-left:6px solid {BORDA[a.severidade]};"
            f"border-radius:4px;padding:12px 16px;margin:8px 0'>{tags}"
            f"<span style='font-weight:700;color:#071d41'>{e(a.regra)}</span>"
            f"<span style='float:right;font-size:12px;color:#888'>{e(a.modulo)}</span>{corpo}</div>")


def listar_achados(achados: list[Achado], vazio: str = "Nenhum apontamento."):
    if not achados:
        ds.mensagem("success", vazio)
        return
    ordem = list(Severidade)
    filtro = st.pills("Filtrar por severidade", [s.value for s in Severidade], selection_mode="multi",
                      default=[s.value for s in Severidade], key=f"filtro_{id(achados)}_{len(achados)}")
    itens = [a for a in sorted(achados, key=lambda x: ordem.index(x.severidade))
             if a.severidade.value in (filtro or [])]
    st.markdown("".join(_item(a) for a in itens), unsafe_allow_html=True)


def moeda(rotulo: str):
    """Coluna monetária com separadores no padrão do navegador (pt-BR: 1.234,56)."""
    return st.column_config.NumberColumn(f"{rotulo} (R$)" if "R$" not in rotulo else rotulo, format="localized")


def tabela_achados(achados: list[Achado]) -> pd.DataFrame:
    return pd.DataFrame([a.to_dict() for a in achados])


def rodape():
    ds.rodape()
