"""Verificação de assinaturas digitais em PDF (PAdES) com pyHanko.

O que é verificado, para cada assinatura embutida no PDF:
  * integridade criptográfica (o conteúdo assinado não foi alterado);
  * se o documento foi modificado DEPOIS da assinatura (cobertura/diff);
  * cadeia de confiança: o certificado do signatário encadeia até uma raiz
    confiável carregada em `certs/` (ICP-Brasil e/ou AC Raiz do Gov. Federal,
    usada nas assinaturas gov.br);
  * dados do signatário (nome, CPF/CNPJ quando presente no certificado),
    data declarada e validade do certificado.

Importante: sem as raízes carregadas, a assinatura pode estar ÍNTEGRA mas
"não confiável". Para validação oficial, o resultado deve ser confrontado com
o Verificador de Conformidade do ITI (validar.iti.gov.br).
"""
from __future__ import annotations

import io
import logging
import re
from pathlib import Path

from .modelos import Achado, ResultadoModulo, Severidade

MOD = "Assinatura Digital"
RAIZ = Path(__file__).resolve().parent.parent
PASTA_CERTS = RAIZ / "certs"
logging.getLogger("pyhanko").setLevel(logging.CRITICAL)
logging.getLogger("pyhanko_certvalidator").setLevel(logging.CRITICAL)

FUND = "MP 2.200-2/2001 (ICP-Brasil); Lei 14.063/2020 (assinaturas eletrônicas no setor público)"


def carregar_raizes(pasta: Path = PASTA_CERTS):
    from asn1crypto import pem, x509

    raizes = []
    if not pasta.exists():
        return raizes
    for arq in sorted(pasta.iterdir()):
        if arq.suffix.lower() not in {".crt", ".cer", ".pem", ".der"}:
            continue
        dados = arq.read_bytes()
        try:
            if pem.detect(dados):
                for _, _, der in pem.unarmor(dados, multiple=True):
                    raizes.append(x509.Certificate.load(der))
            else:
                raizes.append(x509.Certificate.load(dados))
        except Exception:
            continue
    return raizes


def _id_titular(cert) -> str:
    """ICP-Brasil costuma trazer 'NOME:CPF' no CN."""
    cn = cert.subject.native.get("common_name", "")
    m = re.search(r":(\d{11}|\d{14})$", cn)
    return m.group(1) if m else ""


