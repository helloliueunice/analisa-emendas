from pathlib import Path

import pandas as pd
import streamlit as st

from core.documentos import analisar_documentos, carregar_checklist
from core.extracao import extrair_texto
from ui import estado, guardar, listar_achados, placar, rodape

EX = Path(__file__).resolve().parent.parent / "data" / "exemplos" / "documentos"
s = estado()

st.title("2. Checklist documental")
st.caption("Classifica os arquivos enviados contra o checklist do normativo (config/checklist_documental.yaml) "
           "e lê a validade das certidões.")

checklist = carregar_checklist()
padrao = s["meta"].get("tipo_proponente", "osc")
tipo = st.radio("Tipo de proponente", ["osc", "ente_publico"], index=0 if padrao == "osc" else 1,
                format_func=lambda x: "Organização da sociedade civil" if x == "osc" else "Ente público",
                horizontal=True)

with st.expander(f"Itens exigidos (checklist versão {checklist.get('versao')})"):
    st.dataframe(pd.DataFrame([{"Documento": i["nome"], "Obrigatório": i["obrigatorio"],
                                "Fundamento": i["fundamento"]}
                               for i in checklist["itens"] if tipo in i["aplica_a"]]), hide_index=True)

usar_ex = st.checkbox("Usar documentos de exemplo (há uma certidão vencida e um arquivo sem conteúdo)",
                      value=True)
arquivos = []
if usar_ex:
    from scripts.gerar_exemplos import documentos_txt

    documentos_txt()  # regenera com datas relativas a hoje
    arquivos = [{"nome": p.name, "texto": p.read_text(encoding="utf-8")} for p in sorted(EX.glob("*.txt"))]
    st.write("Arquivos:", ", ".join(a["nome"] for a in arquivos))
ups = st.file_uploader("Ou envie os documentos da proposta", accept_multiple_files=True,
                       type=["pdf", "docx", "txt"])
for u in ups or []:
    arquivos.append({"nome": u.name, "texto": extrair_texto(u.name, u.getvalue())})

if arquivos and st.button("Verificar documentação", type="primary"):
    guardar(analisar_documentos(arquivos, tipo, checklist))

res = s["resultados"].get("Checklist Documental")
if res:
    st.divider()
    placar(res)

    def cor(v):
        if v == "Pendente" or v == "VENCIDO":
            return "background-color: rgba(220,38,38,.18)"
        if str(v).startswith(("Vence", "Encontrado –")):
            return "background-color: rgba(234,179,8,.20)"
        return "background-color: rgba(22,163,74,.15)" if v == "Encontrado" else ""

    df = pd.DataFrame(res.resumo["tabela"])
    st.dataframe(df.style.map(cor, subset=["Status"]), hide_index=True, use_container_width=True)
    listar_achados(res.achados)
rodape()
