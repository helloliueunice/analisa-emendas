from pathlib import Path

import pandas as pd
import streamlit as st

import ds_govbr as ds
from core.auditoria import sha256
from core.documentos import analisar_documentos, carregar_checklist
from core.extracao import extrair_texto
from ui import estado, guardar, listar_achados, placar, rodape

EX = Path(__file__).resolve().parent.parent / "data" / "exemplos" / "documentos"
s = estado()

ds.titulo("2. Checklist documental",
          "Classifica os arquivos contra o checklist do normativo, lê a validade das certidões e confere a "
          "titularidade (CNPJ).", "Formalização", "Checklist documental")

checklist = carregar_checklist()
padrao = s["meta"].get("tipo_proponente", "osc")
c1, c2 = st.columns([2, 1])
tipo = c1.radio("Tipo de proponente", ["osc", "ente_publico"], index=0 if padrao == "osc" else 1,
                format_func=lambda x: "Organização da sociedade civil" if x == "osc" else "Ente público",
                horizontal=True)
cnpj = c2.text_input("CNPJ do proponente (cruzamento)", s["meta"].get("cnpj", "98.765.432/0001-98"),
                     help="Preenchido automaticamente quando o Plano de Trabalho já foi analisado.")

with st.expander(f"Itens exigidos – checklist versão {checklist.get('versao')}"):
    st.dataframe(pd.DataFrame([{"Documento": i["nome"], "Obrigatório": "Sim" if i["obrigatorio"] else "Não",
                                "Tem validade": "Sim" if i.get("validade") else "Não",
                                "Fundamento": i["fundamento"]}
                               for i in checklist["itens"] if tipo in i["aplica_a"]]),
                 hide_index=True, use_container_width=True)

usar_ex = st.checkbox("Usar documentos de exemplo (há certidão vencida, certidão a vencer e arquivo sem conteúdo)",
                      value=True)
arquivos = []
if usar_ex:
    from scripts.gerar_exemplos import documentos_txt

    documentos_txt()  # regenera com datas relativas a hoje
    arquivos = [{"nome": p.name, "texto": p.read_text(encoding="utf-8")} for p in sorted(EX.glob("*.txt"))]
ups = st.file_uploader("Envie os documentos da proposta", accept_multiple_files=True, type=["pdf", "docx", "txt"])
for u in ups or []:
    arquivos.append({"nome": u.name, "texto": extrair_texto(u.name, u.getvalue()), "_bytes": u.getvalue()})
if arquivos:
    st.caption(f"{len(arquivos)} arquivo(s): " + ", ".join(a["nome"] for a in arquivos))

if arquivos and st.button("Verificar documentação", type="primary"):
    guardar(analisar_documentos(arquivos, tipo, checklist, cnpj_proponente=cnpj or None))
    for a in arquivos:
        s["entradas"][f"doc:{a['nome']}"] = sha256(a.get("_bytes") or a["texto"])

res = s["resultados"].get("Checklist Documental")
if res:
    st.divider()
    placar(res)

    def cor(v):
        if v in ("Pendente", "VENCIDO"):
            return "background-color:#FDE0DB;color:#5c0d03;font-weight:600"
        if str(v).startswith(("Vence", "Encontrado –")):
            return "background-color:#FFF5C2"
        return "background-color:#E3F5E1;color:#0d4a12" if v == "Encontrado" else ""

    aba1, aba2 = st.tabs(["Situação dos documentos", "Apontamentos"])
    with aba1:
        df = pd.DataFrame(res.resumo["tabela"])
        st.dataframe(df.style.map(cor, subset=["Status"]), hide_index=True, use_container_width=True)
    with aba2:
        listar_achados(res.achados)
rodape()
