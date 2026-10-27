# 🏛️ AnalisaEmendas

**Protótipo de IA para apoiar a análise de propostas oriundas de emendas parlamentares** nas fases de
formalização e acompanhamento das parcerias: plano de trabalho, documentação exigida pelo normativo,
verificação de custos e legitimidade de assinatura digital.

> Problema público de origem: o volume de emendas cresce a cada exercício e absorve grande parte dos
> servidores do Executivo federal em conferências manuais e repetitivas, reduzindo a capacidade de atuar nas
> demandas finalísticas dos órgãos.

---

## 1. O que o protótipo faz

| Módulo | Verificações | Técnica |
|---|---|---|
| **1. Plano de Trabalho** | completude; CNPJ; objeto genérico/sucinto; elementos da justificativa (problema, público, resultados, política); aderência da função/subfunção à emenda; valor da emenda; valor global = repasse + contrapartida; metas, etapas, desembolso e plano de aplicação fecham; indicadores e quantidades; datas dentro da vigência; natureza de despesa × tipo de proponente | Regras determinísticas + IA generativa opcional (nexo causal, clareza, riscos) |
| **2. Checklist documental** | documentos exigidos por tipo de proponente (ente público × OSC), configuráveis em YAML; leitura da validade de certidões; arquivos não classificados | Extração de texto + classificação por palavras-chave |
| **3. Custos** | comparação com preço de referência; indício de sobrepreço (tolerância ajustável); inexequibilidade; unidade divergente; itens sem referência; concentração (curva ABC); excesso estimado em R$ | Casamento por código ou por similaridade textual |
| **4. Assinatura digital** | integridade criptográfica (PAdES); alteração após assinatura; cadeia de confiança ICP-Brasil/Gov.br; validade do certificado; carimbo do tempo; signatário esperado | pyHanko |
| **5. Minuta de parecer** | conclusão preliminar (Apto / Apto com ressalvas / Não apto), apontamentos por severidade, fundamentos a conferir; DOCX, Markdown e CSV | Consolidação |
| **Fila de triagem** | várias propostas ordenadas por risco e valor, com encaminhamento sugerido (diligência, análise detalhada, simplificada) | Lote |

Cada apontamento traz **regra, severidade, evidência, providência sugerida e fundamento a conferir**.
A IA só *sugere*; sugestões aparecem marcadas com 🤖 e o analista decide.

---

## 2. Testar em 5 minutos (na sua máquina)

Pré-requisitos: Python 3.10+ e Git.

```bash
git clone https://github.com/<sua-conta>/analisa-emendas.git
cd analisa-emendas
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/gerar_exemplos.py # (re)gera documentos e PDFs assinados de teste
streamlit run app.py             # abre em http://localhost:8501
```

Roteiro de teste sugerido (todos os dados são fictícios):

1. **Plano de Trabalho** → "Exemplo com problemas" → *Analisar*: 15 apontamentos (CNPJ inválido,
   finalidade divergente da emenda, metas que não fecham, etapa fora da vigência...). Compare com o
   "Exemplo adequado" (risco 0).
2. **Checklist documental** → OSC → *Verificar*: CNDT vencida, FGTS a vencer, documentos ausentes.
3. **Custos** → *Verificar*: caixa de som, refletor e hora-aula acima da referência; drone sem referência.
4. **Assinatura digital** → *Verificar*: `plano_assinado.pdf` íntegro, `plano_adulterado.pdf` inválido,
   ofício sem assinatura. Copie `data/exemplos/ac_teste.crt` para `certs/` e veja a assinatura virar
   "confiável".
5. **Minuta de parecer** → revise o texto e baixe o DOCX.
6. **Fila de triagem** → veja a priorização por risco.

Testes automatizados: `pip install pytest && pytest -q`

---

## 3. Publicar no GitHub

```bash
cd analisa-emendas
git init -b main
git add .
git commit -m "AnalisaEmendas: protótipo inicial"
# crie um repositório vazio em github.com/new (ex.: analisa-emendas) e então:
git remote add origin https://github.com/<sua-conta>/analisa-emendas.git
git push -u origin main
```

Ou, com a CLI do GitHub: `gh repo create analisa-emendas --public --source . --push`

O workflow `.github/workflows/ci.yml` roda os testes a cada push.

> ⚠️ Nunca versione documentos reais de propostas, chaves de API ou `.streamlit/secrets.toml`
> (já estão no `.gitignore`).

## 4. Publicar no Streamlit Community Cloud (link para a equipe testar)

1. Acesse **share.streamlit.io** e entre com a conta do GitHub.
2. **Create app** → selecione o repositório `analisa-emendas`, branch `main`, arquivo `app.py`.
3. (Opcional, para ativar a IA) **Advanced settings → Secrets**, cole o conteúdo de
   `.streamlit/secrets.toml.example` com sua chave.
4. **Deploy**. Em ~2 min você recebe uma URL `https://<nome>.streamlit.app` para compartilhar.

