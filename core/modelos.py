"""Estruturas de dados comuns: achados de análise e severidade."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class Severidade(str, Enum):
    CRITICA = "Crítica"      # impede aprovação
    ALTA = "Alta"            # exige diligência
    MEDIA = "Média"          # recomenda ajuste
    INFO = "Informativa"     # registro / boa prática

    @property
    def peso(self) -> int:
        return {"Crítica": 40, "Alta": 15, "Média": 5, "Informativa": 0}[self.value]


@dataclass
class Achado:
    modulo: str
    regra: str
    severidade: Severidade
    mensagem: str
    recomendacao: str = ""
    fundamento: str = ""
    evidencia: str = ""
    origem: str = "regra"   # "regra" (determinístico) ou "ia" (modelo de linguagem)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["severidade"] = self.severidade.value
        return d


@dataclass
class ResultadoModulo:
    modulo: str
    achados: list[Achado] = field(default_factory=list)
    resumo: dict = field(default_factory=dict)

    @property
    def nota_risco(self) -> int:
        """0 (sem risco aparente) a 100 (risco máximo)."""
        return min(100, sum(a.severidade.peso for a in self.achados))

    @property
    def tem_impeditivo(self) -> bool:
        return any(a.severidade == Severidade.CRITICA for a in self.achados)
