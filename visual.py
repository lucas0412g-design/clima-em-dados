"""Apresentação do dashboard, sem consultas ou alterações nos dados da fonte."""
from datetime import datetime, timezone
from html import escape
import pandas as pd
from tempo import condicao_tempo
from temas import paleta_tema


def icone_tempo(codigo):
    """Símbolos vetoriais locais correspondentes aos grupos de condições WMO."""
    sol = '<circle cx="31" cy="30" r="12" fill="var(--sun)" stroke="var(--sun)"/><path d="M31 9v-4m0 50v-4M10 30H6m50 0h-4M16 15l-3-3m36 36-3-3M16 45l-3 3m36-36-3 3" stroke="var(--sun)"/>'
    nuvem = '<path d="M19 51h38a12 12 0 0 0 1-24 17 17 0 0 0-32-4 14 14 0 0 0-7 28Z" fill="var(--icon-cloud)" stroke="var(--icon-line)"/>'
    if codigo in (0, 1):
        desenho = sol
    elif codigo == 2:
        desenho = sol + nuvem
    elif codigo == 3:
        desenho = nuvem
    elif codigo in (45, 48):
        desenho = nuvem + '<path d="M15 60h44M22 68h32" stroke="var(--icon-line)"/>'
    elif codigo in (71, 73, 75, 77, 85, 86):
        desenho = nuvem + '<path d="M28 58v14m-6-10 12 6m-12 0 12-6m17-4v14m-6-10 12 6m-12 0 12-6" stroke="var(--violet)"/>'
    elif codigo in (95, 96, 99):
        desenho = nuvem + '<path d="m39 49-9 15h9l-4 12 17-19H41l6-8" fill="var(--sun)" stroke="var(--sun)"/>'
    elif codigo in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        desenho = nuvem + '<path d="m25 59-4 9m18-9-4 9m18-9-4 9" stroke="var(--cyan)"/>'
    else:
        desenho = '<circle cx="40" cy="38" r="24" stroke="var(--muted)"/><path d="M34 30a7 7 0 1 1 11 6c-4 2-5 3-5 7m0 8v1" stroke="var(--muted)"/>'
    return '<svg class="weather-icon" viewBox="0 0 80 80" fill="none" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + desenho + '</svg>'


def cartoes_dias(tabela, codigos):
    """Contrato único: o dia local é metadado da tabela, não um valor meteorológico."""
    hoje = tabela.attrs.get("hoje_local") or datetime.now(timezone.utc).date()
    dias = ("SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM")
    def numero(valor, unidade):
        return "—" if pd.isna(valor) else f"{valor:.1f}".rstrip("0").rstrip(".").replace(".", ",") + unidade
    cartoes = []
    for indice, (_, linha) in enumerate(tabela.iterrows()):
        data = linha["Data"]
        eh_hoje = data.date() == hoje
        dia = "HOJE" if eh_hoje else dias[data.weekday()]
        condicao = condicao_tempo(codigos[indice])
        cartoes.append('<article class="day-card' + (' today' if eh_hoje else '') + '"><span class="day-name notranslate" translate="no" lang="pt-BR">' + dia + '</span><span class="day-date">' + data.strftime("%d/%m") + '</span>' + icone_tempo(codigos[indice]) + '<span class="day-condition">' + escape(condicao) + '</span><div class="day-temps"><strong title="Máxima">' + numero(linha["Máxima (°C)"], "°") + '</strong><span title="Mínima">' + numero(linha["Mínima (°C)"], "°") + '</span></div><span class="day-rain">Chuva ' + numero(linha["Chance de chuva (%)"], "%") + '</span></article>')
    return '<div class="days-grid">' + ''.join(cartoes) + '</div>'


def estilizar_grafico(figura, unidade, tema="Escuro"):
    paleta = paleta_tema(tema)
    figura.update_layout(template="plotly_white" if tema == "Claro" else "plotly_dark", height=320,
                         paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(family="Segoe UI, Arial, sans-serif", color=paleta["muted"], size=12),
                         margin=dict(l=12, r=12, t=12, b=20), hovermode="x unified", separators=",.",
                         legend=dict(title_text="", orientation="h", y=1.16, x=0, font=dict(size=11)),
                         hoverlabel=dict(bgcolor=paleta["tooltip"], bordercolor=paleta["cyan"],
                                         font_color=paleta["ink"]), dragmode=False)
    figura.update_xaxes(title_text="", tickformat="%d/%m", dtick=86400000, showgrid=False,
                        zeroline=False, fixedrange=True, automargin=True, hoverformat="%d/%m/%Y")
    figura.update_yaxes(title_text=unidade, gridcolor=paleta["grid"], zeroline=False,
                        fixedrange=True, automargin=True)
    if tema == "Escuro":
        figura.update_layout(paper_bgcolor=paleta["surface"], plot_bgcolor=paleta["surface"])
    if tema == "Futurista":
        figura.update_xaxes(showline=True, linecolor=paleta["grid"])
        figura.update_yaxes(griddash="dot")
