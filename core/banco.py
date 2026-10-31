"""Banco Público de Projetos de Impacto – núcleo (pré-indicação).

Implementa o desenho aprovado no painel de especialistas (out/2026):
  * necessidade medida por território (lacuna do equipamento + vulnerabilidade);
  * elegibilidade e LINHAS VERMELHAS como regras determinísticas (sim/não com motivo);
  * certificação por CHECKLIST objetivo (não por juízo subjetivo);
  * ordenação em FAIXAS, sempre DENTRO de um programa (nunca nota única entre setores);
  * teste de SENSIBILIDADE dos pesos: faixa instável é sinalizada;
  * alertas de integridade (consultoria recorrente, concentração, duplicidade);
  * indicadores públicos (funil, dentro × fora do banco, reconciliação);
  * período vedado pela lei eleitoral (art. 73, VI, Lei 9.504/97) calculado pela data.

Nada aqui recomenda parlamentar nem destino: a escolha é do autor da emenda.
"""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import pandas as pd

from .plano_trabalho import cnpj_valido

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "data" / "banco"

PESOS = {"N": 0.30, "M": 0.20, "C": 0.20, "E": 0.15, "S": 0.10, "A": 0.05}
NOMES = {"N": "Necessidade", "M": "Prontidão", "C": "Custo-efetividade", "E": "Capacidade de execução",
         "S": "Sustentabilidade do custeio", "A": "Alinhamento ao plano"}
FAIXAS = [("Alta", 0.70), ("Média", 0.50), ("Baixa", 0.0)]
STATUS = {"rascunho": "Rascunho", "em_curadoria": "Em curadoria", "certificado": "Certificado",
          "devolvido": "Devolvido para ajuste", "indicado": "Indicado (emenda vinculada)"}


# ------------------------------------------------------------------ dados
@lru_cache(maxsize=1)
def _sementes():
    mun = pd.read_csv(DADOS / "municipios.csv", dtype={"codigo": str})
    prog = pd.read_csv(DADOS / "programas.csv")
    proj = json.loads((DADOS / "projetos.json").read_text(encoding="utf-8"))
    ind = pd.read_csv(DADOS / "indicacoes.csv", dtype={"codigo_municipio": str, "projeto_id": str},
                      keep_default_na=False)
    return mun, prog, proj, ind


def estado_inicial() -> dict:
    mun, prog, proj, ind = _sementes()
    return {"municipios": mun, "programas": prog, "projetos": copy.deepcopy(proj),
            "indicacoes": ind.to_dict("records"), "demandas": [], "registro": []}


def municipio(b: dict, codigo: str) -> dict:
    return b["municipios"].set_index("codigo").loc[codigo].to_dict() | {"codigo": codigo}


def programa(b: dict, pid: str) -> dict:
    return b["programas"].set_index("id").loc[pid].to_dict() | {"id": pid}


def registrar(b: dict, quem: str, acao: str, alvo: str, dados: dict | None = None) -> dict:
    """Registro público de eventos, com hash encadeado (cada evento sela o anterior)."""
    anterior = b["registro"][-1]["hash"] if b["registro"] else "0" * 64
    ev = {"quando": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
          "quem": quem, "acao": acao, "alvo": alvo, "dados": dados or {}}
    ev["hash"] = hashlib.sha256((anterior + json.dumps(ev, sort_keys=True, ensure_ascii=False)).encode()).hexdigest()
    b["registro"].append(ev)
    return ev


# ------------------------------------------------------------ necessidade
def necessidade(m: dict, prog: dict) -> tuple[float, str]:
    """0..1. 70% ausência do equipamento do programa + 30% vulnerabilidade (CadÚnico)."""
    ausente = int(m[prog["equipamento"]]) == 0
    vuln = min(float(m["pct_pobreza_cadunico"]) / 60, 1.0)
    n = 0.7 * (1.0 if ausente else 0.2) + 0.3 * vuln
    txt = (f"{'não tem' if ausente else 'já tem'} o equipamento; "
           f"{m['pct_pobreza_cadunico']:.0f}% da população em pobreza no CadÚnico")
    return round(n, 3), txt