> O Community Cloud é adequado para **teste com dados fictícios**. Para dados reais, use a implantação
> interna (seção 5).

## 5. Implantação interna no órgão (dados reais)

```bash
docker build -t analisa-emendas .
docker run -p 8501:8501 -v $(pwd)/certs:/app/certs analisa-emendas
```

Para IA sem enviar dados para fora da rede, rode um modelo aberto (Ollama/vLLM) num servidor do órgão e
configure `LLM_PROVIDER = "openai_compat"` e `LLM_BASE_URL` (ver `secrets.toml.example`). Coloque o
app atrás do login institucional (proxy reverso com SSO/gov.br).

---

## 6. Passo a passo para transformar o protótipo em solução (roteiro de IA)

**Etapa 1 – Diagnóstico (2–4 semanas).** Mapear o fluxo atual de análise (formalização e
acompanhamento), medir tempo médio por proposta, volume por exercício e os motivos mais frequentes de
diligência e de impedimento técnico. Esses números viram a linha de base dos indicadores.

**Etapa 2 – Base de regras com a área técnica e jurídica (paralelo).** Converter o normativo em regras
verificáveis (Decreto 11.531/2023, Portaria Conjunta MGI/MF/CGU 33/2023, Lei 13.019/2014 para OSC,
LC 210/2024, LDO do exercício, portarias setoriais). Revisar `config/checklist_documental.yaml` e
`core/plano_trabalho.py`. **Regras primeiro, IA depois**: o que é verificável deve ser determinístico e
auditável.

**Etapa 3 – Dados.** Montar um conjunto histórico rotulado (propostas aprovadas, diligenciadas,
reprovadas, com os motivos) para calibrar as regras e avaliar a IA. Definir as fontes de preço de
referência (Painel de Preços, SINAPI/SICRO, contratações do próprio órgão) e o casamento por código
CATMAT/CATSER.

**Etapa 4 – Integração.** Substituir o upload manual por integração com o Transferegov.br (APIs/dados
abertos disponibilizados pelo MGI, quando houver acesso) e com o SEI, para ler planos, anexos e
pareceres sem redigitação.

**Etapa 5 – IA generativa com segurança.** Usar o modelo para o que regra não captura: nexo causal,
clareza do objeto, coerência entre metas e orçamento, resumo para o parecer e estruturação de PDFs.
Preferir modelo na infraestrutura do órgão para dados pessoais; pseudonimizar antes de qualquer envio
externo; registrar prompts e respostas para auditoria; medir taxa de acerto contra os rótulos.

**Etapa 6 – Piloto (1 unidade, 1 ciclo de emendas).** Rodar em paralelo com a análise manual e medir:
tempo por proposta, % de pendências detectadas pela ferramenta que o analista confirmou (precisão),
pendências que a ferramenta deixou passar (revocação), retrabalho e satisfação do analista.

**Etapa 7 – Governança e escala.** Comitê com área finalística, jurídica, TI, controle interno e
encarregado de dados (LGPD); avaliação de impacto à proteção de dados; versionamento das regras;
publicação do código como software público para reuso por outros ministérios.

### Indicadores sugeridos
- Tempo médio de análise por proposta (meta inicial: −40%)
- Propostas analisadas por servidor/mês
- Precisão e revocação dos apontamentos automáticos
- % de diligências resolvidas na primeira rodada
- Prazo entre indicação da emenda e celebração

---

## 7. Estrutura do repositório

```
app.py                      navegação do Streamlit
ui.py                       componentes de interface
views/                      páginas (plano, documentos, custos, assinatura, parecer, fila)
core/                       lógica de análise, independente da interface
  plano_trabalho.py         regras PT-01 a PT-20
  documentos.py             checklist DOC-01 a DOC-05
  custos.py                 regras CUS-01 a CUS-05
  assinatura.py             regras ASS-00 a ASS-07 (pyHanko)
  llm.py                    IA opcional (Claude API ou modelo local compatível)
  parecer.py                minuta em Markdown/DOCX
config/checklist_documental.yaml   checklist editável pela área jurídica
data/exemplos/              dados FICTÍCIOS para teste
certs/                      raízes de confiança (ICP-Brasil, Gov.br)
scripts/gerar_exemplos.py   gera documentos e PDFs assinados de teste
tests/                      testes automatizados
```

## 8. Limitações conhecidas
- Os fundamentos citados são ponto de partida e **devem ser conferidos** com o normativo vigente e as
  orientações do órgão.
- PDFs digitalizados (imagem) exigem OCR (ex.: Tesseract) antes da análise.
- Validação de assinatura sem consulta de revogação (LCR/OCSP) por padrão; para conformidade oficial,
  confronte com o Verificador do ITI (validar.iti.gov.br).
- Casamento de preços por similaridade textual é aproximado.

## Licença
MIT – reuso livre por órgãos públicos e pela sociedade.
