"""Painel escolar: execute com py -m streamlit run app.py."""
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from time import monotonic
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd
import plotly.express as px
import streamlit as st

from relogio import relogio, fuso_cidade
from exploracao import explorar_tempo

from visual import icone_tempo, cartoes_dias, estilizar_grafico
from temas import TEMAS, ROTULOS_TEMAS, css_tema, paleta_tema, tabela_estilizada

from tempo import ErroAPI, analisar_previsao, buscar_cidades, condicao_tempo, nome_local, obter_previsao

st.set_page_config(page_title="Clima em Dados", page_icon="⛅", layout="wide", initial_sidebar_state="collapsed")
st.session_state.setdefault("tema_visual", "Escuro")
if st.session_state.tema_visual not in TEMAS:
    st.session_state.tema_visual = "Escuro"
with st.container(key="seletor_tema"):
    st.radio("Tema visual", list(TEMAS), format_func=ROTULOS_TEMAS.get,
             key="tema_visual", horizontal=True, label_visibility="collapsed")
tema = st.session_state.tema_visual
estilos = (Path(__file__).parent / "assets" / "dashboard.css").read_text(encoding="utf-8")
st.markdown('<style>' + estilos + css_tema(tema) + '</style><span class="theme-marker" id="clima-theme" data-theme="' + paleta_tema(tema)["slug"] + '"></span>', unsafe_allow_html=True)
st.markdown('<div class="brand-header"><div class="brand-mark">' + icone_tempo(2) + '</div><div><span class="eyebrow">SEU HORIZONTE, EM DADOS</span><h1>Clima em Dados</h1><p>O tempo agora. As possibilidades dos próximos dias.</p></div></div>', unsafe_allow_html=True)

def alternar_pesquisa():
    st.session_state.pesquisa_aberta = not st.session_state.get("pesquisa_aberta", False)


with st.container(key="busca_mobile"):
    st.button("Fechar pesquisa" if st.session_state.get("pesquisa_aberta") else "Buscar cidade",
              icon=":material/search:", key="abrir_busca_mobile", width="stretch",
              on_click=alternar_pesquisa)

# Pesquisa única no conteúdo principal; sem widgets na barra lateral.
area_pesquisa = st.container(key="pesquisa_mobile")
with area_pesquisa:
    pesquisar = False
    pesquisa = ""
    if st.session_state.get("pesquisa_aberta"):
        st.header("Explore um lugar")
        st.caption("Encontre sua cidade e selecione o resultado correto.")
        with st.form("pesquisa"):
            pesquisa = st.text_input("Nome da cidade", placeholder="Ex.: São Paulo", key="texto_pesquisa", persist_state="session")
            pesquisar = st.form_submit_button("Pesquisar", type="primary", width="stretch")
    if pesquisar:
        if len(pesquisa.strip()) < 2:
            st.warning("Digite pelo menos duas letras.")
        else:
            try:
                with st.spinner("Buscando cidades…"):
                    resultados = buscar_cidades(pesquisa)
                if resultados:
                    anterior = st.session_state.get("local_escolhido")
                    indice = next((i for i, c in enumerate(resultados)
                                   if (c["latitude"], c["longitude"]) == anterior), 0)
                    st.session_state.cidades = resultados
                    st.session_state.indice_local = indice
                    st.session_state.cidade_selecionada = indice
                else:
                    st.warning("Nenhuma cidade encontrada. Confira o nome ou tente uma cidade próxima.")
            except ErroAPI as erro:
                st.error(str(erro))
    cidades = st.session_state.get("cidades", [])
    cidade = None
    if cidades:
        # Estado durável mesmo quando a área de pesquisa está fechada.
        st.session_state.setdefault("indice_local", st.session_state.get("cidade_selecionada", 0))
        if not 0 <= st.session_state.indice_local < len(cidades):
            st.session_state.indice_local = 0
        st.session_state.cidade_selecionada = st.session_state.indice_local

        def salvar_local():
            st.session_state.indice_local = st.session_state.cidade_selecionada

        if st.session_state.get("pesquisa_aberta"):
            indice = st.selectbox("Selecione o local correto", range(len(cidades)),
                                  format_func=lambda i: nome_local(cidades[i]), key="cidade_selecionada",
                                  on_change=salvar_local, persist_state="session")
        else:
            indice = st.session_state.indice_local
        cidade = cidades[indice]
        st.session_state.local_escolhido = (cidade["latitude"], cidade["longitude"])
    if cidade:
        st.markdown('<div class="location-detail"><span class="eyebrow">LOCAL SELECIONADO</span><strong>' + escape(str(cidade["name"])) + '</strong><span>' + escape(" · ".join(str(cidade.get(campo, "")) for campo in ("admin1", "country") if cidade.get(campo))) + '</span><small>' + f'{cidade["latitude"]:.3f}, {cidade["longitude"]:.3f}' + '</small></div>', unsafe_allow_html=True)
    st.markdown('<div class="sync-note"><span class="status-dot"></span> Consulta automática · 60 s</div>', unsafe_allow_html=True)
    st.caption("A consulta ocorre enquanto esta sessão estiver aberta e conectada. Navegadores podem limitar abas em segundo plano.")
    st.markdown("[Fonte: Open-Meteo](https://open-meteo.com/) · [Locais: GeoNames](https://www.geonames.org/)")