def mapa_lacunas(b: dict, pid: str) -> pd.DataFrame:
    prog = programa(b, pid)
    df = b["municipios"].copy()
    res = [necessidade(r, prog) for r in df.to_dict("records")]
    df["necessidade"] = [r[0] for r in res]
    df["lacuna"] = df[prog["equipamento"]].map({0: "Sem o equipamento", 1: "Já tem"})
    df["porte"] = pd.cut(df["populacao"], [0, 20000, 100000, 10 ** 9],
                         labels=["Pequeno (<20 mil)", "Médio", "Grande (>100 mil)"]).astype(str)
    projs = {(p["codigo_municipio"]) for p in b["projetos"] if p["programa"] == pid}
    df["tem_projeto"] = df["codigo"].isin(projs)
    return df


# ------------------------------------------------------------- pontuação
def componentes(p: dict, m: dict, prog: dict) -> dict:
    n, n_txt = necessidade(m, prog)
    mat = p["maturidade"] / 5
    c = min(1.0, float(prog["custo_ref"]) / float(p["custo"])) if p["custo"] else 0.0
    eh = m.get("execucao_historica")
    sem_hist = eh in ("", None) or (isinstance(eh, float) and pd.isna(eh))
    e = 0.5 if sem_hist else float(eh)
    if p.get("custeio_comprovado"):
        ratio = float(p["custeio_anual"]) / max(float(m["rcl"]), 1)
        s = max(0.0, min(1.0, 1 - (ratio - 0.005) / (0.03 - 0.005)))
    else:
        ratio, s = None, 0.0
    a = 1.0 if int(m["plano_municipal_cultura"]) == 1 else 0.4
    return {
        "N": (n, n_txt),
        "M": (mat, f"maturidade {p['maturidade']} de 5" + (" (modelo padronizado)" if p.get("modelo_padrao") else "")),
        "C": (round(c, 3), f"custo R$ {p['custo']:,.0f} para referência R$ {prog['custo_ref']:,.0f}".replace(",", ".")),
        "E": (e, "sem histórico: nota neutra 0,5" if sem_hist else f"{e:.0%} de execução em instrumentos anteriores"),
        "S": (round(s, 3), "custeio não comprovado" if ratio is None else f"custeio anual = {ratio:.1%} da RCL".replace(".", ",")),
        "A": (a, "tem plano municipal de cultura" if a == 1 else "sem plano municipal de cultura"),
    }


def pontuar(comp: dict, pesos: dict | None = None) -> float:
    pesos = pesos or PESOS
    tot = sum(pesos.values())
    return round(sum(pesos[k] * comp[k][0] for k in pesos) / tot, 4)


def faixa(score: float) -> str:
    for nome, lim in FAIXAS:
        if score >= lim:
            return nome
    return "Baixa"


def variantes_pesos(delta: float = 0.05) -> list[dict]:
    out = []
    for k in PESOS:
        for sinal in (+1, -1):
            w = dict(PESOS)
            w[k] = max(0.0, w[k] + sinal * delta)
            out.append(w)
    return out


def sensibilidade(comp: dict, delta: float = 0.05) -> tuple[bool, set]:
    faixas = {faixa(pontuar(comp, w)) for w in variantes_pesos(delta)} | {faixa(pontuar(comp))}
    return len(faixas) == 1, faixas


def explicar(comp: dict) -> str:
    contrib = sorted(((PESOS[k] * comp[k][0], k) for k in PESOS), reverse=True)
    forte = NOMES[contrib[0][1]].lower()
    fracos = [k for k in PESOS if comp[k][0] < 0.5]
    txt = f"Puxado para cima por {forte}"
    if fracos:
        txt += "; puxado para baixo por " + ", ".join(NOMES[k].lower() for k in fracos)
    return txt + "."


