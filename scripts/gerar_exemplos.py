"""Gera arquivos de exemplo para testar o app (todos FICTÍCIOS):

data/exemplos/documentos/   certidões e documentos em .txt (uma certidão vencida)
data/exemplos/pdfs/         plano_assinado.pdf (íntegro), plano_adulterado.pdf
                            (alterado após assinar) e oficio_sem_assinatura.pdf
data/exemplos/ac_teste.crt  AC raiz de TESTE. Copie para certs/ para ver a
                            assinatura passar a "confiável".

Uso:  python scripts/gerar_exemplos.py
"""
from __future__ import annotations

import datetime as dt
import io
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EX = RAIZ / "data" / "exemplos"


def documentos_txt():
    pasta = EX / "documentos"
    pasta.mkdir(parents=True, exist_ok=True)
    hoje = dt.date.today()
    valida = (hoje + dt.timedelta(days=120)).strftime("%d/%m/%Y")
    perto = (hoje + dt.timedelta(days=7)).strftime("%d/%m/%Y")
    vencida = (hoje - dt.timedelta(days=20)).strftime("%d/%m/%Y")
    arquivos = {
        "certidao_federal_rfb_pgfn.txt":
            "MINISTÉRIO DA FAZENDA – Receita Federal do Brasil / Procuradoria-Geral da Fazenda Nacional\n"
            "CERTIDÃO NEGATIVA DE DÉBITOS RELATIVOS AOS TRIBUTOS FEDERAIS E À DÍVIDA ATIVA DA UNIÃO\n"
            f"Nome: ASSOCIAÇÃO CULTURAL FICTÍCIA VIVA ARTE  CNPJ: 98.765.432/0001-98\nVálida até {valida}.\n",
        "crf_fgts.txt":
            "CAIXA ECONÔMICA FEDERAL – Certificado de Regularidade do FGTS – CRF\n"
            f"Inscrição: 98.765.432/0001-98\nValidade: {perto}\n",
        "cndt_justica_trabalho.txt":
            "PODER JUDICIÁRIO – JUSTIÇA DO TRABALHO\nCERTIDÃO NEGATIVA DE DÉBITOS TRABALHISTAS\n"
            f"CNPJ: 98.765.432/0001-98\nCertidão emitida em {vencida} – Válida até {vencida}\n",
        "estatuto_social_e_ata.txt":
            "ESTATUTO SOCIAL DA ASSOCIAÇÃO CULTURAL FICTÍCIA VIVA ARTE\nCapítulo I – Da denominação...\n"
            "ATA DE ELEIÇÃO E POSSE DA DIRETORIA – Assembleia Geral Ordinária.\n",
        "plano_de_trabalho_viva_arte.txt":
            "PLANO DE TRABALHO – Proposta EXEMPLO-002/2026\nMetas, etapas e cronograma de execução...\n",
        "oficio_encaminhamento.txt":
            "OFÍCIO Nº 12/2026 – Encaminhamento de proposta ao Ministério da Cultura.\n",
        "foto_fachada.txt": "IMG_2026_0001 (arquivo sem conteúdo textual)\n",
    }
    for nome, txt in arquivos.items():
        (pasta / nome).write_text(txt, encoding="utf-8")
    return pasta


def _pdf(linhas: list[str]) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4, pageCompression=0)
    y = 800
    for l in linhas:
        c.drawString(60, y, l)
        y -= 18
    c.save()
    return buf.getvalue()


def _ac_e_signatario():
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    agora = dt.datetime.now(dt.timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_nome = x509.Name([x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
                         x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AC TESTE AnalisaEmendas"),
                         x509.NameAttribute(NameOID.COMMON_NAME, "AC Raiz de TESTE - NAO USAR EM PRODUCAO")])
    ca = (x509.CertificateBuilder().subject_name(ca_nome).issuer_name(ca_nome)
          .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(agora - dt.timedelta(days=1)).not_valid_after(agora + dt.timedelta(days=3650))
          .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
          .add_extension(x509.KeyUsage(True, False, False, False, False, True, True, False, False), critical=True)
          .sign(ca_key, hashes.SHA256()))

    us_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    us_nome = x509.Name([x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
                         x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ICP-TESTE"),
                         x509.NameAttribute(NameOID.COMMON_NAME, "MARIA EXEMPLO DA SILVA:00000000191")])
    us = (x509.CertificateBuilder().subject_name(us_nome).issuer_name(ca_nome)
          .public_key(us_key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(agora - dt.timedelta(days=1)).not_valid_after(agora + dt.timedelta(days=730))
          .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
          .add_extension(x509.KeyUsage(True, True, False, False, False, False, False, False, False), critical=True)
          .sign(ca_key, hashes.SHA256()))

    def der(c):
        return c.public_bytes(serialization.Encoding.DER)

    chave = us_key.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8,
                                 serialization.NoEncryption())
    return der(ca), der(us), chave, ca.public_bytes(serialization.Encoding.PEM)


def pdfs():
    from asn1crypto import keys, x509 as ax509
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import signers
    from pyhanko_certvalidator.registry import SimpleCertificateStore

    pasta = EX / "pdfs"
    pasta.mkdir(parents=True, exist_ok=True)
    ca_der, us_der, chave_der, ca_pem = _ac_e_signatario()
    (EX / "ac_teste.crt").write_bytes(ca_pem)

    signer = signers.SimpleSigner(
        signing_cert=ax509.Certificate.load(us_der),
        signing_key=keys.PrivateKeyInfo.load(chave_der),
        cert_registry=SimpleCertificateStore.from_certs([ax509.Certificate.load(ca_der)]),
    )
    original = _pdf(["PLANO DE TRABALHO - EXEMPLO-001/2026 (FICTICIO)",
                     "Proponente: Municipio Exemplo de Ourilandia",
                     "Valor global: R$ 315.000,00", "Repasse: R$ 300.000,00",
                     "Assinado por: Maria Exemplo da Silva - Prefeita"])
    out = io.BytesIO()
    signers.sign_pdf(IncrementalPdfFileWriter(io.BytesIO(original)),
                     signers.PdfSignatureMetadata(field_name="AssinaturaPrefeita"),
                     signer=signer, output=out)
    assinado = out.getvalue()
    (pasta / "plano_assinado.pdf").write_bytes(assinado)

    # Adulteração do conteúdo assinado (mesmo nº de bytes): 315.000 -> 915.000
    adulterado = assinado.replace(b"R$ 315.000,00", b"R$ 915.000,00", 1)
    assert adulterado != assinado
    (pasta / "plano_adulterado.pdf").write_bytes(adulterado)

    (pasta / "oficio_sem_assinatura.pdf").write_bytes(
        _pdf(["OFICIO N. 12/2026 (FICTICIO)", "Sem assinatura digital - apenas imagem digitalizada"]))
    return pasta


if __name__ == "__main__":
    print("Documentos:", documentos_txt())
    print("PDFs:", pdfs())
