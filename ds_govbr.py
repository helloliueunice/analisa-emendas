"""Camada de Design System gov.br para Streamlit.

Usa os *tokens oficiais* do pacote @govbr-ds/core 3.7 (MIT, vendorizado em
assets/govbr-ds/core-tokens.min.css) e reproduz, em CSS sobre os componentes
do Streamlit, os padrões visuais do DS: tipografia Rawline, cabeçalho com
sombra, botões "pill" de 40 px, br-card, br-message, br-tag, foco acessível
(--focus, dourado), breadcrumb e rodapé escuro.

Observação: o app é um PROTÓTIPO. Por isso não exibe a marca/logotipo gov.br
nem a barra de identidade do governo, reservadas a serviços oficiais.
"""
from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

TOKENS = Path(__file__).resolve().parent / "assets" / "govbr-ds" / "core-tokens.min.css"

IMPORTS = ""  # fonte Rawline servida localmente (static/fonts) – sem dependência de CDN

CSS = r"""

:root{
  --ds-font: Rawline, Raleway, sans-serif;
  --ds-primary: var(--blue-warm-vivid-70, #1351b4);
  --ds-primary-dark: var(--blue-warm-vivid-90, #071d41);
  --ds-primary-hover: var(--blue-warm-vivid-60, #155bcb);
  --ds-focus: var(--gold-vivid-40, #c2850c);
}

/* ---------- tipografia ---------- */
html, body, h1, h2, h3, h4, h5, h6, [class*="st-"], .stMarkdown, [data-testid="stHeading"] *, .stText, button, input, textarea, select,
[data-testid="stSidebarNav"] *, [data-testid="stMetric"] *{
  font-family: var(--ds-font) !important;
}
[data-testid="stIconMaterial"], .material-symbols-rounded, span[data-testid="stIconMaterial"]{
  font-family: "Material Symbols Rounded" !important;
}
h1{ font-weight:300 !important; color:var(--gray-80,#333) !important; font-size:2.4rem !important; }
h2{ font-weight:500 !important; color:var(--gray-80,#333) !important; }
h3{ font-weight:600 !important; color:var(--gray-80,#333) !important; }
p, li{ line-height:1.6; }

@media (max-width: 640px){ h1{ font-size:1.75rem !important; } .br-header-ds{ padding:12px 14px; } }

/* ---------- layout ---------- */
[data-testid="stHeader"]{ background:transparent; }
.block-container{ padding-top:1.2rem !important; max-width:1240px; }
[data-testid="stSidebar"]{ border-right:1px solid var(--gray-10,#e6e6e6); }
[data-testid="stSidebarNav"] a[aria-current="page"]{
  background:var(--blue-warm-vivid-5,#edf5ff) !important; border-left:4px solid var(--ds-primary);
}
[data-testid="stSidebarNav"] a[aria-current="page"] span{ color:var(--ds-primary) !important; font-weight:600; }

/* ---------- br-header ---------- */
.br-header-ds{
  display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap;
  background:#fff; padding:14px 24px; margin:0 0 8px 0; border-radius:4px;
  box-shadow:0 3px 6px rgba(0,0,0,.16);
}
.br-header-ds .marca{ display:flex; align-items:center; gap:14px; }
.br-header-ds .sigla{
  width:44px; height:44px; border-radius:8px; background:var(--ds-primary); color:#fff;
  display:flex; align-items:center; justify-content:center; font-weight:800; font-size:18px;
}
.br-header-ds .divisor{ width:1px; height:36px; background:var(--gray-20,#ccc); }
.br-header-ds .titulo{ font-size:20px; font-weight:500; color:var(--gray-80,#333); line-height:1.2; }
.br-header-ds .subtitulo{ font-size:13px; color:var(--gray-60,#636363); }
.br-header-ds .acoes{ display:flex; gap:8px; align-items:center; }

/* ---------- breadcrumb ---------- */
.br-breadcrumb-ds{ font-size:14px; color:var(--gray-60,#636363); margin:6px 0 10px 2px; }
.br-breadcrumb-ds a{ color:var(--ds-primary); text-decoration:none; }
.br-breadcrumb-ds .sep{ margin:0 8px; color:var(--gray-40,#888); }

/* ---------- br-button ---------- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button{
  min-height:40px; border-radius:100em !important; font-weight:600 !important; font-size:16.8px !important;
  padding:0 24px !important; border:1px solid var(--ds-primary) !important; color:var(--ds-primary) !important;
  background:#fff !important; transition:background .15s;
}
.stButton > button:hover, .stDownloadButton > button:hover{
  background:var(--blue-warm-vivid-5,#edf5ff) !important;
}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"]{
  background:var(--ds-primary) !important; color:#fff !important;
}
.stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover{
  background:var(--ds-primary-hover) !important;
}
.stButton > button p, .stDownloadButton > button p{ font-weight:600 !important; }
.stButton > button:disabled, .stButton > button[disabled]{ opacity:.45 !important; cursor:not-allowed !important; }

/* foco visível (acessibilidade – eMAG/WCAG 2.4.7) */
*:focus-visible, button:focus-visible, input:focus-visible, textarea:focus-visible, a:focus-visible{
  outline:4px dashed var(--ds-focus) !important; outline-offset:4px !important;
}

/* ---------- inputs ---------- */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"]{
  border-radius:6px !important;
}
label, [data-testid="stWidgetLabel"] p{ font-weight:600 !important; color:var(--gray-80,#333) !important; }

/* ---------- br-card ---------- */
.br-card-ds{
  background:#fff; border-radius:8px; padding:20px; height:100%;
  box-shadow:0 1px 6px rgba(0,0,0,.16); border-top:4px solid var(--ds-primary);
  min-height:190px; margin-bottom:12px;
}
.br-card-ds .card-titulo{ font-weight:700; font-size:17px; color:var(--ds-primary-dark); margin-bottom:6px; }
.br-card-ds .card-texto{ font-size:14.5px; color:var(--gray-80,#333); line-height:1.5; }
.br-card-ds .card-icone{ font-size:26px; margin-bottom:8px; }

/* métricas como cartões */
[data-testid="stMetric"]{
  background:#fff; border-radius:8px; padding:14px 16px; box-shadow:0 1px 6px rgba(0,0,0,.16);
}
[data-testid="stMetricLabel"] p{ font-size:13px !important; color:var(--gray-60,#636363) !important; font-weight:600 !important; }
[data-testid="stMetricValue"]{ color:var(--ds-primary-dark) !important; font-weight:600 !important; font-size:1.9rem !important; }
[data-testid="stMetricValue"] > div{ overflow:visible !important; text-overflow:clip !important; }

/* ---------- br-message ---------- */
.br-message-ds{
  display:flex; gap:14px; align-items:flex-start; border-radius:4px; padding:14px 18px; margin:10px 0;
  border-left:8px solid; font-size:15px; line-height:1.5;
}
.br-message-ds .icone{ font-size:20px; line-height:1.2; }
.br-message-ds strong{ display:block; margin-bottom:2px; }
.br-message-ds.info{ background:var(--blue-warm-vivid-10,#d4e5ff); border-color:var(--blue-warm-vivid-60,#155bcb); color:#071d41; }
.br-message-ds.success{ background:var(--green-cool-vivid-5,#e3f5e1); border-color:var(--green-cool-vivid-50,#168821); color:#0d4a12; }
.br-message-ds.warning{ background:var(--yellow-vivid-5,#fff5c2); border-color:var(--yellow-vivid-20,#ffcd07); color:#333; }
.br-message-ds.danger{ background:var(--red-vivid-10,#fde0db); border-color:var(--red-vivid-50,#e52207); color:#5c0d03; }

/* alerts nativos do Streamlit no padrão br-message */
[data-testid="stAlert"] > div{ border-radius:4px !important; border-left:8px solid currentColor !important; }

/* ---------- br-tag (severidade) ---------- */
.br-tag-ds{
  display:inline-block; border-radius:100em; padding:2px 12px; font-size:13px; font-weight:600;
  margin-right:6px; white-space:nowrap; vertical-align:middle;
}
.br-tag-ds.critica{ background:var(--red-vivid-50,#e52207); color:#fff; }
.br-tag-ds.alta{ background:var(--orange-vivid-50,#c05600); color:#fff; }
.br-tag-ds.media{ background:var(--yellow-vivid-20,#ffcd07); color:#333; }
.br-tag-ds.info{ background:var(--blue-warm-vivid-70,#1351b4); color:#fff; }
.br-tag-ds.ia{ background:var(--gray-80,#333); color:#fff; }
.br-tag-ds.ok{ background:var(--green-cool-vivid-50,#168821); color:#fff; }
.br-tag-ds.prototipo{ background:var(--yellow-vivid-20,#ffcd07); color:#333; }
/* faixas de prioridade: tons de UM azul (ordem), sem semântica de bom/ruim */
.br-tag-ds.faixa-alta{ background:#1351B4; color:#fff; }
.br-tag-ds.faixa-media{ background:#D4E5FF; color:#071D41; }
.br-tag-ds.faixa-baixa{ background:#F0F0F0; color:#333; border:1px solid #CCCCCC; }
.br-tag-ds.neutra{ background:#fff; color:#555; border:1px solid #CCCCCC; }

/* cartão de projeto na vitrine */
.br-projeto{ background:#fff; border:1px solid #e6e6e6; border-radius:8px; padding:16px 18px; margin:10px 0;
  box-shadow:0 1px 4px rgba(0,0,0,.08); }
.br-projeto .titulo{ font-weight:700; font-size:17px; color:#071D41; margin:4px 0 2px 0; }
.br-projeto .meta{ font-size:13.5px; color:#555; margin-bottom:8px; }
.br-projeto .porque{ font-size:14px; color:#333; margin-top:8px; }
.br-barra{ display:flex; height:12px; border-radius:6px; overflow:hidden; background:#F0F0F0; margin:6px 0 4px 0; }
.br-barra span{ display:block; height:100%; }
.br-legenda{ display:flex; flex-wrap:wrap; gap:10px; font-size:12px; color:#555; }
.br-legenda i{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:4px; vertical-align:-1px; }

/* ---------- expander como br-item ---------- */
[data-testid="stExpander"] details{ border-radius:4px !important; border:1px solid var(--gray-10,#e6e6e6) !important; }
[data-testid="stExpander"] summary{ font-size:15px; }

/* ---------- abas ---------- */
.stTabs [data-baseweb="tab-list"]{ gap:4px; border-bottom:1px solid var(--gray-20,#ccc); }
.stTabs [data-baseweb="tab"]{ font-weight:600; font-size:16px; padding:10px 18px; color:var(--gray-60,#636363); }
.stTabs [aria-selected="true"]{ color:var(--ds-primary) !important; }

/* ---------- br-footer ---------- */
.br-footer-ds{
  background:var(--ds-primary-dark); color:#fff; border-radius:4px; padding:22px 26px; margin-top:28px;
  font-size:13.5px; line-height:1.6;
}
.br-footer-ds a{ color:#c5d4eb; }
.br-footer-ds .linha{ border-top:1px solid rgba(255,255,255,.25); margin:12px 0; }
.br-footer-ds .colunas{ display:flex; gap:40px; flex-wrap:wrap; }
.br-footer-ds .colunas > div{ flex:1 1 220px; }
.br-footer-ds .colunas strong{ display:block; text-transform:uppercase; letter-spacing:.04em; margin-bottom:4px; font-size:12.5px; }

/* passo-a-passo (br-step) */
.br-step-ds{ display:flex; gap:10px; flex-wrap:wrap; margin:6px 0 14px 0; }
.br-step-ds .passo{ display:flex; align-items:center; gap:8px; font-size:14px; color:var(--gray-80,#333); }
.br-step-ds .num{ width:28px; height:28px; border-radius:50%; background:var(--ds-primary); color:#fff;
  display:flex; align-items:center; justify-content:center; font-weight:700; font-size:13px; }
.br-step-ds .sep{ color:var(--gray-40,#888); }
"""

