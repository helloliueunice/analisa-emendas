"""Checklist documental: classifica arquivos enviados contra o normativo
configurado em `config/checklist_documental.yaml` e verifica validade de
certidões pela data encontrada no texto."""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

import yaml

from .config import p as _p
from .modelos import Achado, ResultadoModulo, Severidade

MOD = "Checklist Documental"
RAIZ = Path(__file__).resolve().parent.parent
CHECKLIST_PADRAO = RAIZ / "config" / "checklist_documental.yaml"

RE_CNPJ = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
RE_DATA = r"(\d{2})[/.-](\d{2})[/.-](\d{4})"
RE_VALIDADE = re.compile(
    r"(v[aá]lid[ao]\s+at[eé]|validade[:\s]+|vencimento[:\s]+|v[aá]lida\s+at[eé]\s+o\s+dia)\s*" + RE_DATA,
    re.IGNORECASE,
)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def carregar_checklist(caminho: str | Path | None = None) -> dict:
    with open(caminho or CHECKLIST_PADRAO, encoding="utf-8") as f:
        return yaml.safe_load(f)


def extrair_validade(texto: str) -> date | None:
    """Procura expressões como 'Válida até 31/12/2026' e devolve a data."""
    m = RE_VALIDADE.search(texto or "")
    if not m:
        return None
    d, mth, y = m.group(2), m.group(3), m.group(4)
    try:
        return datetime(int(y), int(mth), int(d)).date()
    except ValueError:
        return None


def classificar(nome_arquivo: str, texto: str, itens: list[dict]) -> list[tuple[str, int]]:
    """Retorna [(id_item, pontuação)] ordenado. Nome do arquivo pesa mais."""
    nome_n, texto_n = _norm(nome_arquivo), _norm(texto[:20000])
    pont = []
    for it in itens:
        score = 0
        for p in it.get("palavras", []):
            pn = _norm(p)
            if pn in nome_n:
                score += 3
            score += min(texto_n.count(pn), 3)
        if score:
            pont.append((it["id"], score))
    return sorted(pont, key=lambda x: -x[1])


def analisar_documentos(arquivos: list[dict], tipo_proponente: str,
                        checklist: dict | None = None, hoje: date | None = None,
                        cnpj_proponente: str | None = None) -> ResultadoModulo:
    """`arquivos`: lista de {"nome": str, "texto": str}.
    `tipo_proponente`: "ente_publico" ou "osc"."""
    checklist = checklist or carregar_checklist()
    hoje = hoje or date.today()
    itens = [i for i in checklist["itens"] if tipo_proponente in i.get("aplica_a", [])]
    res = ResultadoModulo(MOD)

    atribuicao: dict[str, list[dict]] = {i["id"]: [] for i in itens}
    nao_classificados = []
    for arq in arquivos:
        cand = classificar(arq["nome"], arq.get("texto", ""), itens)
        if cand and cand[0][1] >= _p("documentos", "score_minimo_classificacao", 2):
            atribuicao[cand[0][0]].append({**arq, "score": cand[0][1]})
        else:
            nao_classificados.append(arq["nome"])

    linhas = []
    for it in itens:
        docs = atribuicao[it["id"]]
        status, validade = "Pendente", None
        if docs:
            status = "Encontrado"
            if it.get("validade"):
                validade = extrair_validade(" ".join(d.get("texto", "") for d in docs))
                if validade is None:
                    status = "Encontrado – validade não identificada"
                    res.achados.append(Achado(MOD, "DOC-02 Validade não lida", Severidade.MEDIA,
                                              f"{it['nome']}: não foi possível ler a data de validade.",
                                              "Conferir manualmente ou reemitir a certidão.", it["fundamento"],
                                              ", ".join(d["nome"] for d in docs)))
                elif validade < hoje:
                    status = "VENCIDO"
                    res.achados.append(Achado(MOD, "DOC-03 Certidão vencida", Severidade.CRITICA,
                                              f"{it['nome']} vencida em {validade:%d/%m/%Y}.",
                                              "Solicitar certidão atualizada antes da celebração.",
                                              it["fundamento"], ", ".join(d["nome"] for d in docs)))
                elif (validade - hoje).days <= _p("documentos", "dias_alerta_vencimento", 15):
                    status = f"Vence em {(validade - hoje).days} dia(s)"
                    res.achados.append(Achado(MOD, "DOC-04 Certidão a vencer", Severidade.INFO,
                                              f"{it['nome']} vence em {validade:%d/%m/%Y}.",
                                              "Programar a celebração/pagamento antes do vencimento.",
                                              it["fundamento"]))
        elif it.get("obrigatorio"):
            res.achados.append(Achado(MOD, "DOC-01 Documento ausente", Severidade.CRITICA,
                                      f"Documento obrigatório não localizado: {it['nome']}.",
                                      "Diligenciar o proponente.", it["fundamento"]))
        linhas.append({
            "Documento": it["nome"],
            "Obrigatório": "Sim" if it.get("obrigatorio") else "Não",
            "Status": status,
            "Arquivo(s)": ", ".join(d["nome"] for d in docs) or "—",
            "Validade": validade.strftime("%d/%m/%Y") if validade else "—",
            "Fundamento": it["fundamento"],
        })

    # cruzamento: CNPJ das certidões x CNPJ do proponente no plano
    if cnpj_proponente:
        alvo = re.sub(r"\D", "", cnpj_proponente)
        for it in itens:
            if not it.get("validade"):
                continue
            for d in atribuicao[it["id"]]:
                achados_cnpj = {re.sub(r"\D", "", c) for c in RE_CNPJ.findall(d.get("texto", ""))}
                if achados_cnpj and alvo not in achados_cnpj:
                    res.achados.append(Achado(
                        MOD, "DOC-06 CNPJ divergente", Severidade.CRITICA,
                        f"{it['nome']} ({d['nome']}) emitida para CNPJ diferente do proponente do plano.",
                        "Confirmar a titularidade: certidão de outra pessoa jurídica não comprova regularidade.",
                        it["fundamento"], f"Na certidão: {', '.join(sorted(achados_cnpj))} · Plano: {alvo}"))
    for arq in arquivos:
        txt = arq.get("texto", "")
        if arq["nome"].lower().endswith(".pdf") and len(txt.strip()) < _p("documentos", "caracteres_min_por_pagina", 80):
            res.achados.append(Achado(
                MOD, "DOC-07 Provável digitalização", Severidade.MEDIA,
                f"'{arq['nome']}' tem pouco ou nenhum texto extraível (imagem escaneada).",
                "Aplicar OCR ou solicitar PDF nativo; sem texto, a conferência automática fica limitada."))
    for n in nao_classificados:
        res.achados.append(Achado(MOD, "DOC-05 Arquivo não classificado", Severidade.INFO,
                                  f"Arquivo '{n}' não corresponde a nenhum item do checklist.",
                                  "Verificar se é documento complementar ou se o nome/conteúdo está ilegível (OCR)."))

    res.resumo = {"tabela": linhas, "versao_checklist": checklist.get("versao"),
                  "nao_classificados": nao_classificados}
    return res
