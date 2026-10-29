import textwrap
import numpy as np
import pandas as pd

# Секторы трассы: (label, start_m, end_m)
SECTORS: list[tuple[str, int, int]] = [
    ("T1-T2 (Prima Variante)", 700, 1000),
    ("T4-T5 (Roggia)", 1950, 2150),
    ("T6 (Lesmo 1)", 2300, 2500),
    ("T7 (Lesmo 2)", 2700, 2900),
    ("T8-T10 (Ascari)", 3750, 4150),
    ("T11 (Parabolica)", 4900, 5200),
]

LABELS = {
    "current": "Текущий круг",
    "pb":      "Лучший круг (PB)",
    "ref":     "Эталон (Alien)",
}

def compute_sector_metrics(
    df: pd.DataFrame,
    sector_start: int,
    sector_end: int,
) -> dict | None:
    """
    Для заданного сектора вычисляет:
      - braking_point: первая дистанция, где BRAKE > 10%
      - min_speed: минимальная скорость от точки торможения до конца сектора
      - mini_table: DataFrame из 10 равноотстоящих точек (Distance, Speed, Brake, Throttle, Steer)
    Возвращает словарь или None, если торможение не обнаружено.
    """
    sector = df[(df["DISTANCE"] >= sector_start) & (df["DISTANCE"] <= sector_end)].copy()
    if sector.empty:
        return None

    # Точка начала торможения (BRAKE > 10%)
    braking = sector[sector["BRAKE"] > 5]
    if braking.empty:
        braking_point = sector_start
    else:
        braking_point = braking["DISTANCE"].iloc[0]

    # Данные от точки торможения до конца сектора
    after_brake = sector[sector["DISTANCE"] >= braking_point]
    if after_brake.empty:
        return None

    min_speed = after_brake["SPEED"].min()

    # 10 равноотстоящих точек
    sample_dists = np.linspace(braking_point, sector_end, 10)
    rows = []
    for d in sample_dists:
        idx = (after_brake["DISTANCE"] - d).abs().idxmin()
        row = after_brake.loc[idx]
        rows.append({
            "Distance": round(float(row["DISTANCE"]), 1),
            "Speed":    round(float(row["SPEED"]), 1),
            "Brake":    round(float(row["BRAKE"]), 1),
            "Throttle": round(float(row["THROTTLE"]), 1),
            "Steer":    round(float(row["STEERANGLE"]), 1),
        })
    mini_table = pd.DataFrame(rows)

    return {
        "braking_point": round(braking_point, 1),
        "min_speed": round(min_speed, 1),
        "mini_table": mini_table,
    }

def generate_gemini_prompt(datasets: dict[str, pd.DataFrame]) -> str:
    """
    Для каждого из 6 ключевых секторов рассчитывает метрики по всем
    загруженным кругам и формирует готовый промпт для Gemini.
    """
    data_block_parts: list[str] = []

    for sector_label, s_start, s_end in SECTORS:
        section_lines = [f"### {sector_label} ({s_start}м – {s_end}м)\n"]

        for key in ("current", "pb", "ref"):
            if key not in datasets:
                continue
            metrics = compute_sector_metrics(datasets[key], s_start, s_end)
            if metrics is None:
                continue

            lap_name = LABELS[key]
            section_lines.append(f"**{lap_name}**")
            section_lines.append(
                f"- Точка торможения: {metrics['braking_point']}м  "
                f"| Мин. скорость: {metrics['min_speed']} км/ч"
            )
            table_str = metrics["mini_table"].to_string(index=False)
            section_lines.append(f"```\n{table_str}\n```\n")

        data_block_parts.append("\n".join(section_lines))

    telemetry_data = "\n---\n".join(data_block_parts)

    # Собираем информацию о загруженных кругах
    loaded_laps = []
    if "current" in datasets:
        loaded_laps.append("1. Мой ТЕКУЩИЙ круг (на котором я совершаю ошибки и еду медленно).")
    if "pb" in datasets:
        loaded_laps.append("2. Мой ЛУЧШИЙ круг / PB (мой личный рекорд, к которому я хочу вернуться).")
    if "ref" in datasets:
        loaded_laps.append("3. ЭТАЛОННЫЙ круг / Alien (идеальный круг профессионального гонщика).")
    laps_description = "\n".join(loaded_laps)

    prompt = textwrap.dedent(f"""\
Роль: Ты — элитный гоночный инженер Aston Martin GT3. Перед тобой структурированные данные телеметрии моих кругов на трассе Монца:
{laps_description}

Изучи общие метрики и мини-таблицы по каждому повороту (где показано поведение педалей и скорости на разных метрах дистанции).
Объясни мне простым человеческим языком:
- Почему на ТЕКУЩЕМ круге я еду медленнее своего ЛУЧШЕГО круга? В каких поворотах я укоротил торможение или начал нестабильно нажимать на газ?
- Что мне и моему ЛУЧШЕМУ кругу нужно перенять у ЭТАЛОНА, чтобы стать еще быстрее (например, фазу trail braking на входе или более ранний газ на выходе)?
- Дай конкретные советы под управление геймпадом 8bitDo.

Вот данные телеметрии для анализа:

{telemetry_data}
""")
    return prompt
