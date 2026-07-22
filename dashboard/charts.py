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
