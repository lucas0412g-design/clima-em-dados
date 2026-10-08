"""Navegação por dia; reutiliza a previsão e consulta só o histórico necessário."""
from datetime import datetime, timedelta, timezone
from html import escape
from time import monotonic

import pandas as pd
import streamlit as st

from relogio import fuso_cidade
from tempo import ErroAPI, INICIO_HISTORICO, condicao_tempo, obter_historico


def numero(valor, unidade):
    return "Indisponível" if valor is None or pd.isna(valor) else f"{valor:.1f}".replace(".", ",") + unidade


def calendario(rotulo, chave, minimo, maximo, padrao):
    valor = st.session_state.get(chave)
    if valor is None or not minimo <= valor <= maximo:
        st.session_state[chave] = padrao
    return st.date_input(rotulo, key=chave, min_value=minimo, max_value=maximo, format="DD/MM/YYYY")


def explorar_tempo(cidade, tabela=None, manual=False):
    fuso, nome_fuso, _ = fuso_cidade(cidade)
    hoje = datetime.now(fuso).date()
    st.markdown("### Explore o tempo")
    st.caption("Condições atuais, arquivo histórico e previsão: cada dia com sua origem identificada.")
    modo = st.radio("Período", ["Hoje", "Histórico", "Previsão"], horizontal=True, key="explorar_periodo")
    if modo == "Histórico":
        dia = calendario("Escolha uma data histórica", "data_historica", INICIO_HISTORICO,
                         hoje - timedelta(days=1), hoje - timedelta(days=1))
        st.caption("Arquivo disponível desde 1940. Datas recentes podem ainda não ter dados publicados; não usamos previsão para preencher o histórico.")
    elif modo == "Previsão":
        datas = [] if tabela is None else sorted({data.date() for data in tabela["Data"] if data.date() > hoje})
        if not datas:
            st.info("Não há datas futuras disponíveis na resposta atual. Use Atualizar agora.")
            return
        dia = calendario("Escolha um dia da previsão", "data_prevista", datas[0], datas[-1], datas[0])
        if dia not in datas:
            st.info("Esta data não está disponível na previsão recebida.")
            return
    else:
        dia = hoje
    classe = {"Hoje": "today", "Histórico": "history", "Previsão": "forecast"}[modo]
    origem = {"Hoje": "HOJE · PREVISÃO DO DIA", "Histórico": "HISTÓRICO · ARQUIVO DA FONTE", "Previsão": "PREVISÃO · PODE MUDAR"}[modo]
    st.markdown('<div class="explore-date ' + classe + '"><span class="eyebrow">' + origem + '</span><strong>' + dia.strftime("%d/%m/%Y") + '</strong><span>' + escape(nome_fuso) + '</span></div>', unsafe_allow_html=True)
    if modo == "Histórico":
        cache = st.session_state.setdefault("historico_por_dia", {})
        chave = (cidade["latitude"], cidade["longitude"], dia.isoformat())
        entrada = cache.get(chave)
        validade = 21600 if entrada and not entrada.get("erro") else 300
        if manual or entrada is None or monotonic() - entrada["instante"] >= validade:
            try:
                with st.spinner("Consultando o arquivo histórico…"):
                    valores, modelo = obter_historico(cidade, dia, hoje)
                entrada = {"valores": valores, "modelo": modelo, "erro": None}
            except ErroAPI as erro:
                entrada = {"erro": str(erro)}
            entrada.update(instante=monotonic(), consulta=datetime.now(timezone.utc))
            cache[chave] = entrada
        if entrada["erro"]:
            st.info(entrada["erro"])
            st.caption("A disponibilidade depende do arquivo Open-Meteo. Atualizar agora tenta novamente; tentativas automáticas de histórico indisponível têm intervalo de 5 minutos.")
            return
        valores = entrada["valores"]
        condicao = condicao_tempo(valores["weather_code"])
        metricas = [("Máxima histórica", valores["temperature_2m_max"], " °C"),
                    ("Mínima histórica", valores["temperature_2m_min"], " °C"),
                    ("Precipitação acumulada", valores["precipitation_sum"], " mm"),
                    ("Vento máximo", valores["wind_speed_10m_max"], " km/h")]
        st.caption("Histórico Open-Meteo · " + entrada["modelo"] + ". Estimativas do arquivo meteorológico, não medições de estação. Consulta: " + entrada["consulta"].astimezone(fuso).strftime("%d/%m/%Y às %H:%M:%S"))
    else:
        linhas = tabela.loc[tabela["Data"].dt.date == dia] if tabela is not None else pd.DataFrame()
        if linhas.empty:
            st.info("Não há previsão desta data na resposta atual. Use Atualizar agora.")
            return
        linha = linhas.iloc[0]
        condicao = linha["Condição"]
        metricas = [("Máxima prevista", linha["Máxima (°C)"], " °C"),
                    ("Mínima prevista", linha["Mínima (°C)"], " °C"),
                    ("Chance de chuva", linha["Chance de chuva (%)"], " %")]
        st.caption("Resumo diário previsto. A sensação térmica no painel acima corresponde apenas à referência atual.")
    st.write(condicao)
    for indice, (coluna, (rotulo, valor, unidade)) in enumerate(zip(st.columns(len(metricas), wrap=True), metricas)):
        with coluna:
            with st.container(key=f"resumo_diario_{indice}"):
                st.metric(rotulo, numero(valor, unidade))