ICONE_MSG = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "danger": "⛔"}


def aplicar_tema():
    tokens = TOKENS.read_text(encoding="utf-8") if TOKENS.exists() else ""
    st.markdown(f"<style>{IMPORTS}{tokens}\n{CSS}</style>", unsafe_allow_html=True)


def cabecalho():
    st.markdown(
        """<header class="br-header-ds" role="banner">
             <div class="marca">
               <div class="sigla" aria-hidden="true">AE</div>
               <div class="divisor" aria-hidden="true"></div>
               <div>
                 <div class="titulo">AnalisaEmendas</div>
                 <div class="subtitulo">Destinação e análise de emendas parlamentares</div>
               </div>
             </div>
             <div class="acoes"><span class="br-tag-ds prototipo">PROTÓTIPO · dados fictícios</span></div>
           </header>""",
        unsafe_allow_html=True,
    )


def breadcrumb(*itens: str):
    partes = ['<a href="./" target="_self">Início</a>'] + [html.escape(i) for i in itens]
    st.markdown('<nav class="br-breadcrumb-ds" aria-label="Breadcrumb">'
                + '<span class="sep">›</span>'.join(partes) + "</nav>", unsafe_allow_html=True)


def titulo(texto: str, sub: str = "", *trilha: str):
    breadcrumb(*(trilha or (texto,)))
    st.title(texto)
    if sub:
        st.markdown(f"<p style='color:#636363;margin-top:-10px;font-size:16px'>{html.escape(sub)}</p>",
                    unsafe_allow_html=True)