# --------------------------------------------- elegibilidade e linhas vermelhas
def elegibilidade(p: dict, m: dict, prog: dict) -> list[dict]:
    """Bloqueios determinísticos. Qualquer item não atendido impede a certificação."""
    el = p.get("elaborador") or {}
    itens = [
        ("Cadastro pelo representante legal (gov.br ouro)", bool(p.get("representante_gov_br_ouro")),
         "Linha vermelha 2: só o representante legal cadastra; intermediário não."),
        ("Elaborador sem remuneração por êxito ou percentual", el.get("remuneracao") != "exito",
         "Linha vermelha 2: remuneração por êxito é vedada na plataforma."),
        ("Ente regular no CAUC", int(m["cauc_regular"]) == 1,
         "Linha vermelha 7: ente inadimplente não é habilitado."),
        ("Valor dentro da faixa do programa",
         float(prog["valor_min"]) <= float(p["custo"]) <= float(prog["valor_max"]),
         f"Faixa do programa: R$ {prog['valor_min']:,.0f} a R$ {prog['valor_max']:,.0f}".replace(",", ".")),
    ]
    if el.get("tipo") == "consultoria":
        itens.append(("CNPJ do elaborador válido e declarado", cnpj_valido(el.get("cnpj", "")),
                      "Declaração obrigatória de quem elaborou e quanto recebeu."))
    return [{"item": i, "ok": ok, "motivo": mot} for i, ok, mot in itens]


def checklist_certificacao(p: dict, prog: dict) -> list[dict]:
    """Checklist OBJETIVO do ministério (amparo: art. 28 da LINDB – não garante resultado)."""
    itens = [
        ("Prontidão mínima (maturidade 3 ou modelo padronizado)", p["maturidade"] >= 3 or p.get("modelo_padrao")),
        ("Custo até 20% acima da referência", float(p["custo"]) <= float(prog["custo_ref"]) * 1.2),
        ("Custeio anual comprovado e com fonte declarada", bool(p.get("custeio_comprovado") and p.get("fonte_custeio"))),
        ("Beneficiários estimados informados", int(p.get("beneficiarios_ano") or 0) > 0),
    ]
    return [{"item": i, "ok": bool(ok)} for i, ok in itens]


def avaliar(b: dict, p: dict) -> dict:
    m, prog = municipio(b, p["codigo_municipio"]), programa(b, p["programa"])
    comp = componentes(p, m, prog)
    sc = pontuar(comp)
    estavel, fx = sensibilidade(comp)
    eleg = elegibilidade(p, m, prog)
    chk = checklist_certificacao(p, prog)
    return {"projeto": p, "municipio": m, "programa": prog, "componentes": comp, "score": sc,
            "faixa": faixa(sc), "estavel": estavel, "faixas_possiveis": fx, "elegibilidade": eleg,
            "elegivel": all(i["ok"] for i in eleg), "checklist": chk,
            "certificavel": all(i["ok"] for i in eleg) and all(i["ok"] for i in chk),
            "explicacao": explicar(comp), "indicado": status_indicado(b, p["id"])}


def status_indicado(b: dict, pid: str) -> str:
    for i in b["indicacoes"]:
        if str(i.get("projeto_id")) == pid:
            return i["emenda"]
    return ""


def tabela(b: dict, pid: str | None = None, so_certificados: bool = False) -> pd.DataFrame:
    linhas = []
    for p in b["projetos"]:
        if pid and p["programa"] != pid:
            continue
        if so_certificados and p["status"] != "certificado":
            continue
        a = avaliar(b, p)
        linhas.append({
            "id": p["id"], "Projeto": p["titulo"], "Município": a["municipio"]["municipio"],
            "População": int(a["municipio"]["populacao"]), "Programa": p["programa"],
            "Status": "Indicado" if a["indicado"] else STATUS.get(p["status"], p["status"]),
            "Faixa": a["faixa"], "Faixa estável": a["estavel"], "Custo (R$)": float(p["custo"]),
            **{NOMES[k]: a["componentes"][k][0] for k in PESOS}, "_score": a["score"],
        })
    df = pd.DataFrame(linhas)
    if not df.empty:
        ordem = {"Alta": 0, "Média": 1, "Baixa": 2}
        df = df.sort_values(["Faixa", "Município"], key=lambda s: s.map(ordem) if s.name == "Faixa" else s)
    return df


