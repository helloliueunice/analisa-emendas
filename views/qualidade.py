import streamlit as st

import ds_govbr as ds
from core.avaliacao import DEFEITOS, avaliar, gerar_base
from ui import rodape

ds.titulo("Qualidade das regras",
          "Precisão e revocação medidas em base rotulada. É o que permite confiar — ou não — em cada regra.",
          "Governança", "Qualidade das regras")


@st.cache_data(show_spinner="Avaliando regras...")
def rodar(n, semente, validacao):
    return avaliar(gerar_base(n, semente, validacao))


c1, c2, c3 = st.columns(3)
n = c1.number_input("Casos", 50, 2000, 300, 50)
semente = c2.number_input("Semente aleatória", 0, 9999, 42)
conjunto = c3.radio("Conjunto", ["Calibração", "Validação (textos não usados na calibração)"])
metr, casos = rodar(int(n), int(semente), conjunto.startswith("Valida"))

prec = metr["VP"].sum() / max(metr["VP"].sum() + metr["FP"].sum(), 1)
rev = metr["VP"].sum() / max(metr["VP"].sum() + metr["FN"].sum(), 1)
m = st.columns(4)
m[0].metric("Precisão global", f"{prec:.1%}")
m[1].metric("Revocação global", f"{rev:.1%}")
m[2].metric("Casos com acerto exato", f"{casos['Acerto exato'].mean():.1%}")
m[3].metric("Disparo da triagem semântica (PT-23)", f"{metr.attrs['taxa_triagem_pt23']:.0%}")

ds.mensagem("warning", "Lição registrada na avaliação.",
            " Na primeira versão, a regra lexical PT-06 (elementos da justificativa) teve 0% de precisão no "
            "conjunto de validação: textos adequados, escritos com outro vocabulário, eram apontados como falhos. "
            "A regra foi restringida ao caso extremo e o sinal parcial virou nota informativa (PT-23), que não "
            "altera a conclusão. O alto disparo da PT-23 na validação mostra que o nexo causal da justificativa "
            "precisa de leitura semântica (IA ou analista), não de palavra-chave.")

aba1, aba2, aba3 = st.tabs(["Métricas por regra", "Casos", "Defeitos injetados"])
with aba1:
    st.dataframe(metr, hide_index=True, use_container_width=True, column_config={
        "Precisão": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent"),
        "Revocação": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent"),
    })
with aba2:
    so_erros = st.toggle("Mostrar só os casos com divergência")
    st.dataframe(casos[~casos["Acerto exato"]] if so_erros else casos, hide_index=True,
                 use_container_width=True, height=380)
with aba3:
    st.dataframe([{"Defeito": k, "Regra(s) esperada(s)": ", ".join(sorted(v[1]))} for k, v in DEFEITOS.items()],
                 hide_index=True, use_container_width=True)

ds.mensagem("info", "Limite desta medição:", " a base é sintética. Ela prova que as regras detectam os defeitos "
            "que se propõem a detectar e expõe falsos positivos de redação, mas a métrica de produção deve vir de "
            "uma amostra real de propostas rotulada por analistas (ver etapa 3 do README).")
rodape()
