from pathlib import Path

import pandas as pd
import streamlit as st

from core.assinatura import carregar_raizes, conferir_signatarios, verificar_pdf
from core.modelos import ResultadoModulo
from ui import estado, guardar, listar_achados, placar, rodape

EX = Path(__file__).resolve().parent.parent / "data" / "exemplos" / "pdfs"
s = estado()

st.title("4. Verificação de assinatura digital")
st.caption("Valida assinaturas PAdES embutidas em PDF: integridade, alterações posteriores, cadeia de "
           "confiança e signatário.")

raizes = carregar_raizes()
st.write(f"Raízes de confiança carregadas em `certs/`: **{len(raizes)}**")
if not raizes:
    st.warning("Nenhuma raiz carregada: as assinaturas serão checadas quanto à integridade, mas aparecerão como "
               "'não confiáveis'. Baixe as cadeias ICP-Brasil (ITI) e da AC Raiz do Governo Federal (gov.br) "
               "para a pasta `certs/`. Para o teste, copie `data/exemplos/ac_teste.crt` para `certs/`.")

usar_ex = st.checkbox("Usar PDFs de exemplo (íntegro, adulterado e sem assinatura)", value=True)
ups = st.file_uploader("Ou envie PDFs assinados", type=["pdf"], accept_multiple_files=True)
esperados = st.text_input("Signatários esperados (nome ou CPF, separados por ;)",
                          placeholder="Ex.: Maria Exemplo da Silva; 00000000191")

if st.button("Verificar assinaturas", type="primary"):
    pdfs = [(p.name, p.read_bytes()) for p in sorted(EX.glob("*.pdf"))] if usar_ex and EX.exists() else []
    pdfs += [(u.name, u.getvalue()) for u in ups or []]
    total = ResultadoModulo("Assinatura Digital")
    linhas = []
    for nome, dados in pdfs:
        r = verificar_pdf(dados, nome, raizes)
        total.achados += r.achados
        linhas += r.resumo.get("assinaturas", [])
    if esperados.strip() and linhas:
        total.achados += conferir_signatarios(linhas, esperados.split(";"))
    total.resumo = {"assinaturas": linhas}
    guardar(total)

res = s["resultados"].get("Assinatura Digital")
if res:
    st.divider()
    placar(res)
    if res.resumo["assinaturas"]:
        st.dataframe(pd.DataFrame(res.resumo["assinaturas"]), hide_index=True, use_container_width=True)
    listar_achados(res.achados)
    st.caption("Para conformidade oficial, confronte com o Verificador do ITI: https://validar.iti.gov.br")
rodape()