def formatar_numero(valor, unidade=""):
    if valor is None or pd.isna(valor):
        return "Indisponível"
    return f"{valor:.1f}".replace(".", ",") + unidade


def formatar_consulta(instante, fuso):
    try:
        return instante.astimezone(ZoneInfo(fuso)).strftime("%d/%m/%Y às %H:%M:%S") + f" ({fuso})"
    except (ZoneInfoNotFoundError, ValueError):
        return instante.strftime("%d/%m/%Y às %H:%M:%S UTC")


@st.fragment(run_every="60s")
def painel(cidade):
    # Ler em cada execução do fragmento preserva o tema nas consultas automáticas.
    tema = st.session_state.get("tema_visual", "Escuro")
    paleta = paleta_tema(tema)
    chave = (cidade["latitude"], cidade["longitude"])
    if st.session_state.get("local_painel") != chave:
        # Limpa a previsão anterior para nunca misturar dados de cidades diferentes.
        st.session_state.local_painel = chave
        st.session_state.previsao = None
        st.session_state.ultima_tentativa = None
        st.session_state.ultimo_sucesso = None
        st.session_state.instante_consulta = 0
        st.session_state.erro_consulta = None

    cabecalho, acao = st.columns([3, 1], vertical_alignment="center", wrap=True)
    with cabecalho:
        st.markdown('<div class="section-heading"><span class="eyebrow">VISÃO GERAL</span><h2>' + escape(str(cidade["name"])) + '</h2><p>' + escape(" · ".join(str(cidade.get(campo, "")) for campo in ("admin1", "country") if cidade.get(campo))) + '</p></div>', unsafe_allow_html=True)
    with acao:
        manual = st.button("↻ Atualizar agora", width="stretch")
    precisa_consultar = (st.session_state.ultima_tentativa is None or manual
                         or monotonic() - st.session_state.instante_consulta >= 59)
    if precisa_consultar:
        st.session_state.instante_consulta = monotonic()
        with st.spinner("Consultando a previsão…"):
            try:
                dados, tabela = obter_previsao(cidade)
                st.session_state.previsao = (dados, tabela)
                st.session_state.ultimo_sucesso = datetime.now(timezone.utc)
                st.session_state.erro_consulta = None
            except ErroAPI as erro:
                st.session_state.erro_consulta = str(erro)
            finally:
                st.session_state.ultima_tentativa = datetime.now(timezone.utc)

    if st.session_state.erro_consulta:
        st.error(st.session_state.erro_consulta)
        if st.session_state.previsao:
            st.warning("Exibindo a última resposta válida desta cidade. Os dados abaixo podem estar desatualizados.")
    if not st.session_state.previsao:
        st.caption("Última tentativa: " + formatar_consulta(st.session_state.ultima_tentativa, cidade.get("timezone", "UTC")))
        st.info("Ainda não há dados disponíveis. Use Atualizar agora ou aguarde a próxima consulta automática.")
        explorar_tempo(cidade, manual=manual)
        return

    dados, tabela = st.session_state.previsao
    atual = dados["current"]
    fuso = dados.get("timezone", "UTC")
    horario_dados = datetime.fromisoformat(atual["time"]).strftime("%d/%m/%Y às %H:%M")
    destaque, detalhes = st.columns([2.2, 1], gap="medium", wrap=True)
    with destaque:
        with st.container(key="tempo_destaque_indisponivel" if atual["temperature_2m"] is None else "tempo_destaque"):
            st.markdown('<div class="weather-heading"><span class="eyebrow">TEMPO AGORA</span>' + icone_tempo(atual["weather_code"]) + '</div>', unsafe_allow_html=True)
            st.markdown('<div class="hero-city">' + escape(str(cidade["name"])) + '</div>', unsafe_allow_html=True)
            st.metric("Temperatura", formatar_numero(atual["temperature_2m"], " °C"))
            st.markdown('<div class="current-condition">' + escape(condicao_tempo(atual["weather_code"])) + '</div>', unsafe_allow_html=True)
            st.caption(f"Horário dos dados atuais: {horario_dados} ({fuso})")
    with detalhes:
        with st.container(key="sensacao"):
            st.markdown('<span class="eyebrow">COMO O TEMPO É SENTIDO</span>', unsafe_allow_html=True)
            st.metric("Sensação térmica", formatar_numero(atual.get("apparent_temperature"), " °C"))
        with st.container(key="umidade"):
            st.markdown('<span class="eyebrow">ÁGUA NO AR</span>', unsafe_allow_html=True)
            st.metric("Umidade relativa", formatar_numero(atual["relative_humidity_2m"], " %"))
        with st.container(key="vento"):
            st.markdown('<span class="eyebrow">EM MOVIMENTO</span>', unsafe_allow_html=True)
            st.metric("Velocidade do vento", formatar_numero(atual["wind_speed_10m"], " km/h"))
    st.markdown('<div class="sync-note"><span class="status-dot"></span> Consulta automática a cada 60 segundos</div>', unsafe_allow_html=True)
    with st.expander("Horários de consulta e fonte dos dados"):
        st.caption("Última consulta (tentativa): " + formatar_consulta(st.session_state.ultima_tentativa, fuso)
                   + " • Última consulta bem-sucedida: " + formatar_consulta(st.session_state.ultimo_sucesso, fuso))
        st.write("O aplicativo consulta a API a cada 60 segundos. Isso não significa que a fonte publica novos dados a cada minuto; respostas consecutivas podem ser iguais. As condições atuais são estimativas de modelos meteorológicos do Open-Meteo.")

    explorar_tempo(cidade, tabela, manual=manual)

    st.markdown("### Previsão de 7 dias")
    st.caption("Inclui hoje e os próximos seis dias, no fuso do local. Temperaturas máxima e mínima em °C. Chance de chuva: probabilidade máxima diária de precipitação (também pode incluir neve).")
    if tabela.select_dtypes("number").isna().any().any():
        st.warning("Há valores indisponíveis na fonte. Eles ficam em branco nos gráficos e são excluídos das médias e dos extremos.")
    dias_exibicao = tabela.copy()
    dias_exibicao.attrs["hoje_local"] = datetime.now(fuso_cidade(cidade)[0]).date()
    st.markdown(cartoes_dias(dias_exibicao, dados["daily"]["weather_code"]), unsafe_allow_html=True)
    aba_graficos, aba_tabela = st.tabs(["Evolução da semana", "Dados detalhados"])
    with aba_graficos:
        coluna_temperatura, coluna_chuva = st.columns([1.3, 1], gap="medium", wrap=True)
        with coluna_temperatura:
            with st.container(key="grafico_temperatura"):
                st.markdown("#### Temperaturas")
                st.caption("Máximas e mínimas previstas · °C")
                temperaturas = tabela.melt(id_vars="Data", value_vars=["Máxima (°C)", "Mínima (°C)"],
                                           var_name="Temperatura", value_name="Graus Celsius")
                figura = px.line(temperaturas, x="Data", y="Graus Celsius", color="Temperatura", markers=True,
                                 color_discrete_sequence=[paleta["maxima"], paleta["minima"]])
                estilizar_grafico(figura, "°C", tema)
                figura.update_traces(line_width=3, marker_size=7, connectgaps=False,
                                     hovertemplate="%{y:.1f} °C<extra>%{fullData.name}</extra>")
                st.plotly_chart(figura, width="stretch", theme=None,
                                config={"displayModeBar": False, "responsive": True})
        with coluna_chuva:
            with st.container(key="grafico_chuva"):
                st.markdown("#### Chance de chuva")
                st.caption("Probabilidade máxima diária · %")
                chuva = px.bar(tabela, x="Data", y="Chance de chuva (%)", color_discrete_sequence=[paleta["rain"]])
                estilizar_grafico(chuva, "%", tema)
                chuva.update_yaxes(range=[0, 105], tickvals=[0, 25, 50, 75, 100], ticksuffix="%")
                chuva.update_traces(marker_line_width=0, marker_opacity=0.85,
                                    hovertemplate="%{y:.1f}%<extra>Precipitação</extra>")
                chuva.update_layout(bargap=0.48)
                st.plotly_chart(chuva, width="stretch", theme=None,
                                config={"displayModeBar": False, "responsive": True})
    with aba_tabela:
        exibicao = tabela.copy()
        exibicao["Data"] = exibicao["Data"].dt.strftime("%d/%m/%Y")
        st.dataframe(tabela_estilizada(exibicao, tema), hide_index=True, width="stretch",
                     column_config={nome: st.column_config.NumberColumn(nome, format="%.1f")
                                    for nome in ("Máxima (°C)", "Mínima (°C)", "Chance de chuva (%)")})

    st.markdown("### O que os dados mostram")
    analise = analisar_previsao(tabela)
    colunas = st.columns(3, wrap=True)
    colunas[0].metric("Média das máximas", formatar_numero(analise["media_maximas"], " °C"))
    colunas[1].metric("Média das mínimas", formatar_numero(analise["media_minimas"], " °C"))
    colunas[2].metric("Média das chances de chuva", formatar_numero(analise["media_chuva"], " %"))
    extremos = st.columns(3, wrap=True)
    for coluna, (chave, titulo, unidade) in zip(extremos, (("quente", "🔥 Dia(s) mais quente(s)", " °C"),
                                   ("frio", "❄️ Dia(s) mais frio(s)", " °C"),
                                   ("chuva", "☔ Maior chance de chuva", " %"))):
        extremo = analise[chave]
        valor_texto = "Indisponível" if extremo is None else formatar_numero(extremo[0], unidade)
        datas_texto = "Sem valores disponíveis na fonte" if extremo is None else ", ".join(extremo[1])
        with coluna:
            st.markdown('<div class="extreme-card"><span>' + escape(titulo) + '</span><strong>' + escape(valor_texto) + '</strong><p>' + escape(datas_texto) + '</p></div>', unsafe_allow_html=True)
    with st.expander("Como esta análise é feita?"):
        st.write("Calculamos a média aritmética das máximas, das mínimas e das probabilidades diárias disponíveis. O dia mais quente tem a maior máxima; o mais frio, a menor mínima. Em caso de empate, mostramos todos os dias. A média das probabilidades não é a probabilidade de chover na semana. Não calculamos uma temperatura média diária a partir dos extremos.")
        st.write("A previsão vem diretamente da API Open-Meteo. Este projeto organiza, visualiza e analisa esses dados; não treina um modelo próprio de inteligência artificial. A previsão pode mudar e tem incertezas.")
    st.caption("Dados meteorológicos: Open-Meteo (CC BY 4.0) • Localização: GeoNames • https://open-meteo.com/")


