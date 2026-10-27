"""Avaliação de qualidade das regras do Plano de Trabalho.

Gera uma base SINTÉTICA ROTULADA: parte de um plano adequado, varia objeto e
justificativa com textos realistas (que também são adequados, mas usam
vocabulário diferente) e injeta defeitos conhecidos. O gabarito de cada caso
é o conjunto de regras que um analista esperaria ver disparadas.

Mede-se, por regra: verdadeiros positivos, falsos positivos, falsos
negativos, precisão e revocação. Falsos positivos em textos adequados mostram
as limitações das heurísticas (ex.: PT-06 por palavra-chave) e orientam a
calibração. Em produção, substituir por amostra REAL rotulada por analistas.
"""
from __future__ import annotations

import copy
import random
from pathlib import Path
import json

import pandas as pd

from .plano_trabalho import analisar_plano

EX = Path(__file__).resolve().parent.parent / "data" / "exemplos"

OBJETOS_OK = [
    "Realização de 40 oficinas de formação em audiovisual e 1 mostra pública para 200 jovens da rede municipal.",
    "Implantação de biblioteca comunitária com acervo de 3.000 livros e 12 meses de programação de leitura.",
    "Restauração da cobertura e das fachadas do Teatro Municipal, conforme projeto básico aprovado pelo IPHAN.",
    "Circulação de 8 espetáculos de dança em 4 municípios do semiárido, com 16 apresentações gratuitas.",
    "Capacitação de 120 mestres da cultura popular em gestão de projetos, com 10 encontros presenciais.",
]
JUSTIFICATIVAS_OK = [
    # usa o vocabulário esperado
    "O diagnóstico do Plano Municipal de Cultura aponta carência de formação artística. O público-alvo são "
    "jovens de 15 a 29 anos da rede pública. Espera-se como resultado a ampliação do acesso, em alinhamento ao "
    "Plano Nacional de Cultura e à política do Sistema Nacional de Cultura. A proposta foi debatida com o "
    "conselho municipal e considera indicadores de frequência e conclusão das oficinas ao final do projeto.",
    "Há demanda reprimida por espaços de leitura: o município não possui biblioteca pública ativa desde 2019. "
    "Serão atendidas cerca de 4.000 pessoas por ano, principalmente estudantes e famílias da periferia. O "
    "impacto esperado é a melhoria dos índices de leitura, conforme metas do programa estadual de leitura e da "
    "Política Nacional de Leitura e Escrita. O acervo será catalogado e aberto à comunidade com horário ampliado.",
    # adequadas, mas com vocabulário diferente (testam falso positivo de PT-06)
    "O teatro, tombado, está interditado desde 2024 por infiltrações que comprometem a estrutura do telhado. "
    "Sem a obra, o prédio corre risco de perda do patrimônio edificado e a cidade segue sem palco para os grupos "
    "locais, que hoje se apresentam em escolas improvisadas. Com a reabertura, estima-se receber 25 mil "
    "espectadores por ano, retomar a temporada de formaturas e festivais e gerar renda para técnicos da região.",
    "Os grupos de dança do semiárido raramente se apresentam fora de suas cidades por falta de transporte e de "
    "cachê. A circulação leva espetáculos a municípios sem equipamento cultural, com sessões gratuitas para "
    "escolas, e aproxima artistas locais de novos circuitos. As cidades foram escolhidas por não terem recebido "
    "nenhum espetáculo profissional nos últimos três anos, conforme levantamento da secretaria estadual.",
]

# Conjunto de VALIDAÇÃO: textos adequados escritos depois da calibração e NUNCA usados para
# ajustar as regras. Mede generalização (honestidade da métrica).
JUSTIFICATIVAS_VALIDACAO = [
    "A comunidade quilombola mantém a tradição do jongo, mas os mestres estão envelhecendo e poucos jovens "
    "aprendem os cantos. O projeto registra o repertório em áudio e vídeo e promove rodas mensais abertas, para "
    "que a nova geração assuma a transmissão. Ao final, o acervo ficará disponível na escola local e no ponto de "
    "cultura, permitindo o uso pedagógico pelos professores da rede e a valorização da identidade do território.",
    "Desde o fechamento do único cinema da cidade, em 2021, a população só assiste a filmes em telas de "
    "celular. A sala itinerante fará 48 sessões gratuitas em bairros afastados, com debate após cada exibição. "
    "A expectativa é reunir 6 mil espectadores e formar plateia para a produção audiovisual regional, em diálogo "
    "com a Política Nacional Aldir Blanc e com o plano municipal de cultura aprovado pela câmara.",
]

# defeito -> (função que altera o plano, regras esperadas)
def _cnpj(p): p["proponente"]["cnpj"] = "12.345.678/0001-00"
def _obj_gen(p): p["objeto"] = "Apoio a ações culturais diversas no município e região, conforme necessidade."
def _obj_curto(p): p["objeto"] = "Oficinas de audiovisual"
def _just_curta(p): p["justificativa"] = ("Diagnóstico: carência de oferta. Público: jovens. Resultado: ampliar o "
                                          "acesso, alinhado ao Plano Nacional de Cultura.")
def _final(p): p["funcao_subfuncao"] = "27.812"
def _val_em(p): p["emenda"]["valor"] = p["valor_repasse"] + 50000
def _global(p): p["contrapartida"] = p["contrapartida"] + 5000
def _metas(p):
    p["metas"][0]["valor"] += 1000
    p["metas"][0]["etapas"][-1]["valor"] += 1000