def mensagem(tipo: str, titulo_msg: str, texto: str = ""):
    st.markdown(
        f'<div class="br-message-ds {tipo}" role="{"alert" if tipo == "danger" else "status"}">'
        f'<span class="icone" aria-hidden="true">{ICONE_MSG[tipo]}</span>'
        f"<div><strong>{html.escape(titulo_msg)}</strong>{texto}</div></div>",
        unsafe_allow_html=True,
    )


def tag(texto: str, tipo: str) -> str:
    return f'<span class="br-tag-ds {tipo}">{html.escape(texto)}</span>'


def card(icone: str, titulo_card: str, texto: str):
    st.markdown(
        f'<div class="br-card-ds"><div class="card-icone" aria-hidden="true">{icone}</div>'
        f'<div class="card-titulo">{html.escape(titulo_card)}</div>'
        f'<div class="card-texto">{texto}</div></div>',
        unsafe_allow_html=True,
    )


def passos(itens: list[str]):
    h = []
    for i, t in enumerate(itens, 1):
        h.append(f'<span class="passo"><span class="num">{i}</span>{html.escape(t)}</span>')
    st.markdown('<div class="br-step-ds">' + '<span class="sep">→</span>'.join(h) + "</div>",
                unsafe_allow_html=True)


def rodape():
    st.markdown(
        """<footer class="br-footer-ds" role="contentinfo">
             <div class="colunas">
               <div><strong>Sobre</strong>Protótipo aberto (MIT) de apoio à decisão para análise de
                 emendas parlamentares.</div>
               <div><strong>Uso responsável</strong>Humano no controle · regras auditáveis · LGPD.</div>
               <div><strong>Padrão visual</strong>Tokens do Design System gov.br (@govbr-ds/core 3.7, MIT).</div>
             </div>
             <div class="linha"></div>
             As verificações automatizadas não substituem a análise técnica e a manifestação jurídica.
             Dados de exemplo são fictícios.
           </footer>""",
        unsafe_allow_html=True,
    )
