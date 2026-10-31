import streamlit as st

import ds_govbr as ds
from core import llm
from ui import estado, rodape

s = estado()
ds.breadcrumb("Visão geral")
st.title("Emendas parlamentares: destinar bem e analisar com apoio de IA")
st.markdown(
    "<p style='font-size:18px;color:#555;max-width:900px'>Triagem e pré-análise de propostas nas fases de "
    "<b>formalização</b> e <b>acompanhamento</b>: o servidor recebe os apontamentos com regra, evidência e "
    "fundamento, e uma minuta de parecer para revisar — dedicando seu tempo ao juízo técnico, não à "
    "conferência repetitiva.</p>", unsafe_allow_html=True)

st.subheader("Antes da indicação: Banco de Projetos de Impacto (piloto)")
st.markdown("<p style='font-size:16px;color:#555;max-width:900px'>Necessidades medidas por município e projetos "
            "certificados pelo ministério, ordenados em faixas dentro de cada programa. A escolha da emenda continua "
            "livre e fica registrada publicamente, até o resultado.</p>", unsafe_allow_html=True)
ds.passos(["Mapa de lacunas", "Cadastro", "Curadoria", "Vitrine para gabinetes", "Painel público"])
c = st.columns(3)
with c[0]:
    ds.card("🗺️", "Lacunas e projetos", "Onde falta biblioteca, ponto de cultura ou CEU, e quem já tem projeto. "
            "Modelo padronizado para municípios sem equipe técnica e canal para demanda <b>sem CNPJ</b>.")
with c[1]:
    ds.card("✅", "Curadoria e faixas", "Certificação por <b>checklist objetivo</b>; faixas Alta, Média e Baixa "
            "<b>dentro do programa</b>, com teste de sensibilidade dos pesos.")
with c[2]:
    ds.card("🔎", "Integridade", "Linhas vermelhas aplicadas no cadastro, alertas de consultoria recorrente, "
            "indicador <b>dentro × fora do banco</b>, reconciliação e registro com hash encadeado.")

st.subheader("Depois da indicação: análise da proposta")
ds.passos(["Plano de Trabalho", "Documentos", "Custos", "Assinatura", "Execução", "Parecer auditável"])

c = st.columns(3)
with c[0]:
    ds.card("📋", "1. Plano de Trabalho", "Completude, CNPJ, objeto, justificativa, finalidade da emenda, "
            "fechamento de metas, etapas, desembolso e vigência. <b>23 regras.</b>")
with c[1]:
    ds.card("📁", "2. Checklist documental", "Itens do normativo por tipo de proponente, validade de "
            "certidões, <b>CNPJ da certidão × proponente</b> e PDFs digitalizados.")
with c[2]:
    ds.card("💰", "3. Custos", "Preço de referência, sobrepreço, inexequibilidade, unidade, curva ABC e "
            "<b>orçamento × plano</b>.")
st.write("")
c = st.columns(3)
with c[0]:
    ds.card("✍️", "4. Assinatura digital", "Integridade PAdES, alteração pós-assinatura, cadeia "
            "ICP-Brasil/Gov.br, LCR/OCSP opcional e signatário esperado.")
with c[1]:
    ds.card("📈", "5. Execução", "Físico × financeiro, NF duplicada, pagamento fora da vigência, "
            "fracionamento, autopagamento e recursos parados.")
with c[2]:
    ds.card("🧾", "6. Parecer auditável", "Minuta DOCX e registro com <b>hash SHA-256</b> das entradas e das "
            "regras, para reproduzir e contestar cada conclusão.")

st.subheader("Como testar em 3 minutos")
st.markdown("""
1. **Plano de Trabalho** → *Exemplo com problemas* → **Analisar**.
2. Siga pelo menu: **Documentos**, **Custos**, **Assinatura** e **Execução** já vêm com exemplos.
3. Em **Parecer e auditoria**, baixe a minuta (DOCX) e o registro de auditoria (JSON).
4. Em **Qualidade das regras**, veja a precisão e a revocação medidas em base rotulada.
""")

if llm.disponivel():
    ds.mensagem("success", "Camada de IA generativa ativa.", f" {llm.descricao_provedor()}. "
                "Sugestões da IA são marcadas e nunca são impeditivas por si só.")
else:
    ds.mensagem("info", "Camada de IA generativa desativada.",
                " O app funciona integralmente com regras determinísticas. Para ativar, configure "
                "<code>ANTHROPIC_API_KEY</code> ou um modelo local em <code>.streamlit/secrets.toml</code>.")

st.subheader("Princípios de uso responsável")
c = st.columns(4)
for col, (t, d) in zip(c, [
    ("Humano no controle", "A ferramenta recomenda; o analista decide e assina."),
    ("Explicabilidade", "Cada apontamento traz regra, evidência e fundamento a conferir."),
    ("Proteção de dados", "Pseudonimização antes da IA e opção de modelo na rede do órgão (LGPD)."),
    ("Rastreabilidade", "Regras versionadas no Git, parâmetros em YAML e selo SHA-256 por parecer."),
]):
    with col:
        ds.card("", t, d)
rodape()
