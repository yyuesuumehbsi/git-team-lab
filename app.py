"""
ACC Telemetry Analyzer — интерактивное веб-приложение для трёхстороннего
сравнения телеметрии Assetto Corsa Competizione (Монца).

Запуск:
    pip install -r requirements.txt
    streamlit run app.py
"""

import pandas as pd
import streamlit as st

# Импорты модулей из папки utils
from utils.parser import TRACK_LENGTH, load_telemetry
from utils.metrics import SECTORS, LABELS, compute_sector_metrics, generate_gemini_prompt
from utils.charts import build_charts

# Выпадающий список секторов для пользователя
SECTOR_OPTIONS: dict[str, tuple[int, int]] = {
    f"Вся трасса (0 – {TRACK_LENGTH}м)": (0, TRACK_LENGTH),
}
for label, s, e in SECTORS:
    SECTOR_OPTIONS[f"{label} ({s}м – {e}м)"] = (s, e)


def main():
    st.set_page_config(
        page_title="ACC Telemetry Analyzer — Monza",
        page_icon="🏎️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # ---- CSS-кастомизация под MoTeC i2 Pro ----
    st.markdown("""
    <style>
    /* Глубокий черный фон для приложения и темно-серый для боковой панели */
    .stApp {
        background-color: #000000 !important;
    }
    [data-testid="stSidebar"] {
        background-color: #0d0d0d !important;
    }
    
    /* Точечный моноширинный шрифт только для аналитических элементов */
    .main-title, .subtitle, .stDataFrame, div[data-testid="stTable"], div[data-testid="stMetricValue"], div[data-testid="stMetricLabel"] {
        font-family: 'Courier New', Courier, Consolas, monospace !important;
    }

    /* Градиентный заголовок в стиле MoTeC */
    .main-title {
        background: linear-gradient(90deg, #ff3333 0%, #00bfff 50%, #00ff66 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2rem;
        font-weight: 800;
        margin-bottom: 0;
    }
    .subtitle {
        color: #888888;
        font-size: 0.9rem;
        margin-top: -0.5rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Убираем лишние отступы */
    .block-container { 
        padding-top: 1rem !important; 
        padding-bottom: 2rem !important; 
    }
    
    /* Компактный и строгий стиль файл-лоадеров */
    [data-testid="stFileUploader"] {
        border: 1px dashed #333333;
        background-color: #050505;
        border-radius: 4px;
        padding: 4px;
    }

    /* Стилизация интерактивных таблиц и датафреймов */
    .stDataFrame, div[data-testid="stTable"] {
        border: 1px solid #222222;
    }

    /* Стилизация карточек метрик */
    div[data-testid="stMetric"] {
        background-color: #070707 !important;
        border: 1px solid #222222 !important;
        padding: 10px !important;
        border-radius: 4px !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: bold !important;
        color: #00ff66 !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #888888 !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
    }
    </style>
    """, unsafe_allow_html=True)

    # ---- Заголовок ----
    st.markdown('<p class="main-title">🏎️ ACC Telemetry Analyzer</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Монца · Трёхстороннее сравнение телеметрии</p>', unsafe_allow_html=True)

    # ============================================================
    # БОКОВАЯ ПАНЕЛЬ
    # ============================================================
    with st.sidebar:
        st.header("📂 Загрузка телеметрии")
        st.caption("Загрузите от 1 до 3 CSV-файлов MoTeC / ACC")

        file_current = st.file_uploader(
            "🔴 Мой ТЕКУЩИЙ круг", type=["csv"], key="file_current",
        )
        file_pb = st.file_uploader(
            "🔵 Мой ЛУЧШИЙ круг (PB)", type=["csv"], key="file_pb",
        )
        file_ref = st.file_uploader(
            "🟢 ЭТАЛОННЫЙ круг (Alien)", type=["csv"], key="file_ref",
        )

        st.divider()
        st.header("🗺️ Сектор трассы")
        sector_choice = st.selectbox(
            "Выбрать сектор для детального анализа",
            options=list(SECTOR_OPTIONS.keys()),
        )
        x_range = SECTOR_OPTIONS[sector_choice]

    # ============================================================
    # ЗАГРУЗКА ДАННЫХ
    # ============================================================
    datasets: dict[str, pd.DataFrame] = {}

    upload_map = {
        "current": file_current,
        "pb": file_pb,
        "ref": file_ref,
    }
    for key, uploaded in upload_map.items():
        if uploaded is not None:
            with st.spinner(f"Загрузка {LABELS[key]}…"):
                df = load_telemetry(uploaded)
                if df is not None:
                    datasets[key] = df

    # Если ни одного файла не загружено — показываем подсказку
    if not datasets:
        st.info(
            "👈 Загрузите хотя бы один CSV-файл телеметрии на боковой панели, "
            "чтобы начать анализ."
        )
        st.stop()

    # Показываем сколько кругов загружено
    loaded_names = [f"{LABELS[k]}" for k in datasets]
    st.success(f"✅ Загружено кругов: **{len(datasets)}** — {', '.join(loaded_names)}")

    # ============================================================
    # ГРАФИКИ
    # ============================================================
    st.subheader("📊 Телеметрия")
    fig = build_charts(datasets, x_range)
    st.plotly_chart(fig, use_container_width=True, theme=None, config={"scrollZoom": True})

    # ============================================================
    # ТАБЛИЦА МЕТРИК ПО СЕКТОРАМ
    # ============================================================
    st.subheader("📋 Метрики по секторам")

    for sector_label, s_start, s_end in SECTORS:
        with st.expander(f"{sector_label} ({s_start}м – {s_end}м)", expanded=False):
            cols = st.columns(len(datasets))
            for i, (key, df) in enumerate(datasets.items()):
                metrics = compute_sector_metrics(df, s_start, s_end)
                with cols[i]:
                    st.markdown(f"**{LABELS[key]}**")
                    if metrics:
                        st.metric("Точка торможения", f"{metrics['braking_point']} м")
                        st.metric("Мин. скорость", f"{metrics['min_speed']} км/ч")
                        st.dataframe(
                            metrics["mini_table"],
                            width="stretch",
                            hide_index=True,
                        )
                    else:
                        st.caption("Нет данных для сектора")

    # ============================================================
    # ПРОМПТ ДЛЯ GEMINI
    # ============================================================
    st.subheader("🤖 Промпт для Gemini")
    st.caption(
        "Скопируйте сгенерированный промпт и вставьте в Gemini для получения "
        "персонализированного анализа от виртуального гоночного инженера."
    )

    prompt_text = generate_gemini_prompt(datasets)

    st.code(prompt_text, language="markdown")

    # Кнопка копирования через JS
    st.markdown(
        """
        <script>
        function copyPrompt() {
            const codeBlock = document.querySelectorAll('code');
            const lastCode = codeBlock[codeBlock.length - 1];
            navigator.clipboard.writeText(lastCode.innerText);
        }
        </script>
        """,
        unsafe_allow_html=True,
    )

    # Альтернативная кнопка копирования (нативная Streamlit)
    st.download_button(
        label="📋 Скачать промпт как .txt",
        data=prompt_text,
        file_name="gemini_prompt.txt",
        mime="text/plain",
    )


if __name__ == "__main__":
    main()
