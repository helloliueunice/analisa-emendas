"""Testes do Banco de Projetos de Impacto (núcleo e telas)."""
import sys
from datetime import date
from pathlib import Path

from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core import banco as B  # noqa: E402


def _b():
    return B.estado_inicial()


def test_sementes_coerentes():
    b = _b()
    for p in b["projetos"]:
        if p["status"] == "certificado":
            assert B.avaliar(b, p)["certificavel"], p["id"]
    for i in b["indicacoes"]:
        if i["projeto_id"]:
            p = next(x for x in b["projetos"] if x["id"] == i["projeto_id"])
            assert p["status"] == "certificado"


def test_linhas_vermelhas():
    b = _b()
    p = dict(b["projetos"][0])
    p["elaborador"] = {"tipo": "consultoria", "nome": "X", "cnpj": "11.444.777/0001-61", "remuneracao": "exito",
                       "valor": 0}
    assert not B.avaliar(b, p)["elegivel"]
    p = dict(b["projetos"][0], representante_gov_br_ouro=False)
    assert not B.avaliar(b, p)["elegivel"]
    p = dict(b["projetos"][0], custo=10.0)
    assert not B.avaliar(b, p)["elegivel"]  # fora da faixa do programa


def test_necessidade_e_faixas():
    b = _b()
    prog = B.programa(b, "BIB")
    muns = b["municipios"].to_dict("records")
    sem = next(m for m in muns if m["tem_biblioteca"] == 0)
    com = next(m for m in muns if m["tem_biblioteca"] == 1)
    assert B.necessidade(sem, prog)[0] > B.necessidade(com, prog)[0]
    assert B.faixa(0.71) == "Alta" and B.faixa(0.6) == "Média" and B.faixa(0.2) == "Baixa"
    comp = {k: (1.0, "") for k in B.PESOS}
    assert B.pontuar(comp) == 1.0 and B.sensibilidade(comp)[0]


def test_sem_historico_e_neutro():
    b = _b()
    p = b["projetos"][0]
    m = dict(B.municipio(b, p["codigo_municipio"]), execucao_historica="")
    assert B.componentes(p, m, B.programa(b, p["programa"]))["E"][0] == 0.5


def test_custeio_nao_comprovado_zera_s_e_bloqueia_certificacao():
    b = _b()
    p = dict(b["projetos"][0], custeio_comprovado=False)
    a = B.avaliar(b, p)
    assert a["componentes"]["S"][0] == 0 and not a["certificavel"]


def test_alertas_e_painel():
    b = _b()
    tipos = {a["tipo"] for a in B.alertas(b)}
    assert "Consultoria recorrente" in tipos
    pn = B.painel(b)
    assert pn["dentro"] == 5 and pn["fora"] == 7 and pn["reconciliacao"] < 1


def test_periodo_eleitoral():
    assert B.periodo_eleitoral(date(2026, 8, 1))["vedado"]
    assert not B.periodo_eleitoral(date(2026, 10, 31))["vedado"]
    pe = B.periodo_eleitoral(date(2027, 3, 1))
    assert pe["eleicao"] == date(2028, 10, 1) and pe["inicio"] == date(2028, 7, 1)
    assert B.periodo_eleitoral(date(2028, 9, 1))["vedado"]


def test_registro_encadeado():
    b = _b()
    e1 = B.registrar(b, "a", "x", "P1")
    e2 = B.registrar(b, "b", "y", "P2")
    assert e1["hash"] != e2["hash"] and len(e2["hash"]) == 64


def _rodar(pagina):
    at = AppTest.from_file(str(RAIZ / "views" / pagina), default_timeout=90).run()
    assert not at.exception, at.exception
    return at


def test_telas_abrem():
    for p in ["banco_mapa.py", "banco_cadastro.py", "banco_curadoria.py", "banco_vitrine.py", "banco_painel.py"]:
        _rodar(p)


def test_fluxo_cadastro_curadoria_vitrine():
    at = _rodar("banco_cadastro.py")
    at.checkbox[0].check()  # comprova custeio
    n0 = len(at.session_state["banco"]["projetos"])
    next(b for b in at.button if "curadoria" in b.label.lower()).click().run()
    assert not at.exception, at.exception
    assert len(at.session_state["banco"]["projetos"]) == n0 + 1
    assert at.session_state["banco"]["registro"][-1]["acao"] == "cadastrou projeto"

    at = _rodar("banco_curadoria.py")
    certificar = next(b for b in at.button if b.label == "Certificar")
    if not certificar.disabled:
        certificar.click().run()
        assert not at.exception, at.exception
        assert at.session_state["banco"]["registro"][-1]["acao"] == "certificou"

    at = _rodar("banco_vitrine.py")
    assert any("Faixa" in m.value for m in at.markdown)
