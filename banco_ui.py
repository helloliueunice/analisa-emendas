"""Componentes de interface do Banco de Projetos de Impacto."""
from __future__ import annotations

import html

import streamlit as st

import ds_govbr as ds
from core import banco as B

# tons de UM azul, do mais escuro (maior peso) ao mais claro
CORES = {"N": "#071D41", "M": "#0C326F", "C": "#1351B4", "E": "#5992ED", "S": "#81AEFC", "A": "#ADCDFF"}
TAG_FAIXA = {"Alta": "faixa-alta", "Média": "faixa-media", "Baixa": "faixa-baixa"}


def banco() -> dict:
    if "banco" not in st.session_state:
        st.session_state["banco"] = B.estado_inicial()
    return st.session_state["banco"]


def aviso_piloto():
    ds.mensagem("warning", "Piloto com dados fictícios.",
                " “UF Piloto”, municípios, projetos, consultorias e emendas são inventados. As alterações ficam só "
                "nesta sessão do navegador. Em produção, os dados vêm do IBGE, CadÚnico, SICONFI, Transferegov e SIOP.")
    if st.sidebar.button("Restaurar dados de exemplo", use_container_width=True):
        st.session_state.pop("banco", None)
        st.rerun()


def tag_faixa(f: str, estavel: bool = True) -> str:
    t = ds.tag(f"Faixa {f}", TAG_FAIXA.get(f, "neutra"))
    if not estavel:
        t += ds.tag("sensível aos pesos", "neutra")
    return t


def barra(comp: dict) -> str:
    segs = "".join(
        f'<span title="{B.NOMES[k]}: {comp[k][0]:.2f} × peso {B.PESOS[k]:.2f}" '
        f'style="width:{B.PESOS[k] * comp[k][0] * 100:.1f}%;background:{CORES[k]}"></span>'
        for k in B.PESOS)
    return f'<div class="br-barra" role="img" aria-label="Composição da nota">{segs}</div>'


def legenda() -> str:
    return '<div class="br-legenda">' + "".join(
        f'<span><i style="background:{CORES[k]}"></i>{B.NOMES[k]} ({int(B.PESOS[k] * 100)}%)</span>'
        for k in B.PESOS) + "</div>"


def cartao(a: dict, alertas_mun: list[str] | None = None) -> str:
    p, m = a["projeto"], a["municipio"]
    e = html.escape
    tags = tag_faixa(a["faixa"], a["estavel"])
    if a["indicado"]:
        tags += ds.tag(f"Emenda {a['indicado']}", "ok")
    for al in alertas_mun or []:
        tags += ds.tag(al, "alta")
    porte = "pequeno" if m["populacao"] < 20000 else ("médio" if m["populacao"] < 100000 else "grande")
    valor = f"R$ {p['custo']:,.0f}".replace(",", ".")
    pop = f"{int(m['populacao']):,}".replace(",", ".")
    tipo = "modelo padronizado" if p.get("modelo_padrao") else "projeto próprio"
    return (f'<div class="br-projeto">{tags}<div class="titulo">{e(p["titulo"])}</div>'
            f'<div class="meta">{e(m["municipio"])} · município {porte} ({pop} hab.) · {valor} · {tipo} · '
            f'{e(p["id"])}</div>{barra(a["componentes"])}'
            f'<div class="porque">{e(a["explicacao"])}</div></div>')
