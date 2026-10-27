"""Carrega parâmetros e calcula o hash das regras para a trilha de auditoria."""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
PARAMS = RAIZ / "config" / "parametros.yaml"


@lru_cache(maxsize=1)
def parametros() -> dict:
    with open(PARAMS, encoding="utf-8") as f:
        return yaml.safe_load(f)


def p(secao: str, chave: str, padrao=None):
    return parametros().get(secao, {}).get(chave, padrao)


def hash_regras() -> str:
    """SHA-256 do código das regras + configurações: identifica exatamente
    qual versão da lógica produziu um parecer."""
    h = hashlib.sha256()
    arquivos = sorted((RAIZ / "core").glob("*.py")) + sorted((RAIZ / "config").glob("*.yaml"))
    for a in arquivos:
        h.update(a.name.encode())
        h.update(a.read_bytes())
    return h.hexdigest()
