"""Acompanhamento da execução: confronta o executado com o plano de trabalho.

Entradas
  plano        dicionário do plano de trabalho (mesmo formato do módulo 1)
  pagamentos   DataFrame: data, fornecedor_cnpj, fornecedor_nome, nf_numero, valor, meta[, natureza_despesa]
  execucao     DataFrame: meta, quantidade_executada
  creditos     DataFrame opcional: data, valor (repasses creditados na conta específica)
  hoje         data de referência da análise

Regras ACO-01 a ACO-10: pagamentos fora da vigência, nota fiscal duplicada,
CNPJ de fornecedor inválido, pagamento sem meta correspondente, meta com
gasto acima do previsto, descompasso físico-financeiro, atraso de meta,
recursos parados na conta, indício de fracionamento e possível conflito de
interesse (fornecedor = proponente).
"""
from __future__ import annotations

import re
from datetime import date

import pandas as pd

from .config import p as _p
from .formato import brl
from .modelos import Achado, ResultadoModulo, Severidade
from .plano_trabalho import cnpj_valido

MOD = "Acompanhamento da Execução"
FUND = "Decreto 11.531/2023 e Portaria Conjunta 33/2023 (acompanhamento, movimentação e prestação de contas)"
FUND_OSC = "Lei 13.019/2014 (execução e monitoramento de parcerias com OSC)"


def _d(v) -> date | None:
    try:
        return pd.to_datetime(v).date()
    except Exception:
        return None


def _so_digitos(v) -> str:
    return re.sub(r"\D", "", str(v or ""))


