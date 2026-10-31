import streamlit as st

import ds_govbr as ds
from banco_ui import aviso_piloto, banco, tag_faixa
from core import banco as B
from core.llm import pseudonimizar
from core.plano_trabalho import cnpj_valido
from ui import rodape

b = banco()
ds.titulo("Cadastro de projetos e demandas",
          "O ente ou a OSC cadastra o projeto; conselhos e coletivos sem CNPJ registram a demanda.",
          "Destinação", "Cadastro")
aviso_piloto()

mun = b["municipios"].sort_values("municipio")
nomes_mun = dict(zip(mun["codigo"], mun["municipio"]))
progs = b["programas"].set_index("id")

aba1, aba2 = st.tabs(["Ente ou OSC: cadastrar projeto", "Demanda cidadã (sem CNPJ)"])

with aba1:
    c1, c2 = st.columns(2)
    cod = c1.selectbox("Município", list(nomes_mun), format_func=nomes_mun.get)
    pid = c2.selectbox("Programa do catálogo", list(progs.index), format_func=lambda k: progs.loc[k, "nome"])
    prog = B.programa(b, pid)
    m = B.municipio(b, cod)
    n, n_txt = B.necessidade(m, prog)
    ds.mensagem("info", f"Lacuna calculada: necessidade {n:.2f}".replace(".", ","), f" ({n_txt}).")

    with st.form("projeto"):
        modo = st.radio("Como o projeto será apresentado", ["Aderir ao modelo padronizado", "Projeto próprio"],
                        horizontal=True, help="O modelo padronizado já vem com projeto, custo de referência e "
                                              "maturidade 4: é o caminho para municípios sem equipe técnica.")
        padrao = modo.startswith("Aderir")
        c3, c4, c5 = st.columns(3)
        custo = c3.number_input("Valor do projeto (R$)", min_value=0.0, step=10000.0,
                                value=float(prog["custo_ref"]), disabled=padrao)
        maturidade = c4.select_slider("Maturidade (projetos próprios)", [1, 2, 3, 4, 5], value=3, disabled=padrao,
                                      help="1 ideia · 2 plano de trabalho · 3 orçamento · 4 projeto executivo e "
                                           "licenças · 5 pronto para licitar")
        benef = c5.number_input("Beneficiários por ano", min_value=0, step=100,
                                value=int(m["populacao"] * 0.15))
        c6, c7 = st.columns(2)
        custeio = c6.number_input("Custeio anual depois de pronto (R$)", min_value=0.0, step=5000.0,
                                  value=float(prog["custeio_ref"]))
        fonte = c7.text_input("Fonte do custeio", "Orçamento municipal (LOA), função 13")
        comprovado = st.checkbox("Anexei a comprovação do custeio (lei orçamentária ou declaração do ordenador)")

        st.markdown("**Quem elaborou o projeto** (declaração obrigatória)")
        c8, c9, c10, c11 = st.columns([2, 2, 2, 1.4])
        tipo_el = c8.selectbox("Elaborador", ["proprio_ente", "consultoria", "osc_parceira"],
                               format_func={"proprio_ente": "Equipe do próprio ente", "consultoria": "Consultoria",
                                            "osc_parceira": "OSC parceira"}.get)
        nome_el = c9.text_input("Nome do elaborador", "")
        cnpj_el = c10.text_input("CNPJ do elaborador", "")
        rem = c11.selectbox("Remuneração", ["sem_custo", "fixa", "exito"],
                            format_func={"sem_custo": "Sem custo", "fixa": "Valor fixo",
                                         "exito": "Por êxito / %"}.get)
        valor_el = st.number_input("Valor pago ao elaborador (R$)", min_value=0.0, step=1000.0)
        gov = st.checkbox("Sou o representante legal e entrei com conta gov.br nível ouro (simulado)", value=True)
        enviar = st.form_submit_button("Enviar para curadoria", type="primary")

    if enviar:
        novo = {
            "id": f"P{len(b['projetos']) + 1:03d}", "codigo_municipio": cod, "programa": pid,
            "titulo": f"{prog['nome'].split(' –')[0].split(' (')[0]} em {nomes_mun[cod]}",
            "modelo_padrao": padrao, "maturidade": 4 if padrao else maturidade,
            "custo": float(prog["custo_ref"]) if padrao else float(custo),
            "custeio_anual": float(custeio), "custeio_comprovado": bool(comprovado), "fonte_custeio": fonte,
            "beneficiarios_ano": int(benef),
            "elaborador": {"tipo": tipo_el, "nome": nome_el or ("Equipe do próprio ente" if tipo_el == "proprio_ente"
                                                                else "(não informado)"),
                           "cnpj": cnpj_el, "remuneracao": rem, "valor": float(valor_el)},
            "representante_gov_br_ouro": bool(gov), "status": "rascunho", "historico": [],
        }
        a = B.avaliar(b, novo)
        bloqueios = [i for i in a["elegibilidade"] if not i["ok"]]
        if tipo_el == "consultoria" and cnpj_el and not cnpj_valido(cnpj_el):
            bloqueios.append({"item": "CNPJ do elaborador", "ok": False, "motivo": "CNPJ inválido."})
        if bloqueios:
            ds.mensagem("danger", "Cadastro bloqueado por linha vermelha ou requisito de elegibilidade.",
                        "<br>" + "<br>".join(f"• {i['item']}: {i['motivo']}" for i in bloqueios))
        else:
            novo["status"] = "em_curadoria"
            novo["historico"].append({"quando": "hoje", "quem": "ente", "acao": "cadastro"})
            b["projetos"].append(novo)
            B.registrar(b, f"Ente ({nomes_mun[cod]})", "cadastrou projeto", novo["id"],
                        {"programa": pid, "valor": novo["custo"], "elaborador": novo["elaborador"]["nome"],
                         "remuneracao_elaborador": rem, "valor_elaborador": float(valor_el)})
            ds.mensagem("success", f"Projeto {novo['id']} enviado para a curadoria do ministério.",
                        f" Prévia: {tag_faixa(a['faixa'], a['estavel'])}")
            pend = [i["item"] for i in a["checklist"] if not i["ok"]]
            if pend:
                ds.mensagem("warning", "A curadoria vai devolver o projeto se estes itens não forem atendidos:",
                            "<br>" + "<br>".join(f"• {x}" for x in pend))

