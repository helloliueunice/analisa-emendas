"""Verificação de custos: compara o orçamento do proponente com uma tabela de
preços de referência (ex.: Painel de Preços, SINAPI, SICRO, contratações
anteriores do órgão) e aponta indícios de sobrepreço.

Orçamento (CSV): item, descricao, unidade, quantidade, valor_unitario[, codigo_ref]
Referência (CSV): codigo, descricao, unidade, preco_referencia[, fonte, data_base]
"""
from __future__ import annotations

import difflib
import unicodedata

import pandas as pd

from .modelos import Achado, ResultadoModulo, Severidade

MOD = "Verificação de Custos"
FUND = "Lei 14.133/2021, art. 23 (parâmetros de pesquisa de preços) e IN SEGES/ME 65/2021"


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s).lower())
    return " ".join("".join(c for c in s if not unicodedata.combining(c)).split())


def _casar(desc: str, ref: pd.DataFrame, limiar: float) -> tuple[int | None, float]:
    alvo = _norm(desc)
    melhor, idx = 0.0, None
    for i, d in zip(ref.index, ref["_desc_n"]):
        r = difflib.SequenceMatcher(None, alvo, d).ratio()
        if r > melhor:
            melhor, idx = r, i
    return (idx, melhor) if melhor >= limiar else (None, melhor)


def analisar_custos(orc: pd.DataFrame, ref: pd.DataFrame, limite_sobrepreco: float = 0.20,
                    limiar_similaridade: float = 0.6) -> ResultadoModulo:
    res = ResultadoModulo(MOD)
    orc = orc.copy()
    ref = ref.copy()
    ref["_desc_n"] = ref["descricao"].map(_norm)
    ref_por_cod = {str(c).strip(): i for i, c in zip(ref.index, ref.get("codigo", pd.Series(dtype=str)))}

    for col in ("quantidade", "valor_unitario"):
        orc[col] = pd.to_numeric(orc[col], errors="coerce").fillna(0.0)
    orc["valor_total"] = orc["quantidade"] * orc["valor_unitario"]

    saida = []
    for _, lin in orc.iterrows():
        idx, sim, metodo = None, 1.0, "código"
        cod = str(lin.get("codigo_ref", "") or "").strip()
        if cod and cod.lower() != "nan" and cod in ref_por_cod:
            idx = ref_por_cod[cod]
        else:
            idx, sim = _casar(lin["descricao"], ref, limiar_similaridade)
            metodo = "similaridade" if idx is not None else "—"

        preco_ref = float(ref.loc[idx, "preco_referencia"]) if idx is not None else None
        desvio = (lin["valor_unitario"] / preco_ref - 1) if preco_ref else None
        situacao = "Sem referência"
        if desvio is not None:
            if desvio > limite_sobrepreco:
                situacao = "Indício de sobrepreço"
                sev = Severidade.ALTA if desvio > 2 * limite_sobrepreco else Severidade.MEDIA
                res.achados.append(Achado(
                    MOD, "CUS-01 Sobrepreço", sev,
                    f"Item {lin['item']} – '{lin['descricao']}': R$ {lin['valor_unitario']:,.2f} está "
                    f"{desvio:+.0%} acima da referência (R$ {preco_ref:,.2f}).",
                    "Solicitar justificativa ou ao menos 3 cotações; ajustar ao preço de referência.",
                    FUND, f"Ref.: {ref.loc[idx, 'descricao']} ({ref.loc[idx].get('fonte', 'referência')})"))
            elif desvio < -0.5:
                situacao = "Preço muito abaixo (inexequível?)"
                res.achados.append(Achado(
                    MOD, "CUS-02 Possível inexequibilidade", Severidade.INFO,
                    f"Item {lin['item']}: {desvio:+.0%} em relação à referência.",
                    "Verificar se a especificação corresponde ao item de referência.", FUND))
            else:
                situacao = "Compatível"
            if idx is not None and _norm(ref.loc[idx, "unidade"]) != _norm(lin["unidade"]):
                res.achados.append(Achado(
                    MOD, "CUS-03 Unidade divergente", Severidade.MEDIA,
                    f"Item {lin['item']}: unidade '{lin['unidade']}' ≠ referência '{ref.loc[idx, 'unidade']}'.",
                    "Conferir unidade antes de concluir sobre o preço.", FUND))
        else:
            res.achados.append(Achado(
                MOD, "CUS-04 Item sem referência", Severidade.INFO,
                f"Item {lin['item']} – '{lin['descricao']}' sem preço de referência correspondente.",
                "Exigir pesquisa de preços específica (cotações/Painel de Preços).", FUND))

        saida.append({
            "Item": lin["item"], "Descrição": lin["descricao"], "Unid.": lin["unidade"],
            "Qtd.": lin["quantidade"], "Unitário proposto": lin["valor_unitario"],
            "Total proposto": lin["valor_total"],
            "Referência": ref.loc[idx, "descricao"] if idx is not None else "—",
            "Preço ref.": preco_ref, "Desvio": desvio, "Casamento": metodo,
            "Similaridade": round(sim, 2), "Situação": situacao,
        })

    tab = pd.DataFrame(saida)
    excesso = 0.0
    if not tab.empty:
        m = tab["Situação"] == "Indício de sobrepreço"
        excesso = float(((tab.loc[m, "Unitário proposto"] - tab.loc[m, "Preço ref."]) * tab.loc[m, "Qtd."]).sum())
        # concentração: um item com mais de 50% do valor merece atenção
        total = tab["Total proposto"].sum()
        if total:
            top = tab.loc[tab["Total proposto"].idxmax()]
            if top["Total proposto"] / total > 0.5 and len(tab) > 1:
                res.achados.append(Achado(
                    MOD, "CUS-05 Concentração", Severidade.INFO,
                    f"Item {top['Item']} concentra {top['Total proposto'] / total:.0%} do orçamento.",
                    "Priorizar a conferência de especificação e preço deste item (curva ABC)."))
    res.resumo = {"tabela": tab, "total_proposto": float(tab["Total proposto"].sum()) if not tab.empty else 0.0,
                  "excesso_estimado": excesso}
    return res
