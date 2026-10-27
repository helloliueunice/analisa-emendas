# Raízes de confiança

Coloque aqui os certificados (.crt, .cer, .pem ou .der) das cadeias aceitas pelo órgão:

- **ICP-Brasil** – repositório de certificados do ITI (cadeias v5, v10 etc.).
- **AC Raiz do Governo Federal do Brasil** – cadeia das assinaturas eletrônicas avançadas gov.br.

Baixe sempre das fontes oficiais (ITI e gov.br) e registre a data de atualização.

Para o teste do protótipo, copie `../data/exemplos/ac_teste.crt` para esta pasta: o PDF
`plano_assinado.pdf` passará a aparecer como **confiável**. Remova-o antes de usar em produção.