def verificar_pdf(dados: bytes, nome: str = "documento.pdf", raizes=None,
                  permitir_rede: bool = False) -> ResultadoModulo:
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import validate_pdf_signature
    from pyhanko_certvalidator import ValidationContext

    res = ResultadoModulo(MOD)
    raizes = carregar_raizes() if raizes is None else raizes
    try:
        leitor = PdfFileReader(io.BytesIO(dados), strict=False)
    except Exception as exc:
        res.achados.append(Achado(MOD, "ASS-00 PDF ilegível", Severidade.CRITICA,
                                  f"{nome}: não foi possível abrir o PDF ({exc}).", "Solicitar novo arquivo."))
        return res

    assinaturas = list(leitor.embedded_signatures)
    if not assinaturas:
        res.achados.append(Achado(MOD, "ASS-01 Sem assinatura", Severidade.ALTA,
                                  f"{nome}: nenhuma assinatura digital embutida encontrada.",
                                  "Se assinado em papel/imagem, exigir assinatura eletrônica qualificada "
                                  "(ICP-Brasil) ou avançada (gov.br), conforme exigência do ato.", FUND))
        res.resumo = {"assinaturas": []}
        return res

    vc = ValidationContext(trust_roots=raizes, allow_fetching=permitir_rede)
    linhas = []
    for sig in assinaturas:
        campo = sig.field_name
        try:
            st = validate_pdf_signature(sig, vc)
        except Exception as exc:
            res.achados.append(Achado(MOD, "ASS-02 Erro de validação", Severidade.ALTA,
                                      f"{nome} / {campo}: erro ao validar ({exc}).",
                                      "Validar no verificador do ITI.", FUND))
            continue
        cert = st.signing_cert
        titular = cert.subject.native.get("common_name") or cert.subject.human_friendly
        emissor = cert.issuer.native.get("common_name") or cert.issuer.human_friendly
        validade_cert = cert["tbs_certificate"]["validity"]
        nao_antes = validade_cert["not_before"].native
        nao_depois = validade_cert["not_after"].native
        cobertura = getattr(st.coverage, "name", str(st.coverage))
        modificacao = getattr(st.modification_level, "name", str(st.modification_level))

        if not st.intact or not st.valid:
            res.achados.append(Achado(MOD, "ASS-03 Assinatura inválida", Severidade.CRITICA,
                                      f"{nome} / {campo}: assinatura criptograficamente INVÁLIDA "
                                      "(documento alterado ou assinatura corrompida).",
                                      "Rejeitar o documento e solicitar nova via assinada.", FUND, titular))
        if cobertura != "ENTIRE_FILE":
            sev = Severidade.ALTA if modificacao not in ("NONE", "LTA_UPDATES", "FORM_FILLING") else Severidade.MEDIA
            res.achados.append(Achado(MOD, "ASS-04 Alteração após assinatura", sev,
                                      f"{nome} / {campo}: o arquivo recebeu acréscimos após esta assinatura "
                                      f"(cobertura={cobertura}, nível={modificacao}).",
                                      "Normal quando há várias assinaturas; caso contrário, verificar o que foi "
                                      "alterado.", FUND))
        if not st.trusted:
            res.achados.append(Achado(MOD, "ASS-05 Cadeia não confiável", Severidade.ALTA,
                                      f"{nome} / {campo}: certificado de '{titular}' não encadeia até uma raiz "
                                      "confiável carregada.",
                                      "Carregar as raízes ICP-Brasil/Gov.br em certs/ ou validar em "
                                      "validar.iti.gov.br.", FUND, f"Emissor: {emissor}"))
        if st.signer_reported_dt and not (nao_antes <= st.signer_reported_dt <= nao_depois):
            res.achados.append(Achado(MOD, "ASS-06 Certificado fora da validade", Severidade.CRITICA,
                                      f"{nome} / {campo}: data da assinatura fora da validade do certificado.",
                                      "Rejeitar assinatura.", FUND))
        linhas.append({
            "Arquivo": nome, "Campo": campo, "Signatário": titular, "CPF/CNPJ (cert.)": _id_titular(cert),
            "Emissor": emissor,
            "Data declarada": st.signer_reported_dt.strftime("%d/%m/%Y %H:%M") if st.signer_reported_dt else "—",
            "Íntegra": "Sim" if (st.intact and st.valid) else "NÃO",
            "Confiável (cadeia)": "Sim" if st.trusted else "Não",
            "Carimbo do tempo": "Sim" if st.timestamp_validity else "Não",
            "Cobertura": cobertura,
            "Validade do certificado": f"{nao_antes:%d/%m/%Y} a {nao_depois:%d/%m/%Y}",
        })
    res.resumo = {"assinaturas": linhas, "n_raizes": len(raizes)}
    return res


def conferir_signatarios(linhas: list[dict], esperados: list[str]) -> list[Achado]:
    """Confere se os signatários esperados (ex.: prefeito, presidente da OSC)
    aparecem entre os certificados. Comparação por nome normalizado ou CPF."""
    import unicodedata

    def n(s):
        s = unicodedata.normalize("NFKD", s.upper())
        return "".join(c for c in s if not unicodedata.combining(c))

    achados = []
    presentes = " ".join(n(l["Signatário"]) + " " + l["CPF/CNPJ (cert.)"] for l in linhas)
    for e in esperados:
        if e.strip() and n(e.strip()) not in presentes:
            achados.append(Achado(MOD, "ASS-07 Signatário esperado ausente", Severidade.ALTA,
                                  f"Não foi encontrada assinatura de '{e.strip()}'.",
                                  "Verificar competência de quem assinou (representante legal/delegação).",
                                  FUND))
    return achados
