"""Gera os dados SIMULADOS do piloto do Banco de Projetos de Impacto.

Tudo aqui é FICTÍCIO: uma "UF Piloto" com 36 municípios inventados
(códigos 99xxxxx, que não existem no IBGE), indicadores sorteados com
semente fixa, três programas de cultura com valores ilustrativos,
consultorias e emendas fictícias.

Em produção, estes arquivos são substituídos por extrações de:
  municipios.csv  -> IBGE (população), MUNIC/IBGE (equipamentos culturais),
                     CadÚnico (pobreza), SICONFI (RCL), Transferegov (execução),
                     Portal da Transparência (emendas recebidas)
  programas.csv   -> catálogo do MinC (cartilha parlamentar / SIGPAR)
  projetos.json   -> cadastro feito pelos entes na plataforma
  indicacoes.csv  -> SIOP / Portal da Transparência

Uso:  python scripts/gerar_banco.py
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "data" / "banco"

NOMES = [
    "Vale do Sabiá", "Serra Clara", "Lagoa das Garças", "Pedra Lisa", "Boa Vista do Ipê",
    "Santa Rita do Cerrado", "Morro do Jatobá", "Nova Aurora do Rio", "Cachoeira Mansa",
    "São Bento das Araras", "Vila Rosário", "Campo do Buriti", "Alto Pindaíba", "Ribeirão Sereno",
    "Mata Grande do Sul", "Bom Jardim das Pedras", "Três Barras do Norte", "Olho d'Água Claro",
    "Barra do Tamanduá", "Jardim das Palmeiras", "Monte Verde do Leste", "Riachão do Sertão",
    "Santa Luzia das Flores", "Coqueiral do Brejo", "Ponte Alta do Rio", "Várzea Nova",
    "Canto do Sabiá", "Ilha do Junco", "Sítio Novo das Serras", "Pau d'Arco Alegre",
    "Remanso Azul", "Lajeado das Antas", "Graúna do Sul", "Taquaral Bonito", "Esperança do Vale",
    "Recanto dos Ipês",
]

PROGRAMAS = [
    # valores ILUSTRATIVOS; conferir na cartilha do MinC do exercício
    {"id": "BIB", "nome": "Biblioteca pública – modelo padronizado", "equipamento": "tem_biblioteca",
     "custo_ref": 600000, "valor_min": 150000, "valor_max": 900000, "custeio_ref": 120000,
     "funcional": "13.392", "obra": True},
    {"id": "PTC", "nome": "Ponto de Cultura (Cultura Viva)", "equipamento": "tem_ponto_cultura",
     "custo_ref": 300000, "valor_min": 100000, "valor_max": 500000, "custeio_ref": 60000,
     "funcional": "13.392", "obra": False},
    {"id": "CEU", "nome": "CEU da Cultura", "equipamento": "tem_centro_cultural",
     "custo_ref": 2500000, "valor_min": 2000000, "valor_max": 3000000, "custeio_ref": 300000,
     "funcional": "13.392", "obra": True},
]

CONSULTORIAS = [  # fictícias
    {"nome": "Consultoria Fictícia Captar Projetos", "base": "556667770002"},
    {"nome": "Escritório Fictício Plano Certo", "base": "445556660001"},
    {"nome": "Assessoria Fictícia Cultura+", "base": "334445550001"},
]


def _cnpj(base12: str) -> str:
    def dv(b):
        p = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2][-len(b):]
        r = sum(int(x) * w for x, w in zip(b, p)) % 11
        return "0" if r < 2 else str(11 - r)
    c = base12 + dv(base12)
    c += dv(c)
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"


def municipios(rnd: random.Random) -> pd.DataFrame:
    linhas = []
    for i, nome in enumerate(NOMES):
        if i == 0:
            pop = 312_000
        elif i < 4:
            pop = int(rnd.uniform(60_000, 140_000))
        else:
            pop = int(math.exp(rnd.uniform(math.log(2_500), math.log(45_000))))
        pequeno = pop < 20_000
        pobreza = round(rnd.uniform(18, 58) if pequeno else rnd.uniform(10, 35), 1)
        linhas.append({
            "codigo": f"99{10001 + i:05d}",
            "municipio": nome,
            "uf": "UF Piloto (fictícia)",
            "lat": round(-8.0 + rnd.uniform(-2.2, 2.2), 4),
            "lon": round(-46.0 + rnd.uniform(-2.8, 2.8), 4),
            "populacao": pop,
            "pct_pobreza_cadunico": pobreza,
            "tem_biblioteca": int(rnd.random() < (0.95 if not pequeno else 0.55)),
            "tem_ponto_cultura": int(rnd.random() < (0.8 if not pequeno else 0.25)),
            "tem_centro_cultural": int(rnd.random() < (0.7 if not pequeno else 0.10)),
            "plano_municipal_cultura": int(rnd.random() < (0.8 if not pequeno else 0.35)),
            "rcl": int(pop * rnd.uniform(2800, 4200)),
            "execucao_historica": "" if rnd.random() < 0.3 else round(rnd.uniform(0.35, 0.97), 2),
            "cauc_regular": int(rnd.random() < 0.9) if i != 9 else 0,  # um caso didático de CAUC irregular
            "emendas_cultura_pc_3anos": round(rnd.choice([0, 0, 0, 1, 2, 4, 8, 15, 40]) * rnd.uniform(0.5, 1.5), 2),
        })
    return pd.DataFrame(linhas)


def projetos(rnd: random.Random, mun: pd.DataFrame) -> list[dict]:
    progs = {p["id"]: p for p in PROGRAMAS}
    cons = [{**c, "cnpj": _cnpj(c["base"])} for c in CONSULTORIAS]
    out = []
    usados = set()
    i = 0
    while len(out) < 30:
        i += 1
        m = mun.sample(1, random_state=rnd.randint(0, 10 ** 6)).iloc[0]
        pid = rnd.choices(["BIB", "PTC", "CEU"], weights=[4, 5, 2])[0]
        prog = progs[pid]
        if (m["codigo"], pid) in usados:
            continue
        # a maioria das demandas vem de onde falta o equipamento
        if m[prog["equipamento"]] == 1 and rnd.random() < 0.75:
            continue
        if pid == "CEU" and m["populacao"] < 8000 and rnd.random() < 0.7:
            continue
        usados.add((m["codigo"], pid))
        padrao = rnd.random() < 0.5
        maturidade = 4 if padrao else rnd.choice([1, 2, 3, 3, 4, 5])
        custo = prog["custo_ref"] if padrao else round(prog["custo_ref"] * rnd.uniform(0.8, 1.55), -3)
        custo = min(max(custo, prog["valor_min"]), prog["valor_max"] * 1.1)
        r = rnd.random()
        if r < 0.5:
            elab = {"tipo": "proprio_ente", "nome": "Equipe do próprio ente", "cnpj": "", "remuneracao": "sem_custo",
                    "valor": 0}
        elif r < 0.9:
            c = cons[0] if rnd.random() < 0.55 else rnd.choice(cons[1:])
            elab = {"tipo": "consultoria", "nome": c["nome"], "cnpj": c["cnpj"], "remuneracao": "fixa",
                    "valor": round(rnd.uniform(8000, 25000), -2)}
        else:
            elab = {"tipo": "osc_parceira", "nome": "OSC parceira (fictícia)", "cnpj": "", "remuneracao": "sem_custo",
                    "valor": 0}
        out.append({
            "id": f"P{len(out) + 1:03d}",
            "codigo_municipio": m["codigo"],
            "programa": pid,
            "titulo": f"{prog['nome'].split(' –')[0].split(' (')[0]} em {m['municipio']}",
            "modelo_padrao": padrao,
            "maturidade": maturidade,
            "custo": float(custo),
            "custeio_anual": float(round(prog["custeio_ref"] * rnd.uniform(0.8, 1.25), -3)),
            "custeio_comprovado": rnd.random() < 0.75,
            "fonte_custeio": "Orçamento municipal (LOA), função 13",
            "beneficiarios_ano": int(m["populacao"] * rnd.uniform(0.08, 0.3)),
            "elaborador": elab,
            "representante_gov_br_ouro": True,
            "status": "",
            "historico": [],
        })
    # casos didáticos de linha vermelha
    out[7]["elaborador"] = {"tipo": "consultoria", "nome": cons[1]["nome"], "cnpj": cons[1]["cnpj"],
                            "remuneracao": "exito", "valor": 0}
    out[12]["representante_gov_br_ouro"] = False
    # status iniciais
    estados = (["certificado"] * 14 + ["em_curadoria"] * 9 + ["devolvido"] * 2 + ["rascunho"] * 5)
    rnd.shuffle(estados)
    for p, s in zip(out, estados):
        p["status"] = s
        p["historico"].append({"quando": "2026-11-10", "quem": "ente", "acao": "cadastro"})
        if s in ("certificado", "devolvido"):
            p["historico"].append({"quando": "2026-11-20", "quem": "MinC (curadoria)", "acao": s})
    # coerência: só fica "certificado" quem passa na elegibilidade e no checklist objetivo
    munx = mun.set_index("codigo")
    for p in out:
        prog = progs[p["programa"]]
        m = munx.loc[p["codigo_municipio"]]
        passa = (p["representante_gov_br_ouro"] and p["elaborador"]["remuneracao"] != "exito"
                 and int(m["cauc_regular"]) == 1 and prog["valor_min"] <= p["custo"] <= prog["valor_max"]
                 and (p["maturidade"] >= 3 or p["modelo_padrao"]) and p["custo"] <= prog["custo_ref"] * 1.2
                 and p["custeio_comprovado"])
        if p["status"] == "certificado" and not passa:
            linha_vermelha = (not p["representante_gov_br_ouro"] or p["elaborador"]["remuneracao"] == "exito"
                              or int(m["cauc_regular"]) == 0)
            if linha_vermelha:
                p["status"] = "em_curadoria"
                p["historico"] = p["historico"][:1]
            else:  # o ente ajustou o projeto na curadoria antes de ser certificado
                p["custeio_comprovado"] = True
                p["maturidade"] = max(p["maturidade"], 3)
                p["custo"] = float(min(max(p["custo"], prog["valor_min"]), prog["custo_ref"] * 1.2,
                                       prog["valor_max"]))
    return out


def indicacoes(rnd: random.Random, mun: pd.DataFrame, projs: list[dict]) -> pd.DataFrame:
    cert = [p for p in projs if p["status"] == "certificado"]
    linhas = []
    for k, p in enumerate(rnd.sample(cert, 5)):
        linhas.append({"emenda": f"2027.9999.{k + 1:04d}", "gabinete": f"Gabinete {chr(65 + k)} (fictício)",
                       "codigo_municipio": p["codigo_municipio"], "programa": p["programa"],
                       "valor": p["custo"], "projeto_id": p["id"], "reconciliada": 1, "situacao": "empenhada"})
    for k in range(7):
        m = mun.sample(1, random_state=rnd.randint(0, 10 ** 6)).iloc[0]
        linhas.append({"emenda": f"2027.9999.{k + 6:04d}", "gabinete": f"Gabinete {chr(70 + k % 5)} (fictício)",
                       "codigo_municipio": m["codigo"], "programa": rnd.choice(["BIB", "PTC", "outro"]),
                       "valor": float(round(rnd.uniform(100000, 800000), -3)), "projeto_id": "",
                       "reconciliada": int(k < 5), "situacao": rnd.choice(["empenhada", "paga"])})
    return pd.DataFrame(linhas)


def main():
    rnd = random.Random(2027)
    OUT.mkdir(parents=True, exist_ok=True)
    mun = municipios(rnd)
    mun.to_csv(OUT / "municipios.csv", index=False)
    pd.DataFrame(PROGRAMAS).to_csv(OUT / "programas.csv", index=False)
    projs = projetos(rnd, mun)
    (OUT / "projetos.json").write_text(json.dumps(projs, ensure_ascii=False, indent=1), encoding="utf-8")
    indicacoes(rnd, mun, projs).to_csv(OUT / "indicacoes.csv", index=False)
    print(f"{len(mun)} municípios, {len(projs)} projetos -> {OUT}")


if __name__ == "__main__":
    main()
