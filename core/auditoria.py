"""Trilha de auditoria: registra O QUÊ foi analisado (hash SHA-256 de cada
entrada), COM QUAL versão das regras (hash do código + YAML), QUANDO, POR
QUEM e QUAL foi o resultado. Permite reproduzir e contestar um parecer."""
from __future__ import annotations

import hashlib
import json
import platform
from datetime import datetime, timezone

from . import __version__
from .config import hash_regras, parametros
from .modelos import Achado, ResultadoModulo


def sha256(dados: bytes | str) -> str:
    if isinstance(dados, str):
        dados = dados.encode("utf-8")
    return hashlib.sha256(dados).hexdigest()


def registro(meta: dict, entradas: dict[str, str], resultados: list[ResultadoModulo],
             achados_ia: list[Achado] | None = None, provedor_ia: str = "") -> dict:
    agora = datetime.now(timezone.utc).astimezone()
    corpo = {
        "ferramenta": "AnalisaEmendas", "versao": __version__,
        "versao_parametros": parametros().get("versao"),
        "hash_regras_sha256": hash_regras(),
        "gerado_em": agora.isoformat(timespec="seconds"),
        "ambiente": f"Python {platform.python_version()}",
        "proposta": meta.get("proposta"), "proponente": meta.get("proponente"),
        "analista": meta.get("analista") or "(não informado)",
        "entradas_sha256": entradas,
        "modulos": [{
            "modulo": r.modulo, "indice_risco": r.nota_risco,
            "achados": [a.to_dict() for a in r.achados],
        } for r in resultados],
        "ia": {"provedor": provedor_ia or "não utilizada",
               "achados_sugeridos": [a.to_dict() for a in (achados_ia or [])]},
    }
    corpo["selo_sha256"] = sha256(json.dumps(corpo, ensure_ascii=False, sort_keys=True))
    return corpo


def verificar_selo(reg: dict) -> bool:
    """Confere se o registro não foi alterado depois de gerado."""
    copia = {k: v for k, v in reg.items() if k != "selo_sha256"}
    return sha256(json.dumps(copia, ensure_ascii=False, sort_keys=True)) == reg.get("selo_sha256")
