import streamlit as st
import pandas as pd
import json
import zipfile
from pathlib import Path
from datetime import datetime, timedelta
import plotly.express as px

BACKTEST_FOLDER = Path('user_data/backtest_results')
DRYRUN_FOLDER  = Path('user_data/dryrun_exports')

@st.cache_data(show_spinner=False)
def load_backtest_results():
    records = []
    zip_files = sorted(BACKTEST_FOLDER.glob('backtest-result-*.zip'))
    for zip_file in zip_files:
        ts_str = zip_file.stem.replace('backtest-result-', '')
        try:
            test_dt = datetime.strptime(ts_str, '%Y-%m-%d_%H-%M-%S')
        except ValueError:
            continue
        with zipfile.ZipFile(zip_file, 'r') as z:
            json_name = next(
                (f for f in z.namelist() if f.endswith('.json') and 'config' not in f),
                None
            )
            if not json_name:
                continue
            data = json.load(z.open(json_name))
        for s in data.get('strategy_comparison', []):
            trades = s.get('trades', 0)
            if trades <= 0:
                continue
            records.append({
                'timestamp': test_dt,
                'strategy': s.get('key', '—'),
                'profit_pct': s.get('profit_total_pct', 0),
                'profit_factor': s.get('profit_factor', 0),
                'max_drawdown_pct': float(s.get('max_drawdown_account', 0)),
                'sharpe': s.get('sharpe', 0)
            })
    return pd.DataFrame(records)

@st.cache_data(show_spinner=False)
def load_dryrun_results():
    records = []
    for file in sorted(DRYRUN_FOLDER.glob('*.json')):
        parts = file.stem.split('_', 1)
        if len(parts) != 2:
            continue
        strategy_name, ts_str = parts
        try:
            test_dt = datetime.strptime(ts_str, '%Y-%m-%d_%H-%M-%S')
        except ValueError:
            continue
        with open(file) as f:
            data = json.load(f)
        for t in data:
            profit_raw = t.get('7', 0)
            records.append({
                'timestamp': test_dt,
                'strategy': strategy_name,
                'profit_pct': profit_raw * 100,
                'profit_factor': 0,
                'max_drawdown_pct': 0,
                'sharpe': 0
            })
    return pd.DataFrame(records)

def main():
    st.title("Панель сравнения стратегий Freqtrade")

    if st.sidebar.button("🔄 Обновить данные"):
        load_backtest_results.clear()
        load_dryrun_results.clear()

    df_bt = load_backtest_results()
    df_dr = load_dryrun_results()

    # Отмечаем источник и объединяем
    if df_bt is not None and not df_bt.empty:
        df_bt['source'] = 'BT'
    if df_dr is not None and not df_dr.empty:
        df_dr['source'] = 'DR'
    df = pd.concat([df_bt, df_dr], ignore_index=True)
    
    if df.empty:
        st.warning("Нет данных для отображения. Проверьте папки с результатами.")
        return

    # ——— Фильтры ———
    st.sidebar.header("Фильтры")
    strategies = sorted(df['strategy'].unique())
    selected_strats = st.sidebar.multiselect("Стратегии", strategies, default=strategies)
    sources = sorted(df['source'].unique())
    source_filter = st.sidebar.multiselect("Источники", sources, default=sources)
    min_date = st.sidebar.date_input("Период: с", df['timestamp'].dt.date.min())
    max_date = st.sidebar.date_input("Период: по", df['timestamp'].dt.date.max())
    days = st.sidebar.slider("Показать за последние (дней)", 1, 30, 7)

    now = datetime.now()
    mask = (
        df['strategy'].isin(selected_strats) &
        df['source'].isin(source_filter) &
        (df['timestamp'].dt.date >= min_date) &
        (df['timestamp'].dt.date <= max_date) &
        (df['timestamp'] >= now - timedelta(days=days))
    )
    df = df[mask]

    # ——— Сводная таблица с MultiIndex колонок ———
    metrics = ['profit_pct','profit_factor','max_drawdown_pct','sharpe']
    pivot = df.pivot_table(
        index='strategy',
        columns='source',
        values=metrics,
        aggfunc='mean'
    )

    # Перевод метрик
    rus_metric = {
        'profit_pct':        'Прибыль, %',
        'profit_factor':     'Фактор прибыли (Чем больше — тем лучше)',
        'max_drawdown_pct':  'Макс. просадка, % (Чем меньше — тем лучше)',
        'sharpe':            'Коэф. Шарпа (Чем больше — тем лучше)'
    }
    pivot.columns = pd.MultiIndex.from_tuples([
        (rus_metric[m], src) for m, src in pivot.columns
    ])

    st.markdown("### Сводная таблица по стратегиям")
    st.dataframe(pivot)

        # ——— Графики по метрикам ———
    st.markdown("## Графики метрик")
    for key, rus_m in rus_metric.items():
        # если по этой метрике нет ни одной колонки — пропускаем
        if rus_m not in pivot.columns.get_level_values(0):
            continue

        # вытаскиваем DataFrame только с уровнями (rus_m, источник)
        df_metric = pivot[rus_m]  # колонки — все доступные источники для rus_m
        # из них выбираем только BT и/или DR, которые реально есть
        sources_present = [src for src in ['BT', 'DR'] if src in df_metric.columns]
        if not sources_present:
            continue

        # готовим DF для px.bar: столбец Стратегия + столбцы источников
        df_plot = df_metric[sources_present].reset_index()
        df_plot.columns = ['Стратегия'] + sources_present

        # подсказка по смыслу метрики
        hint = "Чем меньше — тем лучше" if key == 'max_drawdown_pct' else "Чем больше — тем лучше"

        # рисуем
        fig = px.bar(
            df_plot,
            x='Стратегия',
            y=sources_present,
            barmode='group',
            labels={'value': rus_m, 'variable': 'Источник'},
            title=rus_m
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Подсказка: {hint}")


    # ——— Лучшие стратегии по метрикам (без изменений) ———

    st.markdown("## Лучшая стратегия по каждой метрике")
    for key, rus_m in rus_metric.items():
        # Проверяем, есть ли хотя бы один источник для этой метрики
        has_bt = (rus_m, 'BT') in pivot.columns
        has_dr = (rus_m, 'DR') in pivot.columns
        if not has_bt and not has_dr:
            continue  # нет ни BT, ни DR — пропускаем

        st.subheader(rus_m)

        if has_bt:
            series_bt = pivot[rus_m]['BT']
            best_bt   = series_bt.idxmax()
            val_bt    = series_bt.max()
            st.write(f"- **BT**: {best_bt} ({val_bt:.2f})")
        else:
            st.write("- **BT**: нет данных")

        if has_dr:
            series_dr = pivot[rus_m]['DR']
            best_dr   = series_dr.idxmax()
            val_dr    = series_dr.max()
            st.write(f"- **DR**: {best_dr} ({val_dr:.2f})")
        else:
            st.write("- **DR**: нет данных")


if __name__ == "__main__":
    main()
