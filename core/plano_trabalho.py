"""Análise determinística de Plano de Trabalho.

Entrada: dicionário no formato de `data/exemplos/plano_trabalho_*.json`
(espelha os campos principais do Plano de Trabalho do Transferegov.br).
Saída: `ResultadoModulo` com achados classificados por severidade.

As regras aqui são *verificáveis e auditáveis*: cada achado diz qual regra
disparou e qual evidência usou. A IA generativa (core/llm.py) é usada apenas
como camada complementar, para aspectos qualitativos (nexo causal, clareza).
"""
from __future__ import annotations

import re
from datetime import date

from .config import p as _p
from .modelos import Achado, ResultadoModulo, Severidade

MOD = "Plano de Trabalho"
TOL = _p("plano_trabalho", "tolerancia_centavos", 0.01)
OBJ_MIN = _p("plano_trabalho", "objeto_min_caracteres", 40)
JUST_MIN = _p("plano_trabalho", "justificativa_min_caracteres", 300)

FUND_PT = "Decreto 11.531/2023 e Portaria Conjunta MGI/MF/CGU 33/2023 (conteúdo do plano de trabalho)"
FUND_LC210 = "LC 210/2024 (vinculação do objeto à finalidade/funcional da emenda)"

CAMPOS_OBRIGATORIOS = {
    "objeto": "Objeto",
    "justificativa": "Justificativa",
    "proponente": "Proponente",
    "vigencia": "Vigência",
    "valor_global": "Valor global",
    "valor_repasse": "Valor de repasse",
    "metas": "Metas",
    "cronograma_desembolso": "Cronograma de desembolso",
    "plano_aplicacao": "Plano de aplicação detalhado",
    "funcao_subfuncao": "Função/Subfunção (finalidade)",
}

TERMOS_GENERICOS = [
    "diversos", "diversas", "outros", "etc", "apoio a", "apoio ao", "ações diversas",
    "material de consumo em geral", "a definir", "conforme necessidade",
]

# Elementos essenciais da justificativa (radicais, para tolerar variações de redação).
# Calibrado na base sintética de core/avaliacao.py; recalibrar com amostra real rotulada.
ELEMENTOS_JUSTIFICATIVA = {
    "problema/diagnóstico": ["problema", "diagnóstic", "carênc", "demanda", "déficit", "necessidad", "falta",
                             "ausênc", "não possui", "não há", "sem acesso", "interditad", "risco", "precári",
                             "raramente", "escass", "insuficien", "levantamento"],
    "público-alvo": ["público", "beneficiári", "atendid", "populaç", "famílias", "alunos", "estudantes",
                     "artistas", "pessoas", "comunidade", "jovens", "crianças", "idosos", "espectador",
                     "grupos", "mestres", "moradores", "escolas"],
    "resultados esperados": ["resultado", "impacto", "benefíci", "melhori", "ampli", "espera-se", "estima-se",
                             "pretende-se", "permitirá", "possibilit", "gerar", "retomar", "reabertura",
                             "aproxim", "fortalec", "garantir"],
}
# Alinhamento explícito à política pública: recomendado, não impeditivo (regra informativa PT-22).
TERMOS_POLITICA = ["política", "programa", "plano nacional", "plano municipal", "plano estadual", "pnc", "ppa",
                   "lei ", "sistema nacional", "meta do", "metas do"]


# ----------------------------------------------------------------- utilidades
def _num(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _data(v) -> date | None:
    if not v:
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def _brl(v: float) -> str:
    s = f"{v:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def cnpj_valido(cnpj: str) -> bool:
    """Valida os dígitos verificadores do CNPJ (numérico)."""
    d = re.sub(r"\D", "", str(cnpj or ""))
    if len(d) != 14 or d == d[0] * 14:
        return False

    def dv(base: str) -> str:
        pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2][-len(base):]
        soma = sum(int(x) * p for x, p in zip(base, pesos))
        r = soma % 11
        return "0" if r < 2 else str(11 - r)

    return d[12] == dv(d[:12]) and d[13] == dv(d[:13])


