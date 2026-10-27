"""Componentes de interface compartilhados entre as páginas."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.modelos import Achado, ResultadoModulo, Severidade

COR = {Severidade.CRITICA: "🔴", Severidade.ALTA: "🟠", Severidade.MEDIA: "🟡", Severidade.INFO: "🔵"}


def estado():
    """Resultados ficam na sessão para alimentar o parecer consolidado."""
    st.session_state.setdefault("resultados", {})
    st.session_state.setdefault("achados_ia", [])
    st.session_state.setdefault("sintese_ia", "")
    st.session_state.setdefault("meta", {})
    return st.session_state


def guardar(resultado: ResultadoModulo):
    estado()["resultados"][resultado.modulo] = resultado


def placar(res: ResultadoModulo):
    cont = {s: sum(1 for a in res.achados if a.severidade == s) for s in Severidade}
    cols = st.columns(5)
    cols[0].metric("Índice de risco", f"{res.nota_risco}/100")
    for c, s in zip(cols[1:], Severidade):
        c.metric(f"{COR[s]} {s.value}", cont[s])


def listar_achados(achados: list[Achado], vazio: str = "Nenhum apontamento. ✅"):
    if not achados:
        st.success(vazio)
        return
    ordem = list(Severidade)
    for a in sorted(achados, key=lambda x: ordem.index(x.severidade)):
        tag = " · 🤖 sugerido por IA" if a.origem == "ia" else ""
        with st.expander(f"{COR[a.severidade]} **{a.regra}** — {a.mensagem}{tag}",
                         expanded=a.severidade == Severidade.CRITICA):
            if a.recomendacao:
                st.markdown(f"**Providência sugerida:** {a.recomendacao}")
            if a.fundamento:
                st.markdown(f"**Fundamento (conferir):** {a.fundamento}")
            if a.evidencia:
                st.caption(f"Evidência: {a.evidencia}")


def tabela_achados(achados: list[Achado]) -> pd.DataFrame:
    return pd.DataFrame([a.to_dict() for a in achados])


def rodape():
    st.divider()
    st.caption("Protótipo de apoio à decisão. As verificações não substituem a análise técnica e jurídica. "
               "Dados de exemplo são fictícios.")
