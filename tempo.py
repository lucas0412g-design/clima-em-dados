"""Consultas ao Open-Meteo e organização dos dados, sem interface gráfica."""
from datetime import date, datetime
from math import isfinite

import pandas as pd
import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"
INICIO_HISTORICO = date(1940, 1, 1)


class ErroAPI(Exception):
    """Erro que pode ser explicado ao usuário sem encerrar o aplicativo."""


def consultar_json(url, parametros):
    try:
        resposta = requests.get(url, params=parametros, timeout=(5, 15))
        resposta.raise_for_status()
        dados = resposta.json()
    except requests.Timeout as erro:
        raise ErroAPI("A consulta demorou demais. Tente atualizar novamente.") from erro
    except requests.RequestException as erro:
        raise ErroAPI("Não foi possível conectar ao Open-Meteo. Verifique sua internet e tente novamente.") from erro
    except ValueError as erro:
        raise ErroAPI("O serviço retornou uma resposta inválida. Tente novamente.") from erro
    if not isinstance(dados, dict) or dados.get("error"):
        raise ErroAPI("O Open-Meteo não conseguiu atender à consulta.")
    return dados


def buscar_cidades(nome):
    nome = nome.strip()
    if len(nome) < 2:
        return []
    dados = consultar_json(GEOCODING_URL, {"name": nome, "count": 10, "language": "pt", "format": "json"})
    resultados = dados.get("results", [])
    if not isinstance(resultados, list):
        raise ErroAPI("A lista de cidades recebida é inválida.")
    return [cidade for cidade in resultados if isinstance(cidade, dict)
            and all(campo in cidade for campo in ("name", "latitude", "longitude"))]


def nome_local(cidade):
    partes = [cidade.get("name"), cidade.get("admin1"), cidade.get("country")]
    nome = " • ".join(str(parte) for parte in partes if parte)
    return f"{nome} ({cidade['latitude']:.3f}, {cidade['longitude']:.3f})"


def condicao_tempo(codigo):
    codigos = {
        0: "Céu limpo", 1: "Predominantemente limpo", 2: "Parcialmente nublado",
        3: "Nublado", 45: "Nevoeiro", 48: "Nevoeiro com geada",
        51: "Garoa leve", 53: "Garoa moderada", 55: "Garoa intensa",
        56: "Garoa congelante leve", 57: "Garoa congelante intensa",
        61: "Chuva leve", 63: "Chuva moderada", 65: "Chuva forte",
        66: "Chuva congelante leve", 67: "Chuva congelante forte",
        71: "Neve leve", 73: "Neve moderada", 75: "Neve forte", 77: "Grãos de neve",
        80: "Pancadas leves", 81: "Pancadas moderadas", 82: "Pancadas fortes",
        85: "Pancadas de neve leves", 86: "Pancadas de neve fortes",
        95: "Trovoada", 96: "Trovoada com granizo leve", 99: "Trovoada com granizo forte",
    }
    return codigos.get(codigo, "Condição indisponível")


def numero_valido(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool) and isfinite(valor)


def preparar_previsao(dados):
    """Valores ausentes permanecem ausentes: nunca substituímos por zero."""
    try:
        atual = dados["current"]
        datetime.fromisoformat(atual["time"])
        for campo in ("temperature_2m", "relative_humidity_2m", "wind_speed_10m", "weather_code"):
            valor = atual[campo]
            if valor is not None and not numero_valido(valor):
                raise ValueError("Valor atual inválido")
        sensacao = atual.get("apparent_temperature")
        if sensacao is not None and not numero_valido(sensacao):
            raise ValueError("Sensação térmica inválida")
        diario = dados["daily"]
        datas = diario["time"]
        if not isinstance(datas, list) or len(datas) != 7:
            raise ValueError("São necessários sete dias")
        colunas = {"Máxima (°C)": "temperature_2m_max", "Mínima (°C)": "temperature_2m_min",
                   "Chance de chuva (%)": "precipitation_probability_max"}
        tabela = pd.DataFrame({"Data": pd.to_datetime(datas, errors="raise")})
        for nome, campo in colunas.items():
            valores = diario[campo]
            if not isinstance(valores, list) or len(valores) != 7:
                raise ValueError("Lista diária inválida")
            if any(valor is not None and not numero_valido(valor) for valor in valores):
                raise ValueError("Valor diário inválido")
            tabela[nome] = pd.to_numeric(valores, errors="raise")
        codigos = diario["weather_code"]
        if not isinstance(codigos, list) or len(codigos) != 7:
            raise ValueError("Condições diárias inválidas")
        tabela["Condição"] = [condicao_tempo(codigo) for codigo in codigos]
        return tabela
    except (KeyError, TypeError, ValueError, OverflowError) as erro:
        raise ErroAPI("A resposta do serviço contém dados incompletos ou inválidos. Tente atualizar.") from erro


