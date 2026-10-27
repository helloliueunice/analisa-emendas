import streamlit as st

from core import llm
from ui import rodape

st.title("🏛️ AnalisaEmendas")
st.subheader("IA para apoiar a análise de propostas de emendas parlamentares")

st.markdown("""
**Problema:** o volume de emendas parlamentares cresce a cada exercício e consome grande parte da força de
trabalho dos órgãos, que analisam manualmente planos de trabalho, documentos, custos e assinaturas.

**Proposta:** um assistente que faz a *triagem e a pré-análise* de cada proposta, aponta pendências com o
fundamento a conferir e entrega uma **minuta de parecer** para o analista revisar — liberando o servidor para
o juízo técnico, e não para conferências repetitivas.
""")

c1, c2, c3, c4 = st.columns(4)
c1.info("**1. Plano de Trabalho**\n\nCompletude, CNPJ, objeto genérico, nexo da justificativa, "
        "fechamento de metas, etapas, desembolso e finalidade da emenda.")
c2.info("**2. Documentos**\n\nChecklist configurável por normativo, leitura de validade de certidões e "
        "arquivos não classificados.")
c3.info("**3. Custos**\n\nComparação com preços de referência, indícios de sobrepreço, unidade divergente "
        "e curva ABC.")
c4.info("**4. Assinatura**\n\nIntegridade criptográfica (PAdES), alteração pós-assinatura, cadeia "
        "ICP-Brasil/Gov.br e signatário esperado.")

st.markdown("""
### Como testar em 2 minutos
1. Abra **1. Plano de Trabalho** e escolha o exemplo *com problemas* → clique em **Analisar**.
2. Em **2. Checklist documental**, use os documentos de exemplo (há uma certidão vencida).
3. Em **3. Custos**, rode o orçamento de exemplo contra a tabela de referência.
4. Em **4. Assinatura**, compare o PDF íntegro com o adulterado.
5. Em **5. Minuta de parecer**, baixe o parecer consolidado em DOCX.
6. Em **Fila de triagem**, veja como várias propostas são priorizadas por risco.
""")

st.markdown("### Camada de IA generativa")
if llm.disponivel():
    st.success(f"Ativa — {llm.descricao_provedor()}. Sugestões da IA aparecem marcadas com 🤖.")
else:
    st.warning("Desativada (nenhuma chave configurada). O app funciona com as regras determinísticas. "
               "Para ativar, defina `ANTHROPIC_API_KEY` ou um servidor local compatível em "
               "`.streamlit/secrets.toml` (veja o README).")

st.markdown("""
### Princípios de uso responsável
- **Humano no controle:** a ferramenta recomenda; quem decide é o analista.
- **Explicabilidade:** cada apontamento informa a regra, a evidência e o fundamento a conferir.
- **LGPD:** CPF, e-mail e telefone são mascarados antes de qualquer envio a modelo externo; para dados
  sensíveis, prefira um modelo executado na infraestrutura do órgão.
- **Rastreabilidade:** regras versionadas no Git e checklist em arquivo YAML revisável pela área jurídica.
""")
rodape()
