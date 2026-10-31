import json
from datetime import date

import pandas as pd
import streamlit as st

import ds_govbr as ds
from banco_ui import aviso_piloto, banco
from core import banco as B
from core.formato import brl
from ui import rodape

b = banco()
ds.titulo("Painel público de rastreabilidade",
          "Da lacuna medida à emenda indicada, com os indicadores de integridade abertos a qualquer pessoa.",
          "Destinação", "Painel público")
aviso_piloto()
pn = B.painel(b)

st.subheader("Funil do banco")
c = st.columns(len(pn["funil"]))
for col, (nome, v) in zip(c, pn["funil"]):
    col.metric(nome, v)

st.subheader("Dentro × fora do banco")
st.caption("Emendas de cultura indicadas na UF piloto. O indicador mostra se o banco substitui o canal informal "
           "ou só se soma a ele. Não há nenhum indicador por parlamentar.")
c = st.columns(4)
total = pn["dentro"] + pn["fora"]
c[0].metric("Emendas vinculadas a projeto do banco", pn["dentro"], f"{pn['dentro'] / max(total, 1):.0%} do total",
            delta_color="off")
c[1].metric("Emendas fora do banco", pn["fora"])
c[2].metric("Valor dentro do banco", brl(pn["valor_dentro"], 0))
c[3].metric("Valor fora do banco", brl(pn["valor_fora"], 0))
if pn["faixas_escolhidas"]:
    st.markdown("Faixa dos projetos escolhidos pelos gabinetes: " + " · ".join(
        f"**{k}**: {v}" for k, v in sorted(pn["faixas_escolhidas"].items(), key=lambda x: ["Alta", "Média", "Baixa"].index(x[0]))))

st.subheader("Reconciliação")
rec = pn["reconciliacao"]
if rec >= 1:
    ds.mensagem("success", "100% das emendas reconciliadas.")
else:
    ds.mensagem("warning", f"{rec:.0%} das emendas executadas reconciliadas com o banco.",
                " Pendentes: " + ", ".join(pn["nao_reconciliadas"]) + ". Toda emenda precisa estar vinculada a um "
                "projeto ou classificada como fora do banco; a meta é 100%.")

st.subheader("Equidade")
sp, spop = pn["pequenos_share_projetos"]
st.markdown(f"Municípios com menos de 20 mil habitantes têm **{sp:.0%} dos projetos** e "
            f"**{spop:.0%} da população** da UF. Meta do piloto: participação ao menos proporcional à população.")

st.subheader("Alertas de integridade")
al = B.alertas(b)
if al:
    st.dataframe(pd.DataFrame(al).rename(columns={"tipo": "Tipo", "detalhe": "Detalhe", "providencia": "Providência"}),
                 hide_index=True, use_container_width=True)
else:
    ds.mensagem("success", "Nenhum alerta.")

st.subheader("Período eleitoral")
d = st.date_input("Data de referência", value=date.today(), format="DD/MM/YYYY",
                  help="Simule outra data para ver o bloqueio automático.")
pe = B.periodo_eleitoral(d)
if pe["vedado"]:
    ds.mensagem("danger", "Período vedado pela lei eleitoral.",
                f" Eleição {pe['tipo']} em {pe['eleicao']:%d/%m/%Y}; vedação de {pe['inicio']:%d/%m/%Y} a "
                f"{pe['fim']:%d/%m/%Y}. Comunicações, anúncios e selos da plataforma ficam suspensos (art. 73, VI, "
                "Lei 9.504/97).")
else:
    ds.mensagem("info", "Fora do período vedado.",
                f" Próxima eleição ({pe['tipo']}): {pe['eleicao']:%d/%m/%Y}. Bloqueio automático a partir de "
                f"{pe['inicio']:%d/%m/%Y}.")

st.subheader("Emendas indicadas")
ind = pd.DataFrame(b["indicacoes"])
nomes = dict(zip(b["municipios"]["codigo"], b["municipios"]["municipio"]))
if not ind.empty:
    ind["município"] = ind["codigo_municipio"].map(nomes)
    ind["no banco"] = ind["projeto_id"].astype(str) != ""
    st.dataframe(ind[["emenda", "gabinete", "município", "programa", "valor", "projeto_id", "no banco", "situacao"]],
                 hide_index=True, use_container_width=True,
                 column_config={"valor": st.column_config.NumberColumn("valor (R$)", format="localized")})

st.subheader("Registro público de eventos")
st.caption("Cada evento sela o anterior com SHA-256: alterar um registro antigo quebra a cadeia.")
if b["registro"]:
    st.dataframe(pd.DataFrame([{**{k: v for k, v in e.items() if k != "dados"},
                                "dados": json.dumps(e["dados"], ensure_ascii=False)} for e in b["registro"]]),
                 hide_index=True, use_container_width=True)
else:
    st.caption("Nenhum evento nesta sessão. Cadastre, certifique ou vincule uma emenda para ver o registro.")

dados = {"projetos": b["projetos"], "indicacoes": b["indicacoes"], "demandas": b["demandas"],
         "registro": b["registro"]}
st.download_button("Baixar dados abertos (JSON)", json.dumps(dados, ensure_ascii=False, indent=1, default=str),
                   "banco_projetos_dados_abertos.json", "application/json")
rodape()
