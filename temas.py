"""Paletas por sessão: CSS e Plotly usam a mesma identidade visual.

Não altera config.toml em tempo de execução nem configurações globais do servidor.
"""
TEMAS = {
    "Claro": {
        "slug": "claro", "scheme": "light", "ink": "#172c46", "muted": "#52667e",
        "cyan": "#08789b", "violet": "#7250b7", "line": "#dbe6ef",
        "page": "#f5f8fc", "sidebar": "#ffffff", "surface": "#ffffff", "widget": "#edf3f8",
        "hero": "linear-gradient(130deg,#ffffff,#e9f5fc)", "welcome": "linear-gradient(125deg,#ffffff,#e5f3fe)",
        "card": "#ffffff", "today": "#e7f6fc", "extreme": "#ffffff",
        "shadow": "0 8px 26px rgba(30,65,100,.07)", "header": "rgba(245,248,252,.96)",
        "button": "#08789b", "button_text": "#ffffff", "hover": "#e3f0f8", "alert": "#e8f1fa",
        "tag": "#eaf5fb", "icon_cloud": "#d9eafa", "icon_line": "#3b6b93", "sun": "#b57711",
        "grid": "rgba(64,101,134,.14)", "tooltip": "#ffffff", "maxima": "#087fba", "minima": "#7250b7",
        "rain": "#1585b3", "blur": "0px", "glow": "none", "table_filter": "invert(1) hue-rotate(180deg)",
    },
    "Escuro": {
        "slug": "escuro", "scheme": "dark", "ink": "#F5F5F5", "muted": "#B4B4BD",
        "cyan": "#E3E3E8", "violet": "#C7C7CF", "line": "#38383F",
        "page": "#101012", "sidebar": "#18181B", "surface": "#222226", "widget": "#29292E",
        "hero": "#222226", "welcome": "#222226", "card": "#222226", "today": "#29292E",
        "extreme": "#222226", "shadow": "0 8px 28px rgba(0,0,0,.18)",
        "header": "rgba(16,16,18,.96)", "button": "#29292E", "button_text": "#F5F5F5",
        "hover": "#313137", "alert": "#222226", "tag": "#29292E",
        "icon_cloud": "#313136", "icon_line": "#D4D4DC", "sun": "#f3cf83",
        "grid": "rgba(180,180,189,.14)", "tooltip": "#222226",
        "maxima": "#E8BA74", "minima": "#B7A3D8", "rain": "#94BDAC",
        "blur": "0px", "glow": "none", "table_filter": "grayscale(1)",
    },
    "Futurista": {
        "slug": "futurista", "scheme": "dark", "ink": "#edfaff", "muted": "#abc0d9",
        "cyan": "#57f2ed", "violet": "#c2a0ff", "line": "rgba(104,177,255,.33)",
        "page": "radial-gradient(ellipse at 85% 5%,rgba(112,55,204,.22),transparent 50%),radial-gradient(ellipse at 5% 45%,rgba(0,183,214,.12),transparent 55%),repeating-linear-gradient(0deg,transparent,transparent 63px,rgba(75,152,212,.035) 64px),repeating-linear-gradient(90deg,transparent,transparent 63px,rgba(75,152,212,.035) 64px),#050914",
        "sidebar": "rgba(8,15,32,.96)", "surface": "#0e1930", "widget": "#101d35",
        "hero": "linear-gradient(125deg,rgba(15,51,74,.82),rgba(40,24,75,.66))",
        "welcome": "linear-gradient(125deg,rgba(12,46,68,.82),rgba(48,22,83,.72))",
        "card": "rgba(14,25,48,.76)", "today": "linear-gradient(140deg,rgba(8,79,89,.65),rgba(61,32,110,.65))",
        "extreme": "linear-gradient(145deg,rgba(24,34,67,.8),rgba(37,22,69,.7))",
        "shadow": "0 10px 34px rgba(0,0,0,.24)", "header": "rgba(5,9,20,.96)",
        "button": "#286281", "button_text": "#f0fdff", "hover": "#192e4c", "alert": "#14233f",
        "tag": "rgba(17,70,84,.42)", "icon_cloud": "#172847", "icon_line": "#74edf3", "sun": "#d6b4ff",
        "grid": "rgba(89,217,238,.14)", "tooltip": "#13172f", "maxima": "#57f2ed", "minima": "#c2a0ff",
        "rain": "#66acff", "blur": "12px", "glow": "0 0 24px rgba(64,215,233,.10)", "table_filter": "none",
    },
}
ROTULOS_TEMAS = {"Claro": "☀️ Claro", "Escuro": "🌙 Escuro", "Futurista": "🚀 Futurista"}


def paleta_tema(nome="Escuro"):
    return TEMAS.get(nome, TEMAS["Escuro"])


def css_tema(nome="Escuro"):
    paleta = paleta_tema(nome)
    tokens = ";".join(f"--{chave.replace('_', '-')}:{valor}" for chave, valor in paleta.items() if chave not in ("slug", "scheme"))
    return ":root{color-scheme:" + paleta["scheme"] + ";" + tokens + "}"


def tabela_estilizada(tabela, nome="Escuro"):
    """Células nativas por paleta; no Claro o canvas é convertido pelo CSS, preservando os controles nativos.

    O canvas usa o tema global do Streamlit, sem API pública para troca por sessão.
    A conversão invert + hue-rotate inclui seu cabeçalho e mantém seleção/exportação.
    """
    paleta = paleta_tema(nome)
    # No Claro, deixar o canvas nativo escuro permite uma conversão uniforme,
    # inclusive de cabeçalho, células e estados de seleção.
    if nome == "Claro":
        paleta = {"surface": "#000000", "ink": "#eeeeee"}
    return tabela.style.set_properties(**{"background-color": paleta["surface"], "color": paleta["ink"]})
