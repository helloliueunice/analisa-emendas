import json

import streamlit as st

import ds_govbr as ds
from core import llm
from core.auditoria import registro, verificar_selo
from core.parecer import gerar_docx, gerar_markdown, recomendacao_geral
from ui import estado, rodape, tabela_achados

s = estado()
ds.titulo("6. Minuta de parecer e trilha de auditoria",
          "Consolida os módulos executados. A minuta é um rascunho: a decisão e a assinatura são do analista.",
          "Resultado", "Parecer e auditoria")

resultados = list(s["resultados"].values())
if not resultados:
    ds.mensagem("info", "Nenhum módulo executado ainda.",
                " Execute ao menos uma análise (comece pelo Plano de Trabalho) para gerar a minuta.")
    rodape()
    st.stop()

st.caption("Módulos considerados: " + " · ".join(r.modulo for r in resultados))
s["meta"]["analista"] = st.text_input("Nome do analista responsável", s["meta"].get("analista", ""))

conclusao = recomendacao_geral(resultados, s["achados_ia"])
tipo = "danger" if conclusao.startswith("NÃO") else ("warning" if "RESSALVAS" in conclusao else "success")
ds.mensagem(tipo, "Conclusão preliminar", " " + conclusao)

aud = registro(s["meta"], s["entradas"], resultados, s["achados_ia"],
               llm.descricao_provedor() if s["achados_ia"] else "")
md = gerar_markdown(s["meta"], resultados, s["achados_ia"], s["sintese_ia"], aud)

aba1, aba2 = st.tabs(["Minuta (editável)", "Trilha de auditoria"])
with aba1:
    md = st.text_area("Revise e edite a minuta antes de baixar", md, height=460)
    nome = str(s["meta"].get("proposta", "proposta")).replace("/", "-")
    c1, c2, c3 = st.columns(3)
    c1.download_button("Baixar parecer (DOCX)", gerar_docx(md), f"parecer_{nome}.docx",
                       "application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="primary",
                       use_container_width=True)
    c2.download_button("Baixar parecer (Markdown)", md.encode("utf-8"), f"parecer_{nome}.md", "text/markdown",
                       use_container_width=True)
    todos = [a for r in resultados for a in r.achados] + list(s["achados_ia"])
    c3.download_button("Baixar apontamentos (CSV)", tabela_achados(todos).to_csv(index=False).encode("utf-8-sig"),
                       f"apontamentos_{nome}.csv", "text/csv", use_container_width=True)
with aba2:
    m = st.columns(3)
    m[0].metric("Entradas com hash", len(aud["entradas_sha256"]))
    m[1].metric("Versão dos parâmetros", aud["versao_parametros"])
    m[2].metric("Selo íntegro", "Sim" if verificar_selo(aud) else "Não")
    st.markdown(f"**Hash das regras:** `{aud['hash_regras_sha256']}`  \n**Selo do registro:** `{aud['selo_sha256']}`")
    st.download_button("Baixar registro de auditoria (JSON)",
                       json.dumps(aud, ensure_ascii=False, indent=2).encode("utf-8"),
                       f"auditoria_{s['meta'].get('proposta', 'proposta').replace('/', '-')}.json",
                       "application/json", type="primary")
    ds.mensagem("info", "Para que serve:", " o registro permite reproduzir a análise (mesmas entradas + mesma "
                "versão das regras = mesmo resultado) e detectar qualquer alteração posterior no relatório.")
    with st.expander("Ver registro completo"):
        st.json(aud)
rodape()
