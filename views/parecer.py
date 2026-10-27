import streamlit as st

from core.parecer import gerar_docx, gerar_markdown, recomendacao_geral
from ui import estado, rodape, tabela_achados

s = estado()
st.title("5. Minuta de parecer técnico")

resultados = list(s["resultados"].values())
if not resultados:
    st.info("Execute ao menos um dos módulos de análise para gerar a minuta.")
    st.stop()

st.write("Módulos considerados:", ", ".join(r.modulo for r in resultados))
s["meta"]["analista"] = st.text_input("Nome do analista", s["meta"].get("analista", ""))
st.markdown(f"### Conclusão preliminar\n**{recomendacao_geral(resultados, s['achados_ia'])}**")

md = gerar_markdown(s["meta"], resultados, s["achados_ia"], s["sintese_ia"])
md = st.text_area("Revise e edite a minuta antes de baixar", md, height=420)

c1, c2, c3 = st.columns(3)
nome = str(s["meta"].get("proposta", "proposta")).replace("/", "-")
c1.download_button("⬇️ Baixar DOCX", gerar_docx(md), f"parecer_{nome}.docx",
                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="primary")
c2.download_button("⬇️ Baixar Markdown", md.encode("utf-8"), f"parecer_{nome}.md", "text/markdown")
todos = [a for r in resultados for a in r.achados] + list(s["achados_ia"])
c3.download_button("⬇️ Apontamentos (CSV)", tabela_achados(todos).to_csv(index=False).encode("utf-8-sig"),
                   f"apontamentos_{nome}.csv", "text/csv")
rodape()
