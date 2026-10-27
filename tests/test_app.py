"""Teste de fumaça da interface: cada página abre e os botões principais rodam sem erro."""
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


def _rodar(pagina: str, clicar: bool = True) -> AppTest:
    at = AppTest.from_file(str(RAIZ / "views" / pagina), default_timeout=60).run()
    assert not at.exception, at.exception
    if clicar and at.button:
        at.button[0].click().run()
        assert not at.exception, at.exception
    return at


def test_paginas():
    _rodar("inicio.py", clicar=False)
    at = _rodar("plano_trabalho.py")
    assert any("PT-07" in e.label for e in at.expander)
    _rodar("documentos.py")
    _rodar("custos.py")
    _rodar("assinatura.py")
    _rodar("fila.py", clicar=False)


def test_app_principal():
    at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=60).run()
    assert not at.exception, at.exception
