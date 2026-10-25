import io
import numpy as np
import pandas as pd
import streamlit as st

TRACK_LENGTH = 5793  # Полная длина трассы Монца, м
REQUIRED_COLS = ["DISTANCE", "SPEED", "THROTTLE", "BRAKE", "STEERANGLE", "GEAR"]

def load_telemetry(uploaded_file) -> pd.DataFrame | None:
    """
    Надёжное чтение CSV-файла телеметрии MoTeC / ACC.

    Алгоритм:
      1. Декодирует файл в utf-8-sig (автоматически убирает BOM \ufeff).
      2. В первых 30 строках ищет строку, где первые два элемента
         (после очистки от кавычек) — «Time» и «Distance».
      3. Определяет разделитель (`,` или `;`) по найденной строке.
      4. Читает CSV, пропуская метаданные и строку единиц измерения.
      5. Очищает названия колонок от кавычек, пробелов, приводит к UPPER.
      6. Страховочное удаление нечисловой первой строки (units).
      7. Выводит отладочную информацию, если DISTANCE не найден.
      8. Конвертирует единицы, интерполирует на общую шкалу дистанции.

    Возвращает DataFrame или None при ошибке.
    """
    try:
        raw_bytes = uploaded_file.read()

        # ── 1. Кодировка: utf-8-sig убирает BOM автоматически ──
        raw_text = raw_bytes.decode("utf-8-sig", errors="replace")
        lines = raw_text.splitlines()

        # ── 2. Строгий поиск строки заголовков в первых 30 строках ──
        header_idx = None
        sep = ","  # разделитель по умолчанию

        for idx, line in enumerate(lines[:30]):
            clean = line.replace('"', '').replace("'", "").strip()
            # Быстрая проверка: строка начинается с Time,Distance или Time;Distance
            clean_lower = clean.lower()
            if clean_lower.startswith("time,distance") or clean_lower.startswith("time;distance"):
                sep = ";" if ";" in line else ","
                header_idx = idx
                break
            # Дополнительная проверка: разбиваем по возможным разделителям
            for try_sep in (",", ";"):
                parts = [p.replace('"', '').replace("'", "").strip().lower() for p in line.split(try_sep)]
                if len(parts) >= 2 and parts[0] == "time" and parts[1] == "distance":
                    sep = try_sep
                    header_idx = idx
                    break
            if header_idx is not None:
                break

        if header_idx is None:
            st.warning(
                f"⚠️ Не удалось найти строку заголовков (Time, Distance) "
                f"в первых 30 строках файла «{uploaded_file.name}»."
            )
            return None

        # ── 3. Чтение через Pandas ──
        #    skiprows=[header_idx + 1] — пропускаем строку единиц измерения
        #    (MoTeC ставит «s», «m», «km/h» … сразу под заголовками)
        #    Индексы в skiprows отсчитываются от начала файла.
        all_skip = list(range(0, header_idx))          # метаданные до заголовка
        all_skip.append(header_idx + 1)                 # строка единиц (units)

        df = pd.read_csv(
            io.StringIO("\n".join(lines)),
            sep=sep,
            engine="python",
            on_bad_lines="skip",
            quotechar='"',
            skiprows=all_skip,
        )

        # ── 4. Очистка названий колонок от кавычек и пробелов → UPPER ──
        df.columns = (
            df.columns
            .str.replace('"', '', regex=False)
            .str.replace("'", "", regex=False)
            .str.strip()
            .str.upper()
        )

        # ── 5. Удаление строки единиц, если она всё-таки осталась ──
        #    Страховка: если первая строка данных нечисловая — удаляем.
        if not df.empty:
            first_row = df.iloc[0]
            is_text_row = True
            for val in first_row:
                try:
                    float(val)
                    is_text_row = False
                    break
                except (ValueError, TypeError):
                    continue
            if is_text_row:
                df = df.iloc[1:].reset_index(drop=True)

        # ── 7. Приведение данных к числовому типу ──
        df = df.apply(pd.to_numeric, errors="coerce")
        df.dropna(how="all", inplace=True)
        df.reset_index(drop=True, inplace=True)

        # ── 8. Проверка наличия DISTANCE с отладочным выводом ──
        if "DISTANCE" not in df.columns:
            st.warning(
                f"⚠️ Колонка 'DISTANCE' не найдена в файле «{uploaded_file.name}».\n\n"
                f"Доступные колонки в файле: {df.columns.tolist()}"
            )
            return None

        df.dropna(subset=["DISTANCE"], inplace=True)
        df.reset_index(drop=True, inplace=True)

        # Проверка остальных обязательных колонок
        missing = [c for c in REQUIRED_COLS if c not in df.columns]
        if missing:
            st.warning(
                f"⚠️ В файле «{uploaded_file.name}» отсутствуют колонки: {missing}\n\n"
                f"Доступные колонки: {df.columns.tolist()}"
            )
            return None

        # ── 9. Конвертация единиц ──
        # Скорость: если макс < 100 → предположительно м/с → км/ч
        if df["SPEED"].max() < 100:
            df["SPEED"] = df["SPEED"] * 3.6

        # Педали: если макс ≤ 1.5 → шкала 0–1, переводим в 0–100%
        for col in ("THROTTLE", "BRAKE"):
            if df[col].max() <= 1.0:
                df[col] = df[col] * 100

        # ── 10. Интерполяция на единую шкалу дистанции ──
        common_dist = np.arange(0, TRACK_LENGTH + 1, 1, dtype=float)
        interpolated = {"DISTANCE": common_dist}
        for col in REQUIRED_COLS[1:]:
            interpolated[col] = np.interp(
                common_dist, df["DISTANCE"].values, df[col].values
            )
        return pd.DataFrame(interpolated)

    except Exception as exc:
        st.error(f"❌ Ошибка при чтении «{uploaded_file.name}»: {exc}")
        return None
