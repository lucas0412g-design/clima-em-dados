# Clima em dados — trabalho escolar

Programa em Python para o enunciado: “Faça um programa capaz de analisar e realizar previsão do tempo. Apresente com atualização em tempo real.”

Interface em português feita com Streamlit; pesquisa de cidades e previsão real da API Open-Meteo, sem chave. A previsão é produzida pela fonte meteorológica. Este projeto não treina IA nem cria dados meteorológicos.

## Instalar e executar no VS Code (Windows / PowerShell)

Use Python 3.13, versão utilizada na verificação local, e abra o terminal do VS Code na pasta `climas`. Use `py` caso `python` abra a Microsoft Store.

```powershell
cd climas
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Não é necessário ativar o ambiente virtual; os comandos usam seu executável diretamente. Abra http://localhost:8501 se o navegador não abrir sozinho. Mantenha o terminal rodando; para encerrar, pressione Ctrl+C.

Se já abriu diretamente a pasta `climas` no VS Code, omita o comando `cd climas`.

Em Linux/macOS:

```bash
cd climas
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

## Usar

1. Clique em **Buscar cidade** no topo, digite uma cidade e clique em **Pesquisar**.
2. Selecione a cidade correta pelo nome, região, país e coordenadas.
3. Observe temperatura, umidade, vento e condição atual.
4. Explore gráficos e tabela da previsão de sete dias (hoje + seis dias).
5. Leia as médias e os dias extremos; empates são apresentados juntos.
6. Use **Atualizar agora** ou mantenha a sessão aberta para novas consultas a cada 60 segundos.

É necessário acesso à internet aos domínios `geocoding-api.open-meteo.com`, `api.open-meteo.com` e `archive-api.open-meteo.com`. Não há previsão fictícia de demonstração no aplicativo. Em falhas, ele mostra uma mensagem e mantém a última resposta válida da mesma cidade, marcada como possivelmente desatualizada. Uma cidade nova nunca herda a previsão anterior.

## Atualização e horários

`st.fragment(run_every="60s")` atualiza o painel enquanto a sessão está ativa e conectada, sem repetir a pesquisa de cidades. O botão manual faz uma consulta imediata, sem cache de previsão. Abas em segundo plano e suspensão do computador podem atrasar a atualização.

Consultar a cada minuto **não significa que a fonte publica dados novos a cada minuto**. O Open-Meteo usa modelos meteorológicos com ciclos próprios de atualização; respostas consecutivas podem ser iguais. As condições atuais são estimativas baseadas em modelos, não uma leitura direta de um sensor instalado pelo projeto.

O painel distingue o horário dos dados atuais (`current.time`), a última tentativa de consulta e a última consulta bem-sucedida. Os horários são exibidos no fuso retornado pela API para o local escolhido. O horário dos dados não representa a hora em que o modelo foi publicado.

## Análise de dados

- Médias aritméticas das máximas, mínimas e probabilidades diárias disponíveis.
- Dia mais quente: maior temperatura máxima prevista.
- Dia mais frio: menor temperatura mínima prevista.
- Maior chance de chuva: maior probabilidade máxima diária de precipitação, que também pode incluir neve.
- A média das probabilidades diárias não é a chance de chover na semana.
- Valores ausentes não viram zero: são omitidos das médias/extremos e indicados no painel.

A previsão tem incertezas e pode mudar. Não calculamos temperatura média diária usando apenas máximas e mínimas.

## Arquivos

- `app.py`: interface, atualização e estado da sessão.
- `tempo.py`: consultas HTTP, códigos WMO, tabela e cálculos.
- `requirements.txt`: dependências.
- `.streamlit/config.toml`: tema e configuração.
- `tests/test_tempo.py`: testes de cálculos e tratamento de erros, com respostas simuladas apenas nos testes.
- `tests/test_interface.py`: pesquisa, gráficos, tabela, atualização e recuperação de falhas com Streamlit AppTest.
- `tests/verificar_api.py`: consulta real opcional para testar os dois serviços.
- `tests/verificar_servidor.py`: inicia um servidor temporário na porta 18501, verifica sua saúde e o encerra.
- `VERIFICACAO.md`: resultados das verificações realizadas durante a implementação.

## Verificar