# --------------------------------------------------------------- integridade
def alertas(b: dict) -> list[dict]:
    out = []
    # consultoria que aparece em muitos municípios
    por_cnpj: dict[str, set] = {}
    nomes = {}
    for p in b["projetos"]:
        el = p.get("elaborador") or {}
        if el.get("tipo") == "consultoria" and el.get("cnpj"):
            por_cnpj.setdefault(el["cnpj"], set()).add(p["codigo_municipio"])
            nomes[el["cnpj"]] = el["nome"]
    for cnpj, muns in por_cnpj.items():
        if len(muns) >= 3:
            out.append({"tipo": "Consultoria recorrente", "detalhe":
                        f"{nomes[cnpj]} ({cnpj}) elaborou projetos em {len(muns)} municípios.",
                        "providencia": "Conferir contratos, valores declarados e se houve cobrança vinculada a êxito."})
    # concentração de emendas recebidas (adicionalidade)
    mun = b["municipios"]
    p90 = mun["emendas_cultura_pc_3anos"].quantile(0.9)
    for r in mun[mun["emendas_cultura_pc_3anos"] > p90].to_dict("records"):
        if any(p["codigo_municipio"] == r["codigo"] for p in b["projetos"]):
            out.append({"tipo": "Concentração (adicionalidade)", "detalhe":
                        f"{r['municipio']} recebeu R$ {r['emendas_cultura_pc_3anos']:.0f} por habitante em emendas "
                        "de cultura em 3 anos, acima de 90% dos municípios.",
                        "providencia": "Verificar se o novo recurso é adicional ou substitui gasto próprio."})
    # duplicidade município × programa
    vistos: dict[tuple, list] = {}
    for p in b["projetos"]:
        vistos.setdefault((p["codigo_municipio"], p["programa"]), []).append(p["id"])
    for (cod, pid), ids in vistos.items():
        if len(ids) > 1:
            out.append({"tipo": "Possível duplicidade", "detalhe": f"{len(ids)} projetos {pid} no mesmo município: "
                        + ", ".join(ids), "providencia": "Confirmar se são objetos distintos."})
    return out


def periodo_eleitoral(d: date) -> dict:
    """Eleições no 1º domingo de outubro dos anos pares; o art. 73, VI, da Lei 9.504/97
    veda transferências voluntárias e publicidade institucional nos 3 meses anteriores."""
    def primeiro_domingo_out(ano):
        x = date(ano, 10, 1)
        return x + timedelta(days=(6 - x.weekday()) % 7)
    ano = d.year if d.year % 2 == 0 else d.year + 1
    eleicao = primeiro_domingo_out(ano)
    if d > eleicao + timedelta(days=21):  # passado o 2º turno, olha a próxima
        ano += 2
        eleicao = primeiro_domingo_out(ano)
    inicio = date(eleicao.year, eleicao.month - 3, eleicao.day)
    fim = eleicao + timedelta(days=21)  # cobre o 2º turno (último domingo de outubro)
    return {"vedado": inicio <= d <= fim, "inicio": inicio, "eleicao": eleicao, "fim": fim,
            "tipo": "municipal" if ano % 4 == 0 else "geral"}


