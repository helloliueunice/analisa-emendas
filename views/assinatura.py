from pathlib import Path

import pandas as pd
import streamlit as st

import ds_govbr as ds
from core.assinatura import carregar_raizes, conferir_signatarios, verificar_pdf
from core.auditoria import sha256
from core.modelos import ResultadoModulo
from ui import estado, guardar, listar_achados, placar, rodape

EX = Path(__file__).resolve().parent.parent / "data" / "exemplos" / "pdfs"
s = estado()

ds.titulo("4. Verificação de assinatura digital",
          "Valida assinaturas PAdES embutidas em PDF: integridade, alterações posteriores, cadeia de confiança "
          "e signatário.", "Formalização", "Assinatura digital")

raizes = carregar_raizes()
if raizes:
    ds.mensagem("success", f"{len(raizes)} raiz(es) de confiança carregada(s) em certs/.")
else:
    ds.mensagem("warning", "Nenhuma raiz de confiança carregada.",
                " As assinaturas serão checadas quanto à integridade, mas aparecerão como “não confiáveis”. "
                "Baixe as cadeias ICP-Brasil (ITI) e da AC Raiz do Governo Federal (gov.br) para <code>certs/</code>. "
                "Para o teste, copie <code>data/exemplos/ac_teste.crt</code> para <code>certs/</code>.")

c1, c2 = st.columns([3, 2])
usar_ex = c1.checkbox("Usar PDFs de exemplo (íntegro, adulterado e sem assinatura)", value=True)
rede = c2.toggle("Consultar revogação online (LCR/OCSP)", value=False,
                 help="Requer acesso de rede às ACs. Desligado: valida integridade e cadeia sem revogação.")
ups = st.file_uploader("Envie PDFs assinados", type=["pdf"], accept_multiple_files=True)
esperados = st.text_input("Signatários esperados (nome ou CPF, separados por ;)",
                          placeholder="Ex.: Maria Exemplo da Silva; 00000000191")

if st.button("Verificar assinaturas", type="primary"):
    pdfs = [(p.name, p.read_bytes()) for p in sorted(EX.glob("*.pdf"))] if usar_ex and EX.exists() else []
    pdfs += [(u.name, u.getvalue()) for u in ups or []]
    total = ResultadoModulo("Assinatura Digital")
    linhas = []
    for nome, dados in pdfs:
        r = verificar_pdf(dados, nome, raizes, permitir_rede=rede)
        total.achados += r.achados
        linhas += r.resumo.get("assinaturas", [])
        s["entradas"][f"pdf:{nome}"] = sha256(dados)
    if esperados.strip() and linhas:
        total.achados += conferir_signatarios(linhas, esperados.split(";"))
    total.resumo = {"assinaturas": linhas, "n_pdfs": len(pdfs)}
    guardar(total)

res = s["resultados"].get("Assinatura Digital")
if res:
    st.divider()
    placar(res)
    if res.resumo["assinaturas"]:
        def cor(v):
            return {"Sim": "background-color:#E3F5E1", "NÃO": "background-color:#FDE0DB;font-weight:700",
                    "Não": "background-color:#FFF5C2"}.get(v, "")
        df = pd.DataFrame(res.resumo["assinaturas"])
        st.dataframe(df.style.map(cor, subset=["Íntegra", "Confiável (cadeia)"]), hide_index=True,
                     use_container_width=True)
    listar_achados(res.achados)
    ds.mensagem("info", "Conformidade oficial:", " confronte o resultado com o Verificador do ITI "
                "(<a href='https://validar.iti.gov.br' target='_blank'>validar.iti.gov.br</a>).")
rodape()
