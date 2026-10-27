"""Camada opcional de IA generativa.

Dois provedores possíveis (variável LLM_PROVIDER ou st.secrets):
  * "anthropic"     – API do Claude (ANTHROPIC_API_KEY, LLM_MODEL)
  * "openai_compat" – qualquer servidor compatível com /v1/chat/completions,
                      inclusive modelos abertos rodando NA REDE DO ÓRGÃO
                      (Ollama, vLLM, LM Studio): LLM_BASE_URL, LLM_API_KEY, LLM_MODEL

Sem configuração, o app funciona só com as regras determinísticas.

Princípios: a IA só SUGERE achados; toda sugestão é marcada como origem="ia"
e precisa ser confirmada pelo analista. Dados pessoais devem ser
pseudonimizados antes do envio a provedores externos (ver `pseudonimizar`).
"""
from __future__ import annotations

import json
import os
import re

from .modelos import Achado, Severidade

PROMPT_SISTEMA = """Você é um analista técnico sênior do Poder Executivo federal, especializado em
transferências da União oriundas de emendas parlamentares (Decreto 11.531/2023,
Portaria Conjunta MGI/MF/CGU 33/2023, Lei 13.019/2014, LC 210/2024).
Analise o plano de trabalho com rigor técnico, imparcialidade e foco em:
1) objeto certo e determinado; 2) nexo causal entre problema, objeto, metas e resultados;
3) metas mensuráveis e indicadores verificáveis; 4) compatibilidade de prazos e custos;
5) aderência à finalidade (função/subfunção) da emenda; 6) riscos de execução.
Não invente fatos. Se a informação não estiver no texto, diga que não está.
Responda SOMENTE com JSON válido no formato:
{"achados":[{"regra":"IA-xx título curto","severidade":"Crítica|Alta|Média|Informativa",
"mensagem":"...","recomendacao":"...","evidencia":"trecho literal curto do plano"}],
"sintese":"parágrafo de até 120 palavras para o parecer técnico"}"""


def _cfg(nome: str, padrao: str = "") -> str:
    try:
        import streamlit as st

        if nome in st.secrets:
            return str(st.secrets[nome])
    except Exception:
        pass
    return os.getenv(nome, padrao)


def disponivel() -> bool:
    prov = _cfg("LLM_PROVIDER", "anthropic")
    if prov == "openai_compat":
        return bool(_cfg("LLM_BASE_URL"))
    return bool(_cfg("ANTHROPIC_API_KEY"))


def descricao_provedor() -> str:
    prov = _cfg("LLM_PROVIDER", "anthropic")
    if prov == "openai_compat":
        return f"Modelo local/compatível: {_cfg('LLM_MODEL', 'llama3.1')} em {_cfg('LLM_BASE_URL')}"
    return f"Claude API: {_cfg('LLM_MODEL', 'claude-sonnet-5-5')}"


def pseudonimizar(texto: str) -> str:
    """Mascara CPF, e-mail e telefone antes de enviar a provedor externo (LGPD)."""
    texto = re.sub(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", "[CPF]", texto)
    texto = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[EMAIL]", texto)
    texto = re.sub(r"\(?\b\d{2}\)?\s?9?\d{4}-?\d{4}\b", "[TELEFONE]", texto)
    return texto


def _chamar(sistema: str, usuario: str, max_tokens: int = 2000) -> str:
    prov = _cfg("LLM_PROVIDER", "anthropic")
    if prov == "openai_compat":
        import httpx

        r = httpx.post(
            _cfg("LLM_BASE_URL").rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {_cfg('LLM_API_KEY', 'x')}"},
            json={"model": _cfg("LLM_MODEL", "llama3.1"), "temperature": 0, "max_tokens": max_tokens,
                  "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}]},
            timeout=180,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    import anthropic

    cli = anthropic.Anthropic(api_key=_cfg("ANTHROPIC_API_KEY"))
    msg = cli.messages.create(model=_cfg("LLM_MODEL", "claude-sonnet-5-5"), max_tokens=max_tokens,
                              system=sistema, messages=[{"role": "user", "content": usuario}])
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


def _json(txt: str) -> dict:
    m = re.search(r"\{.*\}", txt, re.DOTALL)
    return json.loads(m.group(0)) if m else {}


def analisar_plano_ia(plano: dict | str, contexto_normativo: str = "") -> tuple[list[Achado], str]:
    """Retorna (achados sugeridos pela IA, síntese para o parecer)."""
    conteudo = plano if isinstance(plano, str) else json.dumps(plano, ensure_ascii=False, indent=1)
    usuario = pseudonimizar(conteudo)[:60000]
    if contexto_normativo:
        usuario = f"Orientações internas do órgão:\n{contexto_normativo}\n\nPLANO DE TRABALHO:\n{usuario}"
    else:
        usuario = f"PLANO DE TRABALHO:\n{usuario}"
    dados = _json(_chamar(PROMPT_SISTEMA, usuario))
    mapa = {s.value: s for s in Severidade}
    achados = [
        Achado("Plano de Trabalho (IA)", a.get("regra", "IA"), mapa.get(a.get("severidade"), Severidade.MEDIA),
               a.get("mensagem", ""), a.get("recomendacao", ""), evidencia=a.get("evidencia", ""), origem="ia")
        for a in dados.get("achados", [])
    ]
    return achados, dados.get("sintese", "")


def estruturar_plano_ia(texto: str) -> dict:
    """Converte um plano de trabalho em PDF/DOCX (texto livre) no JSON padrão do app."""
    sistema = ("Extraia do texto um plano de trabalho no JSON com as chaves: objeto, justificativa, "
               "funcao_subfuncao, proponente{nome,cnpj,tipo,uf,municipio}, emenda{numero,autor,valor,"
               "funcao_subfuncao}, vigencia{inicio,fim} (AAAA-MM-DD), valor_global, valor_repasse, contrapartida, "
               "metas[{numero,descricao,indicador,quantidade,unidade,valor,etapas[{descricao,valor,inicio,fim}]}], "
               "cronograma_desembolso[{parcela,mes(AAAA-MM),valor}], plano_aplicacao[{natureza_despesa,descricao,"
               "valor}]. Use null quando não houver a informação. Responda só com o JSON.")
    return _json(_chamar(sistema, pseudonimizar(texto)[:60000], max_tokens=4000))
