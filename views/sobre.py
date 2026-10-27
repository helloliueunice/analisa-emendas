import ast
from pathlib import Path

import pandas as pd
import streamlit as st

import ds_govbr as ds
from core.config import hash_regras, parametros
from core.documentos import carregar_checklist
from ui import rodape

RAIZ = Path(__file__).resolve().parent.parent

ds.titulo("Regras e parâmetros",
          "Catálogo de todas as regras em uso, extraído do próprio código, e os parâmetros configuráveis.",
          "Governança", "Regras e parâmetros")


@st.cache_data
def catalogo():
    """Lê as chamadas Achado(MOD, "XX-NN Título", Severidade.X, ...) direto do código-fonte."""
    linhas = []
    for arq in sorted((RAIZ / "core").glob("*.py")):
        arvore = ast.parse(arq.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if isinstance(no, ast.Call) and getattr(no.func, "id", "") == "Achado" and len(no.args) >= 3:
                rg, sev = no.args[1], no.args[2]
                if isinstance(rg, ast.Constant) and isinstance(sev, ast.Attribute):
                    cod, _, tit = rg.value.partition(" ")
                    linhas.append({"Código": cod, "Regra": tit, "Severidade padrão": sev.attr.title(),
                                   "Módulo": arq.stem})
    return pd.DataFrame(linhas).drop_duplicates("Código").sort_values("Código")


cat = catalogo()
m = st.columns(3)
m[0].metric("Regras catalogadas", len(cat))
m[1].metric("Versão dos parâmetros", parametros().get("versao"))
m[2].metric("Hash das regras", hash_regras()[:10] + "…")
aba1, aba2, aba3 = st.tabs(["Catálogo de regras", "Parâmetros (config/parametros.yaml)", "Checklist documental"])
with aba1:
    st.dataframe(cat, hide_index=True, use_container_width=True, height=520)
with aba2:
    st.code((RAIZ / "config" / "parametros.yaml").read_text(encoding="utf-8"), language="yaml")
    ds.mensagem("info", "Governança:", " mudanças de parâmetro passam por revisão (pull request) e alteram o hash "
                "das regras, que fica registrado em cada parecer.")
with aba3:
    ck = carregar_checklist()
    st.dataframe(pd.DataFrame(ck["itens"])[["id", "nome", "aplica_a", "obrigatorio", "validade", "fundamento"]],
                 hide_index=True, use_container_width=True)
rodape()
