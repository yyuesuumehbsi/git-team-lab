import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Цвета линий MoTeC i2 Pro
COLORS = {
    "current": "#ff3333",   # Яркий красный — текущий круг
    "pb":      "#00bfff",   # Яркий голубой — личный рекорд
    "ref":     "#00ff66",   # Насыщенный зеленый/лайм — эталон
}

LABELS = {
    "current": "Текущий круг",
    "pb":      "Лучший круг (PB)",
    "ref":     "Эталон (Alien)",
}

def build_charts(
    datasets: dict[str, pd.DataFrame],
    x_range: tuple[int, int],
) -> go.Figure:
    """
    Строит единую фигуру Plotly с 5 подграфиками (общая ось X = Distance):
      1. Скорость (км/ч)
      2. Газ (%)
      3. Тормоз (%)
      4. Угол руля (°)
      5. Передача (ступенчатая линия)
    """
    fig = make_subplots(
        rows=5, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.015,
        subplot_titles=(
            "Скорость (км/ч)",
            "Газ (%)",
            "Тормоз (%)",
            "Угол руля (°)",
            "Передача"
        ),
        row_heights=[0.24, 0.19, 0.19, 0.19, 0.19],
    )

    for key, df in datasets.items():
        color = COLORS[key]
        label = LABELS[key]

        # ---- График 1: Speed ----
        fig.add_trace(
            go.Scattergl(
                x=df["DISTANCE"], y=df["SPEED"],
                mode="lines", name=label,
                line=dict(color=color, width=1.5),
                legendgroup=key,
                showlegend=True,  # Легенда показывается только для первого графика
            ),
            row=1, col=1,
        )

        # ---- График 2: Throttle ----
        fig.add_trace(
            go.Scattergl(
                x=df["DISTANCE"], y=df["THROTTLE"],
                mode="lines", name=f"{label} — Throttle",
                line=dict(color=color, width=1.5),
                legendgroup=key,
                showlegend=False,
            ),
            row=2, col=1,
        )

        # ---- График 3: Brake ----
        fig.add_trace(
            go.Scattergl(
                x=df["DISTANCE"], y=df["BRAKE"],
                mode="lines", name=f"{label} — Brake",
                line=dict(color=color, width=1.5),
                legendgroup=key,
                showlegend=False,
            ),
            row=3, col=1,
        )

        # ---- График 4: SteerAngle ----
        fig.add_trace(
            go.Scattergl(
                x=df["DISTANCE"], y=df["STEERANGLE"],
                mode="lines", name=f"{label} — Steer",
                line=dict(color=color, width=1.5),
                legendgroup=key,
                showlegend=False,
            ),
            row=4, col=1,
        )

        # ---- График 5: Gear ----
        fig.add_trace(
            go.Scattergl(
                x=df["DISTANCE"], y=df["GEAR"],
                mode="lines", name=f"{label} — Gear",
                line=dict(color=color, width=1.5),
                line_shape="hv",
                legendgroup=key,
                showlegend=False,
            ),
            row=5, col=1,
        )

    # Стиль графиков
    fig.update_layout(
        height=1100,
        template="plotly_dark",
        paper_bgcolor="#000000",
        plot_bgcolor="#000000",
        
        # ЖЕСТКАЯ НАСТРОЙКА ЛЕГЕНДЫ (ВНИЗУ)
        legend=dict(
            bgcolor="#111111",                       # Чистый темно-серый/черный фон (вместо светлого)
            font=dict(
                color="#ffffff",                     # Чистый белый контрастный текст
                size=11,
                family="monospace"
            ),
            bordercolor="#333333",                   # Темная рамка вокруг легенды
            borderwidth=1,
            orientation="h",                         # Горизонтальное расположение
            yanchor="top",
            y=-0.15,                                 # Смещение ниже графика
            xanchor="center",
            x=0.5
        ),
        
        # ЖЕСТКАЯ НАСТРОЙКА ВСПЛЫВАЮЩИХ ПОДСКАЗОК (ТУЛТИПОВ)
        hoverlabel=dict(
            bgcolor="#111111",                       # Черный фон для всплывающего окна подсказки
            font=dict(
                color="#ffffff",                     # Белый текст внутри подсказки
                size=12,
                family="monospace"
            ),
            bordercolor="#333333"                    # Темная рамка подсказки
        ),
        margin=dict(l=60, r=30, t=30, b=80),
        hovermode="x unified",
    )

    # Общие настройки осей
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#222222",
        tickfont=dict(family="Courier New, monospace", size=10, color="#888888"),
        linecolor="#333333",
        showspikes=True,
        spikemode="across",
        spikethickness=1,
        spikedash="solid",
        spikecolor="rgba(255, 255, 0, 0.4)",
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#222222",
        tickfont=dict(family="Courier New, monospace", size=10, color="#888888"),
        linecolor="#333333",
    )

    # Настройки по конкретным осям
    fig.update_xaxes(range=[x_range[0], x_range[1]], row=5, col=1, title_text="Дистанция (м)")
    fig.update_yaxes(title_text="км/ч", row=1, col=1)
    fig.update_yaxes(title_text="%", range=[-5, 105], row=2, col=1)
    fig.update_yaxes(title_text="%", range=[-5, 105], row=3, col=1)
    fig.update_yaxes(title_text="°", row=4, col=1)
    fig.update_yaxes(title_text="Gear", row=5, col=1)

    # Применение начального диапазона X ко всем подграфикам
    fig.update_xaxes(range=[x_range[0], x_range[1]])

    return fig