No terminal, dentro de `clima_escolar`, após instalar as dependências:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tests/verificar_api.py
.\.venv\Scripts\python.exe tests/verificar_servidor.py
```

O segundo comando exige internet e valida a busca por São Paulo e sete dias de previsão real. Para conferir a interface manualmente, teste cidades homônimas, um nome inexistente, o botão de atualização, a atualização após um minuto e a perda/restauração da conexão. Não é necessário instalar pytest.

## Fontes

- Previsão e condições atuais: [Open-Meteo Weather Forecast API](https://open-meteo.com/en/docs).
- Pesquisa de locais: [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api), com dados do [GeoNames](https://www.geonames.org/).
- Atualização da interface: [Streamlit — st.fragment](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment).
- Dados do Open-Meteo sob [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Uso escolar não comercial sem chave de API, sujeito aos limites de uso da fonte.

## Visual do dashboard

Três temas visuais (Claro, Escuro e Futurista), cartão de temperatura atual,
ícones vetoriais locais por condição WMO e cartões dos sete dias. Os gráficos e os
cartões se reorganizam em telas pequenas. O seletor preserva nome, região, país e
coordenadas; os detalhes completos do local também aparecem na barra lateral.

- `assets/dashboard.css`: estilos e regras para desktop e celular.
- `visual.py`: ícones, cartões diários e tema dos gráficos, sem consultar a API.

Os horários das consultas ficam em **Horários de consulta e fonte dos dados**.
A tabela fica na aba **Dados detalhados**. A tabela mantém sua rolagem interna
quando necessária para ler todas as colunas em celulares.

Execute `.\.venv\Scripts\python.exe -m streamlit run app.py` e abra
http://localhost:8501. Se o aplicativo já estiver aberto, recarregue a página;
reinicie o servidor se o tema anterior permanecer carregado.

## Escolher um tema

Use **☀️ Claro | 🌙 Escuro | 🚀 Futurista** no topo do dashboard.
Escuro é o padrão. A escolha é mantida em `st.session_state.tema_visual` durante
esta sessão; uma sessão nova volta ao Escuro. O controle usa a reexecução normal
do Streamlit, sem navegar ou recarregar o documento do navegador. A cidade e a
previsão permanecem carregadas. Uma consulta meteorológica só ocorre quando o
intervalo estiver vencido ou quando o usuário clicar em Atualizar agora.

As paletas ficam em `temas.py`, os estilos em `assets/dashboard.css` e os gráficos
em `visual.py`. A configuração global continua escura como base: **não é escrita
nem alterada na troca de tema**, evitando interferência entre sessões.

Os controles são estilizados por test IDs, papéis ARIA e chaves explícitas dos
containers. O Streamlit 1.65 usa React Aria para os seletores; há também regras para
os controles Base Web das versões anteriores. Não são usadas classes Emotion
geradas automaticamente.

A tabela conserva ordenação, seleção, exportação e rolagem nativas. As células
usam pandas Styler. Como o Streamlit não oferece uma API pública para alterar o
tema do canvas da tabela por sessão, no Claro o CSS converte apenas os canvases
com `invert(1) hue-rotate(180deg)`; o cabeçalho também acompanha o modo claro.
Essa conversão pode mudar levemente as cores dos emojis desenhados na tabela.
As mensagens, controles e os cartões externos usam a paleta diretamente.

O Futurista combina vidro, grade sutil, gradientes e um brilho suave no símbolo
principal. A preferência `prefers-reduced-motion` desativa brilho animado e
transições. Não há animações pesadas ou dependências novas.

Verificação opcional no Windows com Edge e o ambiente existente:

```powershell
.\.venv\Scripts\python.exe tests/verificar_temas_navegador.py
```

Esse script inicia e encerra seu próprio servidor temporário na porta 18502 e
verifica os três temas com dados reais. Salva capturas em `tests/artifacts/temas`.
O teste completo espera um ciclo real de atualização automática; `--skip-timer`
omite essa espera. Os testes normais não exigem navegador nem acesso à internet.


## Preparação para Streamlit Community Cloud

Esta etapa não publica o aplicativo. Quando autorizado, envie o conteúdo do projeto ao repositório GitHub, preservando esta estrutura:

- `app.py`, `tempo.py`, `visual.py`, `temas.py`, `relogio.py` e `exploracao.py`.
- `requirements.txt` na mesma pasta de `app.py`.
- `assets/dashboard.css` e `.streamlit/config.toml`, mantendo os nomes e maiúsculas/minúsculas.

Escolha `app.py` como arquivo principal e Python 3.13 nas opções avançadas da publicação. Se o projeto estiver em uma subpasta do repositório, informe o caminho correspondente para `app.py`. O Streamlit está fixado na versão 1.65.0 usada localmente para preservar os recursos e estilos existentes.

O aplicativo não utiliza caminhos absolutos do Windows, ambiente virtual local, chaves de API nem programas externos. O CSS é localizado a partir de `__file__` com `pathlib`. Não é necessário `packages.txt`. Os dados dependem de acesso à internet ao Open-Meteo.

Não envie `.venv`, caches, arquivos `.env` ou `.streamlit/secrets.toml`; o `.gitignore` protege esses arquivos. Mantenha `.streamlit/config.toml` no repositório, pois ele faz parte do tema. Caso segredos sejam necessários no futuro, configure-os no painel do Community Cloud.

A inicialização local não substitui uma validação no servidor Linux após a publicação.
