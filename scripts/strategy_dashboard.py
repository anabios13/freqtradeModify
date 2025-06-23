import streamlit as st
import pandas as pd
import json
from pathlib import Path
import zipfile
from datetime import datetime, timedelta
import plotly.express as px

# Путь к папке с результатами backtest
BACKTEST_FOLDER = Path('user_data/backtest_results')

# Используем новый декоратор, чтобы можно было вручную сбрасывать кэш
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
        # перебираем все стратегии в JSON
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
                'trades': trades,
                'sharpe': s.get('sharpe', 0)
            })
    df = pd.DataFrame(records)
    if not df.empty:
        df.sort_values(by='timestamp', ascending=False, inplace=True)
        df.reset_index(drop=True, inplace=True)
    return df

def main():
    st.title("Dashboard сравнения стратегий Freqtrade")

    # Кнопка для сброса кэша и перезагрузки данных
    if st.sidebar.button("🔄 Обновить данные"):
        load_backtest_results.clear()

    df = load_backtest_results()
    if df.empty:
        st.warning("Нет данных backtest результатов в папке.")
        return

    # Sidebar — фильтры
    st.sidebar.header("Фильтры")
    min_date = st.sidebar.date_input("Начало периода", df['timestamp'].dt.date.min())
    max_date = st.sidebar.date_input("Конец периода", df['timestamp'].dt.date.max())
    selected_strats = st.sidebar.multiselect(
        "Выберите стратегии", options=df['strategy'].unique(), 
        default=list(df['strategy'].unique())
    )
    days = st.sidebar.slider("Показать результаты за последние (дней)", 1, 30, 7)

    # Фильтрация
    now = datetime.now()
    filtered = df[
        (df['timestamp'].dt.date >= min_date) &
        (df['timestamp'].dt.date <= max_date) &
        (df['strategy'].isin(selected_strats)) &
        (df['timestamp'] >= now - timedelta(days=days))
    ]

    st.markdown(f"### Отображаются {len(filtered)} записей")
    st.dataframe(filtered)

    # Графики
    metrics = {
        'profit_pct': 'Прибыль (%)',
        'profit_factor': 'Фактор прибыли',
        'max_drawdown_pct': 'Макс. просадка (%)',
        'sharpe': 'Коэффициент Шарпа'
    }
    for col, label in metrics.items():
        fig = px.bar(filtered, x='strategy', y=col, title=label,
                     labels={'strategy': 'Стратегия', col: label})
        st.plotly_chart(fig, use_container_width=True)

    # Краткий обзор
    if not filtered.empty:
        top_profit = filtered.loc[filtered['profit_pct'].idxmax()]
        top_sharpe = filtered.loc[filtered['sharpe'].idxmax()]
        top_factor = filtered.loc[filtered['profit_factor'].idxmax()]
        min_drawdown = filtered.loc[filtered['max_drawdown_pct'].idxmin()]

        st.markdown("## Лучшие стратегии")
        st.write(f"**По прибыли:** {top_profit['strategy']} — {top_profit['profit_pct']:.2f}%")
        st.write(f"**По Sharpe:** {top_sharpe['strategy']} — {top_sharpe['sharpe']:.2f}")
        st.write(f"**По фактору прибыли:** {top_factor['strategy']} — {top_factor['profit_factor']:.2f}")
        st.write(f"**По минимальной просадке:** {min_drawdown['strategy']} — {min_drawdown['max_drawdown_pct']:.2f}%")

if __name__ == "__main__":
    main()
