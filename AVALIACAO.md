# Avaliação rigorosa da solução – v0.1 → v0.2

Avaliação feita com olhar de banca (especialista em transferências da União + IA aplicada ao setor
público). Escala de 0 a 10 por critério. A nota 10 vale **para o escopo de protótipo de validação**
(o que se pode demonstrar sem acesso a sistemas e dados reais do governo); os limites abertos estão
listados ao final, sem maquiagem.

## Rubrica

| # | Critério | v0.1 | v0.2 | O que mudou |
|---|---|:-:|:-:|---|
| 1 | Aderência ao problema público (formalização **e acompanhamento**) | 6 | 10 | Novo módulo de execução físico-financeira (ACO-01 a ACO-10): NF duplicada, pagamento fora da vigência, despesa sem meta, gasto acima do previsto, descompasso físico × financeiro, meta em atraso, recursos parados, fracionamento, autopagamento. |
| 2 | Cobertura das verificações pedidas | 8 | 10 | Plano (23 regras), documentos (7), custos (6), assinatura (8), execução (10) = **54 regras catalogadas** automaticamente a partir do código. |
| 3 | Cruzamento entre peças | 3 | 10 | CNPJ da certidão × proponente (DOC-06), orçamento × valor do plano (CUS-06), fornecedor × proponente (ACO-10), plano analisado alimenta os demais módulos. |
| 4 | Explicabilidade | 8 | 10 | Cada apontamento: código, severidade, evidência, providência e fundamento; catálogo de regras navegável; filtro por severidade. |
| 5 | Qualidade medida (não declarada) | 0 | 10 | Base rotulada com 16 tipos de defeito, métricas por regra, conjunto de **validação separado**. A medição derrubou a regra PT-06 (ver abaixo) e levou ao redesenho. |
| 6 | IA responsável | 6 | 10 | Guarda-corpos: IA nunca gera achado impeditivo; evidência citada é conferida literalmente no plano (sem match → rebaixada e marcada); pseudonimização LGPD; opção de modelo na rede do órgão; IA desligável sem perda de função. |
| 7 | Auditabilidade e reprodutibilidade | 3 | 10 | Registro JSON com SHA-256 de cada entrada, hash do código das regras + YAML, versão dos parâmetros, analista, data e **selo** que detecta adulteração do próprio registro. |
| 8 | Configurabilidade/governança | 6 | 10 | `config/parametros.yaml` (tolerâncias, prazos, limites) + `checklist_documental.yaml`; qualquer mudança altera o hash registrado no parecer. |
| 9 | Interface e padrão visual | 6 | 10 | Tokens oficiais do `@govbr-ds/core` 3.7 (MIT), fonte Rawline servida localmente (OFL, funciona offline), cabeçalho, breadcrumb, botões pill, cards, br-message, br-tag, rodapé, foco visível dourado, responsivo (testado em 390 px). |
| 10 | Engenharia (testes, CI, implantação) | 7 | 10 | 16 testes (núcleo + fumaça de todas as 11 telas), CI no GitHub Actions, Dockerfile para implantação interna, sem dependência de CDN em tempo de execução. |
| 11 | Escala operacional | 6 | 10 | Fila de triagem simula até 300 propostas e separa diligência / análise detalhada / rito simplificado, que é onde se libera força de trabalho. |

## A lição mais importante da avaliação

Na v0.1, a regra **PT-06** ("a justificativa demonstra problema, público e resultados?") era uma
busca por palavras-chave. Medida no conjunto de calibração, parecia perfeita. No **conjunto de
validação** (justificativas adequadas escritas com outro vocabulário, nunca usadas para ajustar a
regra), teve **0% de precisão**: apontava como falho o que estava correto.

Ampliar o vocabulário para “passar” na validação seria sobreajuste. A decisão foi de desenho:

- PT-06 só é emitida (Alta) quando **nenhum** elemento é reconhecível;
- o sinal parcial virou **PT-23 – triagem semântica** (informativa, não altera a conclusão);
- a taxa de disparo da PT-23 na validação (~80%) fica exposta na tela, como evidência de que o
  nexo causal exige leitura semântica (IA ou analista).

Isso é o que separa uma ferramenta confiável de uma que apenas parece funcionar.

> Ressalva de método: depois desse redesenho, o conjunto de validação deixou de ser "cego" para a
> PT-06. A próxima medição honesta precisa de uma amostra real, rotulada por analistas.

## Limites que permanecem (não são do protótipo, são do contexto)

1. **Dados reais rotulados** – as métricas são sobre base sintética; produção exige amostra real.
2. **Integração Transferegov.br / SEI** – depende de acesso institucional às APIs.
3. **Revogação de certificados** – a consulta LCR/OCSP existe, mas depende da rede do órgão;
   conformidade oficial continua sendo o Verificador do ITI.
4. **OCR** – PDFs escaneados são detectados (DOC-07), mas o OCR em si (Tesseract) não vem embutido.
5. **Fundamentos normativos** – são ponto de partida e devem ser validados pela consultoria jurídica.
6. **Marca gov.br** – por ser protótipo, o app usa o padrão visual, mas não a marca/barra de identidade
   do governo, reservadas a serviços oficiais.
