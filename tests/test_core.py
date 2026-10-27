import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
EX = RAIZ / "data" / "exemplos"

from core.custos import analisar_custos  # noqa: E402
from core.documentos import analisar_documentos, extrair_validade  # noqa: E402
from core.llm import pseudonimizar  # noqa: E402
from core.modelos import Severidade  # noqa: E402
from core.parecer import gerar_docx, gerar_markdown  # noqa: E402
from core.plano_trabalho import analisar_plano, cnpj_valido  # noqa: E402


def _plano(nome):
    return json.loads((EX / nome).read_text(encoding="utf-8"))


def _regras(res):
    return {a.regra.split()[0] for a in res.achados}


def test_cnpj():
    assert cnpj_valido("12.345.678/0001-95")
    assert not cnpj_valido("98.765.432/0001-00")
    assert not cnpj_valido("11111111111111")


def test_plano_adequado_sem_impeditivos():
    res = analisar_plano(_plano("plano_trabalho_adequado.json"))
    assert not res.tem_impeditivo, [a.mensagem for a in res.achados]
    assert res.nota_risco <= 15


def test_plano_com_problemas():
    res = analisar_plano(_plano("plano_trabalho_com_problemas.json"))
    esperadas = {"PT-02", "PT-04", "PT-05", "PT-23", "PT-07", "PT-08", "PT-10", "PT-15", "PT-16", "PT-18", "PT-21"}
    assert esperadas <= _regras(res), _regras(res)
    assert res.tem_impeditivo


def test_plano_vazio():
    res = analisar_plano({})
    assert sum(a.regra.startswith("PT-01") for a in res.achados) >= 8


def test_validade_certidao():
    assert extrair_validade("Válida até 31/12/2026.") == date(2026, 12, 31)
    assert extrair_validade("sem data") is None


def test_documentos():
    hoje = date.today()
    venc = (hoje - timedelta(days=3)).strftime("%d/%m/%Y")
    arquivos = [
        {"nome": "plano_de_trabalho.pdf", "texto": "Plano de trabalho com metas"},
        {"nome": "cndt.pdf", "texto": f"Certidão negativa de débitos trabalhistas. Válida até {venc}"},
    ]
    res = analisar_documentos(arquivos, "osc", hoje=hoje)
    regras = _regras(res)
    assert "DOC-03" in regras  # vencida
    assert "DOC-01" in regras  # faltam obrigatórios


def test_custos():
    orc = pd.read_csv(EX / "orcamento_proposta.csv")
    ref = pd.read_csv(EX / "precos_referencia.csv")
    res = analisar_custos(orc, ref, 0.20)
    tab = res.resumo["tabela"]
    sobre = set(tab.loc[tab["Situação"] == "Indício de sobrepreço", "Item"])
    assert {1, 3, 6} <= sobre, tab[["Item", "Situação", "Desvio"]]
    assert 8 in set(tab.loc[tab["Situação"] == "Sem referência", "Item"])  # drone
    assert res.resumo["excesso_estimado"] > 0


def test_assinatura():
    from asn1crypto import pem, x509

    from core.assinatura import verificar_pdf

    pdfs = EX / "pdfs"
    ok = verificar_pdf((pdfs / "plano_assinado.pdf").read_bytes(), raizes=[])
    assert ok.resumo["assinaturas"][0]["Íntegra"] == "Sim"
    assert "ASS-05" in _regras(ok)  # sem raiz -> não confiável

    _, _, der = pem.unarmor((EX / "ac_teste.crt").read_bytes())
    conf = verificar_pdf((pdfs / "plano_assinado.pdf").read_bytes(), raizes=[x509.Certificate.load(der)])
    assert not conf.achados

    adult = verificar_pdf((pdfs / "plano_adulterado.pdf").read_bytes(), raizes=[])
    assert "ASS-03" in _regras(adult)

    sem = verificar_pdf((pdfs / "oficio_sem_assinatura.pdf").read_bytes(), raizes=[])
    assert "ASS-01" in _regras(sem)


def test_parecer_e_lgpd():
    res = analisar_plano(_plano("plano_trabalho_com_problemas.json"))
    md = gerar_markdown({"proposta": "X"}, [res])
    assert "NÃO APTO" in md
    assert gerar_docx(md)[:2] == b"PK"
    assert "[CPF]" in pseudonimizar("CPF 123.456.789-09")
    assert Severidade.CRITICA.peso > Severidade.ALTA.peso


def test_acompanhamento():
    from core.acompanhamento import analisar_execucao

    r = analisar_execucao(_plano("plano_trabalho_adequado.json"), pd.read_csv(EX / "execucao_pagamentos.csv"),
                          pd.read_csv(EX / "execucao_fisica.csv"), pd.read_csv(EX / "execucao_creditos.csv"),
                          hoje=date(2027, 12, 15))
    assert {"ACO-01", "ACO-02", "ACO-03", "ACO-04", "ACO-06", "ACO-07", "ACO-09", "ACO-10"} <= _regras(r)


def test_cruzamentos():
    docs = [{"nome": "cnd_federal.txt", "texto": "Receita Federal certidão negativa CNPJ: 11.444.777/0001-61 "
                                                 "Válida até 31/12/2099"}]
    r = analisar_documentos(docs, "osc", cnpj_proponente="12.345.678/0001-95")
    assert "DOC-06" in _regras(r)
    orc = pd.read_csv(EX / "orcamento_proposta.csv")
    ref = pd.read_csv(EX / "precos_referencia.csv")
    assert "CUS-06" in _regras(analisar_custos(orc, ref, valor_plano=1_000_000))


def test_auditoria():
    from core.auditoria import registro, verificar_selo

    res = analisar_plano(_plano("plano_trabalho_adequado.json"))
    reg = registro({"proposta": "X"}, {"plano": "abc"}, [res])
    assert verificar_selo(reg)
    reg["analista"] = "adulterado"
    assert not verificar_selo(reg)


def test_guardrails_ia():
    from core.llm import validar_achados_ia

    out = validar_achados_ia([
        {"regra": "IA-1", "severidade": "Crítica", "mensagem": "m", "evidencia": "Apoio a ações"},
        {"regra": "IA-2", "severidade": "Alta", "mensagem": "m", "evidencia": "texto inventado"},
        {"regra": "IA-3", "severidade": "Alta", "mensagem": ""},
    ], "Objeto: Apoio a  ações culturais")
    assert [a.severidade for a in out] == [Severidade.ALTA, Severidade.INFO]


def test_qualidade_regras():
    from core.avaliacao import avaliar, gerar_base

    for val in (False, True):
        m, _ = avaliar(gerar_base(200, validacao=val))
        assert m["FP"].sum() == 0 and m["FN"].sum() == 0, m
