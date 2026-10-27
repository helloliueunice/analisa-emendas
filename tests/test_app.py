"""Teste de fumaça da interface: cada página abre e o botão principal roda sem erro."""
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


def _rodar(pagina: str, clicar: bool = True) -> AppTest:
    at = AppTest.from_file(str(RAIZ / "views" / pagina), default_timeout=90).run()
    assert not at.exception, at.exception
    if clicar:
        prim = [b for b in at.button if getattr(b, "type", "") == "primary"] or list(at.button)
        prim[0].click().run()
        assert not at.exception, at.exception
    return at


def _texto(at) -> str:
    return " ".join(m.value for m in at.markdown)


def test_paginas():
    _rodar("inicio.py", clicar=False)
    assert "PT-07" in _texto(_rodar("plano_trabalho.py"))
    assert "DOC-03" in _texto(_rodar("documentos.py"))
    assert "CUS-01" in _texto(_rodar("custos.py"))
    assert "ASS-03" in _texto(_rodar("assinatura.py"))
    assert "ACO-02" in _texto(_rodar("acompanhamento.py"))
    _rodar("parecer.py", clicar=False)
    _rodar("fila.py", clicar=False)
    _rodar("qualidade.py", clicar=False)
    _rodar("sobre.py", clicar=False)


def test_app_principal():
    at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=90).run()
    assert not at.exception, at.exception