def obter_previsao(cidade):
    parametros = {
        "latitude": cidade["latitude"], "longitude": cidade["longitude"],
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
        "forecast_days": 7, "timezone": "auto", "temperature_unit": "celsius", "wind_speed_unit": "kmh",
    }
    dados = consultar_json(FORECAST_URL, parametros)
    tabela = preparar_previsao(dados)
    return dados, tabela


def analisar_previsao(tabela):
    """Médias das máximas/mínimas e extremos, incluindo todos os empates."""
    analise = {}
    for chave, coluna, operacao in (
        ("quente", "Máxima (°C)", "max"), ("frio", "Mínima (°C)", "min"),
        ("chuva", "Chance de chuva (%)", "max"),
    ):
        serie = tabela[coluna].dropna()
        if serie.empty:
            analise[chave] = None
        else:
            valor = getattr(serie, operacao)()
            datas = tabela.loc[tabela[coluna] == valor, "Data"].dt.strftime("%d/%m").tolist()
            analise[chave] = (float(valor), datas)
    analise["media_maximas"] = tabela["Máxima (°C)"].mean()
    analise["media_minimas"] = tabela["Mínima (°C)"].mean()
    analise["media_chuva"] = tabela["Chance de chuva (%)"].mean()
    return analise


def obter_historico(cidade, dia, hoje_local):
    """Arquivo histórico do Open-Meteo, sem substituir ausências por previsões."""
    if not INICIO_HISTORICO <= dia < hoje_local:
        raise ErroAPI("Escolha uma data entre 01/01/1940 e ontem, no fuso da cidade.")
    modelo = "ecmwf_ifs" if dia >= date(2017, 1, 1) else "era5"
    campos = ("temperature_2m_max", "temperature_2m_min", "weather_code",
              "precipitation_sum", "wind_speed_10m_max")
    parametros = {
        "latitude": cidade["latitude"], "longitude": cidade["longitude"],
        "start_date": dia.isoformat(), "end_date": dia.isoformat(),
        "daily": ",".join(campos), "models": modelo, "timezone": "auto",
        "temperature_unit": "celsius", "wind_speed_unit": "kmh",
    }
    dados = consultar_json(HISTORICAL_URL, parametros)
    try:
        diario = dados["daily"]
        if diario["time"] != [dia.isoformat()]:
            raise ValueError("Data histórica diferente da solicitada")
        resultado = {}
        for campo in campos:
            valores = diario[campo]
            if not isinstance(valores, list) or len(valores) != 1:
                raise ValueError("Resposta diária inválida")
            valor = valores[0]
            if valor is not None and not numero_valido(valor):
                raise ValueError("Valor histórico inválido")
            resultado[campo] = valor
    except (KeyError, TypeError, ValueError) as erro:
        raise ErroAPI("O arquivo histórico ainda não disponibilizou uma resposta válida para esta data. Tente novamente mais tarde.") from erro
    if all(valor is None for valor in resultado.values()):
        raise ErroAPI("Os dados históricos desta data ainda não estão disponíveis na fonte. Tente novamente mais tarde.")
    return resultado, "ECMWF IFS" if modelo == "ecmwf_ifs" else "ERA5"
