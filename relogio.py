"""Relógio local independente das consultas meteorológicas."""
from datetime import datetime, timezone
from html import escape
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import streamlit as st


def fuso_cidade(cidade):
    chave = (cidade["latitude"], cidade["longitude"])
    previsao = st.session_state.get("previsao")
    nome = cidade.get("timezone") or "UTC"
    if st.session_state.get("local_painel") == chave and previsao:
        nome = previsao[0].get("timezone") or nome
    try:
        return ZoneInfo(nome), nome, not bool(cidade.get("timezone") or (
            previsao and st.session_state.get("local_painel") == chave and previsao[0].get("timezone")))
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        return timezone.utc, "UTC", True


def hora_referencia(texto, fuso):
    instante = datetime.fromisoformat(texto)
    return instante.replace(tzinfo=fuso) if instante.tzinfo is None else instante.astimezone(fuso)


@st.fragment(run_every="1s")
def relogio(cidade):
    fuso, nome, fallback = fuso_cidade(cidade)
    agora = datetime.now(fuso)
    previsao = st.session_state.get("previsao")
    mesmo_local = st.session_state.get("local_painel") == (cidade["latitude"], cidade["longitude"])
    consulta = st.session_state.get("ultima_tentativa") if mesmo_local else None
    referencia = hora_referencia(previsao[0]["current"]["time"], fuso) if mesmo_local and previsao else None
    itens = [("HORÁRIO ATUAL DA CIDADE", agora.strftime("%d/%m/%Y · %H:%M:%S")),
             ("ÚLTIMA CONSULTA · TENTATIVA", consulta.astimezone(fuso).strftime("%d/%m/%Y · %H:%M:%S") if consulta else "Aguardando consulta"),
             ("REFERÊNCIA METEOROLÓGICA", referencia.strftime("%d/%m/%Y · %H:%M") if referencia else "Indisponível")]
    st.markdown('<div class="clock-grid">' + ''.join(
        '<div><span class="eyebrow">' + rotulo + '</span><strong>' + escape(valor) + '</strong></div>'
        for rotulo, valor in itens) + '</div>', unsafe_allow_html=True)
    if referencia:
        idade = (agora - referencia).total_seconds() / 60
        if idade >= 0:
            aviso = " · Atenção: referência antiga na fonte." if idade >= 60 else ""
            st.caption(f"Referência meteorológica de há {int(idade)} min{aviso} Fuso: {nome}. A idade refere-se ao horário dos dados, não à publicação do modelo.")
        else:
            st.caption(f"A fonte retornou uma referência {int(-idade)} min à frente do relógio local. Fuso: {nome}.")
    else:
        st.caption(f"Relógio local · {nome}. Sem referência meteorológica disponível.")
    if fallback:
        st.caption("Fuso local indisponível: relógio exibido em UTC.")