# --------------------------------------------------------------------- análise
def analisar_plano(pt: dict) -> ResultadoModulo:
    res = ResultadoModulo(MOD)
    add = res.achados.append

    # 1. Completude --------------------------------------------------------
    faltantes = [rot for k, rot in CAMPOS_OBRIGATORIOS.items() if not pt.get(k)]
    for rot in faltantes:
        add(Achado(MOD, "PT-01 Completude", Severidade.CRITICA,
                   f"Campo obrigatório ausente ou vazio: {rot}.",
                   "Solicitar complementação do plano de trabalho ao proponente.", FUND_PT))

    # 2. Proponente ----------------------------------------------------------
    prop = pt.get("proponente") or {}
    if prop and not cnpj_valido(prop.get("cnpj", "")):
        add(Achado(MOD, "PT-02 CNPJ", Severidade.CRITICA,
                   f"CNPJ do proponente inválido: {prop.get('cnpj')!r}.",
                   "Conferir o CNPJ no cadastro do Transferegov.br/Receita Federal.",
                   evidencia=str(prop.get("cnpj"))))

    # 3. Objeto ---------------------------------------------------------------
    objeto = str(pt.get("objeto") or "")
    if objeto:
        obj_l = objeto.lower()
        if len(objeto) < OBJ_MIN:
            add(Achado(MOD, "PT-03 Objeto sucinto", Severidade.ALTA,
                       f"Objeto com apenas {len(objeto)} caracteres; pode não permitir aferir o que será entregue.",
                       "Pedir descrição com o quê, quanto, onde e para quem.", FUND_PT, objeto))
        genericos = [t for t in TERMOS_GENERICOS if re.search(rf"\b{re.escape(t)}\b", obj_l)]
        if genericos:
            add(Achado(MOD, "PT-04 Objeto genérico", Severidade.ALTA,
                       f"Objeto contém termos genéricos: {', '.join(genericos)}.",
                       "Exigir objeto certo e determinado, vedada descrição genérica.", FUND_PT, objeto))

    # 4. Justificativa -------------------------------------------------------
    just = str(pt.get("justificativa") or "")
    if just:
        jl = just.lower()
        if len(just) < JUST_MIN:
            add(Achado(MOD, "PT-05 Justificativa curta", Severidade.MEDIA,
                       f"Justificativa com {len(just)} caracteres (referência mínima sugerida: {JUST_MIN}).",
                       "Solicitar diagnóstico, público-alvo e resultados esperados.", FUND_PT))
        ausentes = [nome for nome, termos in ELEMENTOS_JUSTIFICATIVA.items()
                    if not any(t in jl for t in termos)]
        # A heurística lexical NÃO generalizou no conjunto de validação (ver AVALIACAO.md): só é
        # impeditiva/alta quando nenhum elemento é reconhecível. O sinal parcial vira nota
        # informativa (PT-23), que não altera a conclusão e pede juízo semântico (IA ou analista).
        if len(ausentes) == len(ELEMENTOS_JUSTIFICATIVA):
            add(Achado(MOD, "PT-06 Elementos da justificativa", Severidade.ALTA,
                       "A justificativa não evidencia problema, público-alvo nem resultados esperados.",
                       "Diligenciar o proponente para demonstrar nexo entre problema, objeto e resultados.",
                       FUND_PT))
        elif len(ausentes) >= 2:
            add(Achado(MOD, "PT-23 Triagem semântica", Severidade.INFO,
                       "Não foram reconhecidos por palavra-chave: " + "; ".join(ausentes) + ".",
                       "Confirmar na leitura (ou pela camada de IA) se o texto demonstra esses elementos.",
                       FUND_PT))
        if not any(t in jl for t in TERMOS_POLITICA):
            add(Achado(MOD, "PT-22 Alinhamento à política", Severidade.INFO,
                       "A justificativa não cita explicitamente a política, plano ou programa a que se vincula.",
                       "Recomendar a indicação do instrumento de planejamento (PNC, PPA, plano setorial).",
                       FUND_PT))

    # 5. Finalidade / emenda --------------------------------------------------
    emenda = pt.get("emenda") or {}
    if emenda and pt.get("funcao_subfuncao") and emenda.get("funcao_subfuncao"):
        if str(pt["funcao_subfuncao"]).strip() != str(emenda["funcao_subfuncao"]).strip():
            add(Achado(MOD, "PT-07 Finalidade da emenda", Severidade.CRITICA,
                       f"Função/subfunção do plano ({pt['funcao_subfuncao']}) difere da emenda "
                       f"({emenda['funcao_subfuncao']}).",
                       "Ajustar o objeto à finalidade da emenda ou registrar impedimento técnico.", FUND_LC210))
    if emenda.get("valor") and abs(_num(emenda["valor"]) - _num(pt.get("valor_repasse"))) > TOL:
        add(Achado(MOD, "PT-08 Valor da emenda", Severidade.ALTA,
                   f"Valor de repasse ({_brl(_num(pt.get('valor_repasse')))}) diferente do valor indicado na "
                   f"emenda ({_brl(_num(emenda['valor']))}).",
                   "Confirmar valor indicado pelo parlamentar e eventual complementação.", FUND_LC210))

    # 6. Consistência financeira --------------------------------------------
    vg, vr, cp = _num(pt.get("valor_global")), _num(pt.get("valor_repasse")), _num(pt.get("contrapartida"))
    if vg and abs(vg - (vr + cp)) > TOL:
        add(Achado(MOD, "PT-09 Composição do valor global", Severidade.CRITICA,
                   f"Valor global {_brl(vg)} ≠ repasse {_brl(vr)} + contrapartida {_brl(cp)}.",
                   "Corrigir valores do plano.", FUND_PT))

    metas = pt.get("metas") or []
    soma_metas = sum(_num(m.get("valor")) for m in metas)
    if metas and vg and abs(soma_metas - vg) > TOL:
        add(Achado(MOD, "PT-10 Soma das metas", Severidade.CRITICA,
                   f"Soma das metas ({_brl(soma_metas)}) difere do valor global ({_brl(vg)}).",
                   "Ajustar valores das metas.", FUND_PT))

    desemb = pt.get("cronograma_desembolso") or []
    soma_des = sum(_num(p.get("valor")) for p in desemb)
    if desemb and vg and abs(soma_des - vg) > TOL and abs(soma_des - vr) > TOL:
        add(Achado(MOD, "PT-11 Cronograma de desembolso", Severidade.ALTA,
                   f"Desembolso total ({_brl(soma_des)}) não fecha com repasse ({_brl(vr)}) nem com o global "
                   f"({_brl(vg)}).", "Corrigir cronograma de desembolso.", FUND_PT))

    pa = pt.get("plano_aplicacao") or []
    soma_pa = sum(_num(i.get("valor")) for i in pa)
    if pa and vg and abs(soma_pa - vg) > TOL:
        add(Achado(MOD, "PT-12 Plano de aplicação", Severidade.ALTA,
                   f"Plano de aplicação ({_brl(soma_pa)}) difere do valor global ({_brl(vg)}).",
                   "Ajustar naturezas de despesa.", FUND_PT))
    tipo_prop = str(prop.get("tipo", "")).lower()
    for i in pa:
        nd = re.sub(r"\D", "", str(i.get("natureza_despesa", "")))
        if nd.startswith("44") and ("osc" in tipo_prop or "privad" in tipo_prop):
            add(Achado(MOD, "PT-13 Natureza de despesa x proponente", Severidade.MEDIA,
                       f"Investimento (ND {nd}) proposto por entidade privada: verificar permissão na LDO/normativo.",
                       "Confirmar se a LDO vigente admite transferência de capital à entidade.",
                       "LDO do exercício", str(i.get("descricao"))))

    # 7. Metas e etapas -------------------------------------------------------
    ini, fim = _data((pt.get("vigencia") or {}).get("inicio")), _data((pt.get("vigencia") or {}).get("fim"))
    if ini and fim and fim <= ini:
        add(Achado(MOD, "PT-14 Vigência", Severidade.CRITICA, "Data final da vigência anterior ou igual à inicial.",
                   "Corrigir vigência.", FUND_PT))
    for m in metas:
        rot = f"Meta {m.get('numero', '?')}"
        if not m.get("indicador"):
            add(Achado(MOD, "PT-15 Indicador da meta", Severidade.ALTA, f"{rot} sem indicador de aferição.",
                       "Definir indicador físico mensurável (ex.: nº de oficinas realizadas).", FUND_PT))
        if _num(m.get("quantidade")) <= 0:
            add(Achado(MOD, "PT-16 Quantidade da meta", Severidade.ALTA, f"{rot} sem quantidade física.",
                       "Informar quantidade e unidade de medida.", FUND_PT))
        etapas = m.get("etapas") or []
        if not etapas:
            add(Achado(MOD, "PT-21 Meta sem etapas", Severidade.MEDIA,
                       f"{rot} sem etapas/cronograma de execução.",
                       "Detalhar etapas com prazo e valor para permitir o acompanhamento.", FUND_PT))
        if etapas:
            soma_et = sum(_num(e.get("valor")) for e in etapas)
            if abs(soma_et - _num(m.get("valor"))) > TOL:
                add(Achado(MOD, "PT-17 Etapas x meta", Severidade.MEDIA,
                           f"{rot}: etapas somam {_brl(soma_et)}, meta vale {_brl(_num(m.get('valor')))}.",
                           "Conciliar valores das etapas.", FUND_PT))
        for e in etapas:
            ei, ef = _data(e.get("inicio")), _data(e.get("fim"))
            if ini and fim and ((ei and ei < ini) or (ef and ef > fim)):
                add(Achado(MOD, "PT-18 Etapa fora da vigência", Severidade.MEDIA,
                           f"{rot} / etapa '{e.get('descricao')}' fora da vigência ({ini} a {fim}).",
                           "Ajustar cronograma de execução.", FUND_PT))

    for p in desemb:
        mes = _data(str(p.get("mes", "")) + "-01") if p.get("mes") and len(str(p.get("mes"))) == 7 else None
        if mes and ini and fim and not (date(ini.year, ini.month, 1) <= mes <= fim):
            add(Achado(MOD, "PT-19 Parcela fora da vigência", Severidade.MEDIA,
                       f"Parcela {p.get('parcela')} ({p.get('mes')}) fora da vigência.",
                       "Ajustar cronograma de desembolso.", FUND_PT))

    if cp == 0 and "munic" in tipo_prop:
        add(Achado(MOD, "PT-20 Contrapartida", Severidade.INFO,
                   "Contrapartida zerada para município.",
                   "Verificar percentuais mínimos/isenções previstos na LDO do exercício.", "LDO do exercício"))

    res.resumo = {
        "valor_global": vg, "valor_repasse": vr, "contrapartida": cp,
        "n_metas": len(metas), "n_etapas": sum(len(m.get("etapas") or []) for m in metas),
        "soma_metas": soma_metas, "soma_desembolso": soma_des, "soma_plano_aplicacao": soma_pa,
    }
    return res