# ------------------------------------------------------------ painel público
def painel(b: dict) -> dict:
    projs = b["projetos"]
    ind = pd.DataFrame(b["indicacoes"])
    cert = [p for p in projs if p["status"] == "certificado"]
    vinculados = {str(i["projeto_id"]) for i in b["indicacoes"] if i.get("projeto_id")}
    funil = [
        ("Lacunas mapeadas", int(sum((b["municipios"][c] == 0).sum() for c in b["programas"]["equipamento"]))),
        ("Projetos cadastrados", len(projs)),
        ("Projetos certificados", len(cert)),
        ("Com emenda vinculada", len(vinculados)),
    ]
    dentro = ind[ind["projeto_id"].astype(str) != ""] if not ind.empty else ind
    fora = ind[ind["projeto_id"].astype(str) == ""] if not ind.empty else ind
    faixa_escolhidos = []
    for pid in dentro["projeto_id"] if not dentro.empty else []:
        p = next((x for x in projs if x["id"] == pid), None)
        if p:
            faixa_escolhidos.append(avaliar(b, p)["faixa"])
    return {
        "funil": funil,
        "dentro": len(dentro), "fora": len(fora),
        "valor_dentro": float(dentro["valor"].sum()) if not dentro.empty else 0.0,
        "valor_fora": float(fora["valor"].sum()) if not fora.empty else 0.0,
        "faixas_escolhidas": pd.Series(faixa_escolhidos, dtype=str).value_counts().to_dict(),
        "reconciliacao": float(ind["reconciliada"].astype(int).mean()) if not ind.empty else 1.0,
        "nao_reconciliadas": ind[ind["reconciliada"].astype(int) == 0]["emenda"].tolist() if not ind.empty else [],
        "pequenos_share_projetos": _share_pequenos(b),
    }


def _share_pequenos(b: dict) -> tuple[float, float]:
    mun = b["municipios"].set_index("codigo")
    peq = set(mun[mun["populacao"] < 20000].index)
    projs = b["projetos"]
    share_proj = sum(p["codigo_municipio"] in peq for p in projs) / max(len(projs), 1)
    share_pop = mun.loc[list(peq), "populacao"].sum() / mun["populacao"].sum()
    return round(share_proj, 3), round(float(share_pop), 3)


# --------------------------------------------------------- resumo p/ gabinete
def resumo_markdown(a: dict) -> str:
    p, m, prog, c = a["projeto"], a["municipio"], a["programa"], a["componentes"]
    L = [f"# {p['titulo']}", "",
         f"**Programa:** {prog['nome']} (funcional {prog['funcional']})  ",
         f"**Município:** {m['municipio']} – {m['uf']} · população {int(m['populacao']):,}".replace(",", ".") + "  ",
         f"**Valor:** R$ {p['custo']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + "  ",
         f"**Situação no banco:** {STATUS.get(p['status'], p['status'])} · faixa **{a['faixa']}**"
         + ("" if a["estavel"] else " (faixa sensível aos pesos)"), "",
         "## Por que este projeto", "", a["explicacao"], ""]
    for k in PESOS:
        L.append(f"- **{NOMES[k]}** ({c[k][0]:.2f}): {c[k][1]}".replace(f"({c[k][0]:.2f})", f"({c[k][0]:.2f})".replace(".", ",")))
    el = p.get("elaborador") or {}
    L += ["", "## Execução e custeio", "",
          f"- Beneficiários estimados por ano: {int(p['beneficiarios_ano']):,}".replace(",", "."),
          f"- Custeio anual: R$ {p['custeio_anual']:,.0f}".replace(",", ".") + f" · fonte: {p.get('fonte_custeio') or '—'}",
          f"- Elaborado por: {el.get('nome', '—')}" + (f" (CNPJ {el['cnpj']}, R$ {el['valor']:,.0f})".replace(",", ".")
                                                        if el.get("cnpj") else ""),
          "", "## Avisos", "",
          "- A ordenação em faixas é informativa e não vinculante; não constitui impedimento técnico nem condição.",
          "- A escolha da emenda é prerrogativa do parlamentar e fica registrada publicamente.",
          "- Documento gerado pelo protótipo do Banco de Projetos de Impacto. DADOS FICTÍCIOS."]
    return "\n".join(L)