with aba2:
    ds.mensagem("info", "Para quem não tem CNPJ.",
                " Conselhos municipais, coletivos e comunidades registram a necessidade. A demanda fica pública e "
                "aguarda o ente transformá-la em projeto. Não informe CPF, telefone ou dados de pessoas.")
    with st.form("demanda"):
        c1, c2 = st.columns(2)
        codd = c1.selectbox("Município ", list(nomes_mun), format_func=nomes_mun.get)
        pidd = c2.selectbox("Equipamento que falta", list(progs.index), format_func=lambda k: progs.loc[k, "nome"])
        quem = st.text_input("Quem registra (conselho, coletivo ou comunidade)", "Conselho Municipal de Cultura")
        desc = st.text_area("Descreva a necessidade", max_chars=600)
        ok = st.form_submit_button("Registrar demanda", type="primary")
    if ok and desc.strip():
        d = {"municipio": nomes_mun[codd], "programa": pidd, "quem": quem.strip()[:80],
             "descricao": pseudonimizar(desc.strip()), "situacao": "aguardando o ente"}
        b["demandas"].append(d)
        B.registrar(b, quem.strip()[:80], "registrou demanda", nomes_mun[codd], {"programa": pidd})
        ds.mensagem("success", "Demanda registrada e publicada.", " Dados pessoais foram mascarados.")
    if b["demandas"]:
        st.dataframe(b["demandas"], hide_index=True, use_container_width=True)
rodape()
