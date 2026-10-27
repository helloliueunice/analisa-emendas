"""Formatação no padrão brasileiro."""


def brl(v, casas: int = 2) -> str:
    """1234.5 -> 'R$ 1.234,50'."""
    try:
        s = f"{float(v):,.{casas}f}"
    except (TypeError, ValueError):
        return "—"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")