def _desemb(p): p["cronograma_desembolso"][-1]["valor"] -= 10000
def _aplic(p): p["plano_aplicacao"][0]["valor"] += 7000
def _indic(p): p["metas"][1]["indicador"] = ""
def _qtd(p): p["metas"][1]["quantidade"] = 0
def _etapa(p): p["metas"][0]["etapas"][-1]["fim"] = "2028-03-31"
def _parcela(p): p["cronograma_desembolso"][-1]["mes"] = "2028-02"
def _sem_etapas(p):
    p["metas"][1]["etapas"] = []
def _ausente(p): p["justificativa"] = ""


DEFEITOS = {
    "CNPJ inválido": (_cnpj, {"PT-02"}),
    "Objeto genérico": (_obj_gen, {"PT-04"}),
    "Objeto sucinto": (_obj_curto, {"PT-03"}),
    "Justificativa curta": (_just_curta, {"PT-05"}),
    "Finalidade divergente": (_final, {"PT-07"}),
    "Valor da emenda divergente": (_val_em, {"PT-08"}),
    "Valor global não fecha": (_global, {"PT-09"}),
    "Soma das metas não fecha": (_metas, {"PT-10"}),
    "Desembolso não fecha": (_desemb, {"PT-11"}),
    "Plano de aplicação não fecha": (_aplic, {"PT-12"}),
    "Meta sem indicador": (_indic, {"PT-15"}),
    "Meta sem quantidade": (_qtd, {"PT-16"}),
    "Etapa fora da vigência": (_etapa, {"PT-18"}),
    "Parcela fora da vigência": (_parcela, {"PT-19"}),
    "Meta sem etapas": (_sem_etapas, {"PT-21"}),
    "Justificativa ausente": (_ausente, {"PT-01"}),
}
CONFLITOS = [{"Objeto genérico", "Objeto sucinto"}, {"Justificativa curta", "Justificativa ausente"},
             {"Meta sem etapas", "Etapa fora da vigência"}]


def gerar_base(n: int = 300, semente: int = 42, validacao: bool = False) -> list[dict]:
    rnd = random.Random(semente)
    base = json.loads((EX / "plano_trabalho_adequado.json").read_text(encoding="utf-8"))
    casos = []
    nomes = list(DEFEITOS)
    for i in range(n):
        p = copy.deepcopy(base)
        p["objeto"] = rnd.choice(OBJETOS_OK)
        pool = JUSTIFICATIVAS_VALIDACAO if validacao else JUSTIFICATIVAS_OK
        p["justificativa"] = rnd.choice(pool)
        k = 0 if rnd.random() < 0.25 else rnd.randint(1, 3)
        escolhidos: set[str] = set()
        while len(escolhidos) < k:
            d = rnd.choice(nomes)
            if any(d in c and (c - {d}) & escolhidos for c in CONFLITOS):
                continue
            escolhidos.add(d)
        esperado: set[str] = set()
        for d in sorted(escolhidos):
            DEFEITOS[d][0](p)
            esperado |= DEFEITOS[d][1]
        from .plano_trabalho import TERMOS_POLITICA
        if p["justificativa"] and not any(t in p["justificativa"].lower() for t in TERMOS_POLITICA):
            esperado.add("PT-22")  # rótulo: alinhamento não explicitado (informativo)
        p["numero_proposta"] = f"{'VAL' if validacao else 'SINT'}-{i + 1:03d}"
        casos.append({"plano": p, "defeitos": sorted(escolhidos), "esperado": esperado})
    return casos


def avaliar(casos: list[dict] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    casos = casos or gerar_base()
    regras = sorted({r for _, rs in DEFEITOS.values() for r in rs} | {"PT-06", "PT-22"})
    cont = {r: {"VP": 0, "FP": 0, "FN": 0} for r in regras}
    por_caso = []
    for c in casos:
        obtido = {a.regra.split()[0] for a in analisar_plano(c["plano"]).achados}
        c["_pt23"] = "PT-23" in obtido
        for r in regras:
            if r in c["esperado"] and r in obtido:
                cont[r]["VP"] += 1
            elif r in obtido and r not in c["esperado"]:
                cont[r]["FP"] += 1
            elif r in c["esperado"] and r not in obtido:
                cont[r]["FN"] += 1
        obtido.discard("PT-23")  # nota informativa de triagem: medida à parte (taxa de disparo)
        extras = obtido - c["esperado"]
        por_caso.append({"Caso": c["plano"]["numero_proposta"], "Defeitos injetados": ", ".join(c["defeitos"]) or "—",
                         "Esperado": ", ".join(sorted(c["esperado"])) or "—",
                         "Obtido": ", ".join(sorted(obtido | ({"PT-23"} if c["_pt23"] else set()))) or "—",
                         "Acerto exato": obtido == c["esperado"],
                         "Falsos positivos": ", ".join(sorted(extras)) or "—"})
    linhas = []
    for r, v in cont.items():
        prec = v["VP"] / (v["VP"] + v["FP"]) if v["VP"] + v["FP"] else None
        rev = v["VP"] / (v["VP"] + v["FN"]) if v["VP"] + v["FN"] else None
        linhas.append({"Regra": r, **v, "Precisão": prec, "Revocação": rev})
    df_casos = pd.DataFrame(por_caso)
    taxa_pt23 = sum("PT-23" in o for o in df_casos["Obtido"]) / len(df_casos) if len(df_casos) else 0
    df = pd.DataFrame(linhas)
    df.attrs["taxa_triagem_pt23"] = taxa_pt23
    return df, df_casos