if cidade:
    relogio(cidade)
    painel(cidade)
else:
    st.markdown('<div class="welcome-card"><span class="eyebrow">UM NOVO OLHAR PARA O TEMPO</span>' + icone_tempo(2) + '<h2>Qual é o clima<br>do seu próximo dia?</h2><p>Pesquise uma cidade para explorar as condições atuais e a previsão dos próximos sete dias.</p><div class="welcome-tags"><span>Dados reais</span><span>7 dias de previsão</span><span>Consulta a cada 60 s</span></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="intro-grid"><div><span class="eyebrow">01 / ACOMPANHE</span><h3>O presente, em detalhe</h3><p>Temperatura, umidade e vento em uma visão clara do seu lugar.</p></div><div><span class="eyebrow">02 / EXPLORE</span><h3>Uma semana à frente</h3><p>Compare as temperaturas e veja a probabilidade diária de precipitação.</p></div><div><span class="eyebrow">03 / ENTENDA</span><h3>Os números do clima</h3><p>Médias e extremos para interpretar a previsão com mais contexto.</p></div></div>', unsafe_allow_html=True)
    st.caption("Fonte: Open-Meteo · Localização: GeoNames · Condições estimadas por modelos meteorológicos. A atualização automática começa após selecionar uma cidade.")
