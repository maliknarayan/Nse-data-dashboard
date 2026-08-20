"""Premium Plotly charts for the dashboard — theme-aware (dark/light).

Every figure has a transparent background so it inherits the card surface,
tabular hover labels, tight margins and no modebar. Colors come from theme.py
so charts always match the active palette.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard import theme as T

_FONT = "Poppins, Inter, -apple-system, Segoe UI, sans-serif"


def _ink(dark: bool) -> str:
    return "#E6E9F0" if dark else "#101828"


def _muted(dark: bool) -> str:
    return "#94A3B8" if dark else "#667085"


def _grid(dark: bool) -> str:
    return "rgba(255,255,255,0.08)" if dark else "rgba(16,24,40,0.08)"


def _rgba(hex_color: str, a: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{a})"


def _layout(dark: bool, height: int) -> dict:
    return dict(
        height=height, font=dict(family=_FONT, color=_muted(dark), size=12),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=8, r=8, t=8, b=8),
        hoverlabel=dict(font=dict(family=_FONT, size=12),
                        bgcolor=("#1A1A1A" if dark else "#FFFFFF"),
                        bordercolor=_grid(dark)),
        xaxis=dict(gridcolor=_grid(dark), zeroline=False, color=_muted(dark)),
        yaxis=dict(gridcolor=_grid(dark), zeroline=False, color=_muted(dark)),
        showlegend=False,
    )


def show(fig: go.Figure) -> None:
    # theme=None so our explicit colors win over Streamlit's auto plotly template
    st.plotly_chart(fig, use_container_width=True, theme=None,
                    config={"displayModeBar": False})


def candlestick(df: pd.DataFrame, dark: bool, height: int = 360) -> go.Figure:
    """df needs columns date/open/high/low/close (lowercase)."""
    fig = go.Figure(go.Candlestick(
        x=df["date"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_line_color=T.GREEN, decreasing_line_color=T.CORAL,
        increasing_fillcolor=T.GREEN, decreasing_fillcolor=T.CORAL, line_width=1))
    fig.update_layout(**_layout(dark, height))
    fig.update_layout(xaxis_rangeslider_visible=False, yaxis_title=None)
    return fig


def donut(labels: list[str], values: list[float], colors: list[str],
          dark: bool, center: str = "", height: int = 220) -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.64, sort=False,
        marker=dict(colors=colors, line=dict(color="rgba(0,0,0,0)", width=0)),
        textinfo="none", hovertemplate="%{label}: %{value} (%{percent})<extra></extra>"))
    fig.update_layout(**_layout(dark, height))
    fig.update_layout(showlegend=True,
                      legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center",
                                  font=dict(color=_muted(dark))))
    if center:
        fig.add_annotation(text=center, x=0.5, y=0.5, showarrow=False,
                           font=dict(family=_FONT, size=18, color=_ink(dark)))
    return fig


def hbar(series: pd.Series, dark: bool, color=None, height: int = 320,
         diverge: bool = False) -> go.Figure:
    """Horizontal bars. color = single hex, or diverge=True for green/red by sign."""
    s = series.dropna()
    if diverge:
        cols = [T.GREEN if v >= 0 else T.CORAL for v in s.values]
    else:
        cols = color or T.INDIGO
    fig = go.Figure(go.Bar(
        x=s.values, y=[str(i) for i in s.index], orientation="h",
        marker=dict(color=cols, line_width=0),
        hovertemplate="%{y}: %{x:,.2f}<extra></extra>"))
    fig.update_layout(**_layout(dark, height))
    fig.update_traces(marker_cornerradius=4)
    fig.update_layout(yaxis=dict(autorange="reversed", gridcolor="rgba(0,0,0,0)",
                                 color=_muted(dark)))
    return fig


def bars(series: pd.Series, dark: bool, color=None, height: int = 300) -> go.Figure:
    """Vertical bars (e.g. volume)."""
    s = series.dropna()
    fig = go.Figure(go.Bar(x=[str(i) for i in s.index], y=s.values,
                           marker=dict(color=color or T.INDIGO, line_width=0),
                           hovertemplate="%{x}: %{y:,.0f}<extra></extra>"))
    fig.update_layout(**_layout(dark, height))
    fig.update_traces(marker_cornerradius=3)
    return fig


def _map_hover(dark: bool) -> dict:
    """High-contrast tooltip — the shared muted grey is unreadable on the map."""
    return dict(bgcolor=("#10141F" if dark else "#FFFFFF"),
                bordercolor=("#3D4557" if dark else "#D0D5DD"),
                font=dict(family=_FONT, size=12.5, color=_ink(dark)),
                align="left")


def _diverge_scale(dark: bool) -> list:
    mid = "#2A2F3D" if dark else "#E7EAF0"
    return [[0.0, "#B42318"], [0.25, T.CORAL], [0.5, mid],
            [0.75, T.GREEN], [1.0, "#0E7A4B"]]


def treemap(d: pd.DataFrame, group: str, label: str, size: str, color: str,
            dark: bool, crange: float = 5.0, cmid: float = 0.0, height: int = 640,
            ctitle: str = "% change") -> go.Figure:
    """Group → stock treemap. Tile area = `size`, tile colour = `color` around zero."""
    d = d.dropna(subset=[size, color])
    d = d[d[size] > 0]
    if d.empty:
        return go.Figure().update_layout(**_layout(dark, height))
    g = d[group].astype(str)
    tot = d.groupby(g)[size].sum()
    # parent tile takes the size-weighted mean so a sector reads as its own move
    wsum = d.assign(_w=d[size] * d[color]).groupby(g)["_w"].sum()
    gcol = (wsum / tot).reindex(tot.index)

    fig = go.Figure(go.Treemap(
        ids=["G|" + i for i in tot.index] + ["S|" + s for s in d[label].astype(str)],
        labels=list(tot.index) + d[label].astype(str).tolist(),
        parents=[""] * len(tot) + ["G|" + i for i in g],
        values=list(tot.values) + d[size].tolist(),
        branchvalues="total", sort=True, tiling=dict(pad=2),
        marker=dict(colors=list(gcol.values) + d[color].tolist(),
                    colorscale=_diverge_scale(dark), cmid=cmid,
                    cmin=cmid - crange, cmax=cmid + crange, cornerradius=4,
                    line=dict(width=0)),
        textposition="middle center",
        textfont=dict(family=_FONT, size=12, color="#FFFFFF"),
        customdata=[[round(v, 2)] for v in gcol.values] +
                   [[round(v, 2)] for v in d[color]],
        hovertemplate="<b>%{label}</b><br>" + ctitle +
                      ": %{customdata[0]:+.2f}<br>" + size + ": %{value:,.1f}<extra></extra>",
    ))
    fig.update_layout(**_layout(dark, height))
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), hoverlabel=_map_hover(dark))
    return fig


def heatgrid(d: pd.DataFrame, label: str, color: str, dark: bool, cols: int = 16,
             height: int | None = None, crange: float = 5.0, cmid: float = 0.0,
             ctitle: str = "% change", hover: list[str] | None = None) -> go.Figure:
    """Equal-size block grid — one square per company, colour = `color`."""
    import math

    d = d.dropna(subset=[color]).reset_index(drop=True)
    if d.empty:
        return go.Figure().update_layout(**_layout(dark, height or 400))
    rows = math.ceil(len(d) / cols)
    height = height or max(360, min(1400, rows * 34 + 40))
    z = [[None] * cols for _ in range(rows)]
    txt = [[""] * cols for _ in range(rows)]
    hov = [[""] * cols for _ in range(rows)]
    hcols = [c for c in (hover or []) if c in d.columns and c != color]  # ctitle already shows it
    for i, r in d.iterrows():
        y, x = rows - 1 - i // cols, i % cols  # fill top-left first
        z[y][x] = float(r[color])
        txt[y][x] = str(r[label])[:8]  # long tickers bleed into the next cell
        extra = "<br>".join(f"{c}: {r[c]:,.2f}" if isinstance(r[c], (int, float))
                            else f"{c}: {r[c]}" for c in hcols)
        hov[y][x] = f"<b>{r[label]}</b><br>{ctitle}: {r[color]:+.2f}" + (f"<br>{extra}" if extra else "")

    fig = go.Figure(go.Heatmap(
        z=z, text=txt, hovertext=hov, texttemplate="%{text}", xgap=3, ygap=3,
        textfont=dict(family=_FONT, size=9, color="#FFFFFF"),
        colorscale=_diverge_scale(dark), zmid=cmid,
        zmin=cmid - crange, zmax=cmid + crange,
        hovertemplate="%{hovertext}<extra></extra>",
        colorbar=dict(title=ctitle, thickness=10, outlinewidth=0,
                      tickfont=dict(family=_FONT, size=10, color=_muted(dark)))))
    fig.update_layout(**_layout(dark, height))
    fig.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False),
                      margin=dict(l=0, r=0, t=0, b=0), hoverlabel=_map_hover(dark))
    return fig


def lines(data, dark: bool, height: int = 300, area: bool = False,
          colors: list[str] | None = None) -> go.Figure:
    """Line/area. data = Series (single) or DataFrame (one line per column).
    Index is the x axis."""
    if isinstance(data, pd.Series):
        data = data.to_frame()
    palette = colors or [T.INDIGO, T.GREEN, T.CORAL, T.INDIGO_DK, "#F5C451"]
    fig = go.Figure()
    for i, col in enumerate(data.columns):
        c = palette[i % len(palette)]
        fig.add_trace(go.Scatter(
            x=[str(x) for x in data.index], y=data[col], name=str(col),
            mode="lines", line=dict(color=c, width=2.4, shape="spline"),
            fill="tozeroy" if area else None,
            fillcolor=(_rgba(c, 0.12) if area and c.startswith("#") else None),
            hovertemplate="%{x} · %{y:,.2f}<extra>" + str(col) + "</extra>"))
    fig.update_layout(**_layout(dark, height))
    if data.shape[1] > 1:
        fig.update_layout(showlegend=True,
                          legend=dict(orientation="h", y=1.12, x=0,
                                      font=dict(color=_muted(dark))))
    return fig