def analisar_execucao(plano: dict, pagamentos: pd.DataFrame, execucao: pd.DataFrame,
                      creditos: pd.DataFrame | None = None, hoje: date | None = None) -> ResultadoModulo:
    hoje = hoje or date.today()
    res = ResultadoModulo(MOD)
    add = res.achados.append
    pag = pagamentos.copy()
    pag["valor"] = pd.to_numeric(pag["valor"], errors="coerce").fillna(0.0)
    pag["_data"] = pag["data"].map(_d)
    pag["meta"] = pd.to_numeric(pag["meta"], errors="coerce")
    vig = plano.get("vigencia") or {}
    ini, fim = _d(vig.get("inicio")), _d(vig.get("fim"))
    metas = {int(m["numero"]): m for m in plano.get("metas") or []}
    cnpj_prop = _so_digitos((plano.get("proponente") or {}).get("cnpj"))

    # ACO-01 pagamento fora da vigência
    for _, r in pag.iterrows():
        if r["_data"] and ini and fim and not (ini <= r["_data"] <= fim):
            add(Achado(MOD, "ACO-01 Pagamento fora da vigência", Severidade.CRITICA,
                       f"NF {r['nf_numero']} paga em {r['_data']:%d/%m/%Y}, fora da vigência "
                       f"({ini:%d/%m/%Y} a {fim:%d/%m/%Y}).",
                       "Glosar a despesa ou exigir devolução, salvo prorrogação formalizada.", FUND,
                       f"{r['fornecedor_nome']} – {brl(r['valor'])}"))

    # ACO-02 nota fiscal duplicada
    chave = pag["fornecedor_cnpj"].map(_so_digitos) + "|" + pag["nf_numero"].astype(str).str.strip()
    for k, grupo in pag[chave.duplicated(keep=False)].groupby(chave[chave.duplicated(keep=False)]):
        add(Achado(MOD, "ACO-02 Nota fiscal em duplicidade", Severidade.CRITICA,
                   f"NF {grupo['nf_numero'].iloc[0]} do fornecedor {grupo['fornecedor_nome'].iloc[0]} "
                   f"lançada {len(grupo)} vezes ({brl(grupo['valor'].sum())}).",
                   "Verificar pagamento em duplicidade e solicitar devolução.", FUND))

    # ACO-03 CNPJ inválido / ACO-10 fornecedor = proponente
    for _, r in pag.drop_duplicates("fornecedor_cnpj").iterrows():
        d = _so_digitos(r["fornecedor_cnpj"])
        if len(d) == 14 and not cnpj_valido(d):
            add(Achado(MOD, "ACO-03 CNPJ de fornecedor inválido", Severidade.ALTA,
                       f"Fornecedor {r['fornecedor_nome']} com CNPJ inválido ({r['fornecedor_cnpj']}).",
                       "Conferir a nota fiscal na Receita Federal / NF-e.", FUND))
        if cnpj_prop and d == cnpj_prop:
            add(Achado(MOD, "ACO-10 Fornecedor é o próprio proponente", Severidade.ALTA,
                       f"Pagamento a {r['fornecedor_nome']}, mesmo CNPJ do proponente.",
                       "Apurar autopagamento ou conflito de interesses; vedado sem previsão no plano.",
                       FUND_OSC))

    # ACO-04 pagamento sem meta
    for _, r in pag[~pag["meta"].isin(list(metas))].iterrows():
        add(Achado(MOD, "ACO-04 Despesa sem meta correspondente", Severidade.ALTA,
                   f"NF {r['nf_numero']} ({brl(r['valor'])}) vinculada à meta {r['meta']}, inexistente no plano.",
                   "Exigir vinculação a meta aprovada ou glosar.", FUND))

    # ACO-05/06/07 por meta
    exe = execucao.copy()
    exe["meta"] = pd.to_numeric(exe["meta"], errors="coerce")
    exe["quantidade_executada"] = pd.to_numeric(exe["quantidade_executada"], errors="coerce").fillna(0)
    exec_meta = exe.groupby("meta")["quantidade_executada"].sum().to_dict()
    gasto_meta = pag.groupby("meta")["valor"].sum().to_dict()
    limite_pp = _p("acompanhamento", "descompasso_fisico_financeiro_pp", 30)
    linhas = []
    for n, m in metas.items():
        prev_v, prev_q = float(m.get("valor") or 0), float(m.get("quantidade") or 0)
        gasto, feito = float(gasto_meta.get(n, 0)), float(exec_meta.get(n, 0))
        pf = gasto / prev_v * 100 if prev_v else 0
        pq = feito / prev_q * 100 if prev_q else 0
        if prev_v and gasto > prev_v + 0.01:
            add(Achado(MOD, "ACO-05 Gasto acima do previsto", Severidade.ALTA,
                       f"Meta {n}: gasto {brl(gasto)} supera o previsto ({brl(prev_v)}).",
                       "Exigir reformulação aprovada do plano ou glosar o excedente.", FUND))
        if prev_q and pf - pq > limite_pp:
            add(Achado(MOD, "ACO-06 Descompasso físico-financeiro", Severidade.ALTA,
                       f"Meta {n}: {pf:.0f}% do recurso gasto para {pq:.0f}% da execução física.",
                       "Solicitar justificativa e comprovação da execução física (fotos, listas, relatórios).",
                       FUND))
        fim_meta = max((_d(e.get("fim")) for e in m.get("etapas") or [] if _d(e.get("fim"))), default=None)
        if fim_meta and fim_meta < hoje and pq < 100:
            add(Achado(MOD, "ACO-07 Meta em atraso", Severidade.MEDIA,
                       f"Meta {n}: prazo encerrado em {fim_meta:%d/%m/%Y} com {pq:.0f}% executado.",
                       "Notificar o convenente; avaliar reprogramação ou medidas de saneamento.", FUND))
        linhas.append({"Meta": n, "Descrição": m.get("descricao"), "Previsto (R$)": prev_v, "Gasto (R$)": gasto,
                       "% financeiro": pf, "Qtd. prevista": prev_q, "Qtd. executada": feito,
                       "% físico": pq, "Descompasso (pp)": pf - pq})

    # ACO-08 recursos parados
    if creditos is not None and not creditos.empty:
        cred = creditos.copy()
        cred["_data"] = cred["data"].map(_d)
        ultimo_pag = max((d for d in pag["_data"] if d), default=None)
        prim_cred = min((d for d in cred["_data"] if d), default=None)
        saldo = float(pd.to_numeric(cred["valor"], errors="coerce").sum()) - float(pag["valor"].sum())
        ref = ultimo_pag or prim_cred
        dias = (hoje - ref).days if ref else 0
        if saldo > 0 and dias > _p("acompanhamento", "dias_recurso_parado", 180):
            add(Achado(MOD, "ACO-08 Recursos parados", Severidade.MEDIA,
                       f"Saldo de {brl(saldo)} sem movimentação há {dias} dias.",
                       "Verificar aplicação financeira obrigatória e risco de devolução/inexecução.", FUND))

    # ACO-09 fracionamento
    qmin = _p("acompanhamento", "fracionamento_qtd_minima", 3)
    vmax = _p("acompanhamento", "fracionamento_valor_maximo", 10000.0)
    pequenas = pag[pag["valor"] < vmax]
    for cnpj, g in pequenas.groupby(pequenas["fornecedor_cnpj"].map(_so_digitos)):
        if len(g) >= qmin and g["valor"].sum() >= vmax:
            add(Achado(MOD, "ACO-09 Indício de fracionamento", Severidade.MEDIA,
                       f"{g['fornecedor_nome'].iloc[0]}: {len(g)} notas abaixo de {brl(vmax, 0)}, "
                       f"somando {brl(g['valor'].sum())}.",
                       "Verificar se houve fracionamento para fugir de procedimento de seleção/cotação.", FUND))

    total_plano = float(plano.get("valor_global") or 0)
    total_pago = float(pag["valor"].sum())
    res.resumo = {"tabela": pd.DataFrame(linhas), "total_pago": total_pago, "total_plano": total_plano,
                  "perc_financeiro": total_pago / total_plano * 100 if total_plano else 0,
                  "n_pagamentos": len(pag)}
    return res
