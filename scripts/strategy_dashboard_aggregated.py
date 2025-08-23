#!/usr/bin/env python3
"""
Streamlit Dashboard для FreqTrade стратегий
Использует агрегированные данные от data_aggregator
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
from pathlib import Path
import time
from datetime import datetime, timedelta
import numpy as np

# Настройка страницы
st.set_page_config(
    page_title="FreqTrade Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Заголовок
st.title("📊 FreqTrade Dashboard - Агрегированные данные")
st.markdown("---")

@st.cache_data(ttl=300)  # Кэш на 5 минут
def load_aggregated_data():
    """Загружает агрегированные данные"""
    try:
        data_file = Path("/tmp/aggregated_data/streamlit_data.json")
        if data_file.exists():
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        else:
            st.error("Файл с агрегированными данными не найден. Запустите data_aggregator.py")
            return None
    except Exception as e:
        st.error(f"Ошибка при загрузке данных: {e}")
        return None

def format_timestamp(timestamp_str):
    """Форматирует временную метку"""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp_str

def create_profit_chart(profit_data):
    """Создает график прибыли по стратегиям"""
    if not profit_data or 'by_strategy' not in profit_data:
        return None
    
    strategies = list(profit_data['by_strategy'].keys())
    profits = [profit_data['by_strategy'][s]['profit'] for s in strategies]
    win_rates = [profit_data['by_strategy'][s]['win_rate'] for s in strategies]
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Прибыль по стратегиям', 'Процент выигрышных сделок'),
        vertical_spacing=0.1
    )
    
    # График прибыли
    fig.add_trace(
        go.Bar(x=strategies, y=profits, name='Прибыль', marker_color='lightblue'),
        row=1, col=1
    )
    
    # График процента выигрышных сделок
    fig.add_trace(
        go.Bar(x=strategies, y=win_rates, name='Win Rate %', marker_color='lightgreen'),
        row=2, col=1
    )
    
    fig.update_layout(height=600, showlegend=False)
    return fig

def create_trades_timeline(recent_trades):
    """Создает временную шкалу сделок"""
    if not recent_trades:
        return None
    
    # Конвертируем в DataFrame
    df = pd.DataFrame(recent_trades)
    
    # Добавляем стратегию если её нет
    if 'strategy' not in df.columns:
        df['strategy'] = 'Unknown'
    
    # Группируем по дате и стратегии
    df['date'] = pd.to_datetime(df['close_date']).dt.date
    daily_trades = df.groupby(['date', 'strategy']).size().reset_index(name='count')
    
    fig = px.line(
        daily_trades, 
        x='date', 
        y='count', 
        color='strategy',
        title='Количество сделок по дням'
    )
    
    fig.update_layout(height=400)
    return fig

def create_strategy_status_chart(summary_data):
    """Создает график статуса стратегий"""
    if not summary_data or 'strategies' not in summary_data:
        return None
    
    strategies = list(summary_data['strategies'].keys())
    statuses = []
    trade_counts = []
    
    for strategy in strategies:
        strategy_info = summary_data['strategies'][strategy]
        if strategy_info['status'] == 'active':
            statuses.append('Активна')
            trade_counts.append(strategy_info.get('trades_count', 0))
        else:
            statuses.append('Ошибка')
            trade_counts.append(0)
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Статус стратегий', 'Количество сделок'),
        specs=[[{"type": "pie"}, {"type": "bar"}]]
    )
    
    # Круговая диаграмма статусов
    status_counts = pd.Series(statuses).value_counts()
    fig.add_trace(
        go.Pie(labels=status_counts.index, values=status_counts.values, name="Статус"),
        row=1, col=1
    )
    
    # Столбчатая диаграмма сделок
    fig.add_trace(
        go.Bar(x=strategies, y=trade_counts, name="Сделки"),
        row=1, col=2
    )
    
    fig.update_layout(height=400, showlegend=False)
    return fig

def main():
    """Основная функция дашборда"""
    
    # Загружаем данные
    data = load_aggregated_data()
    
    if data is None:
        st.error("Не удалось загрузить данные. Проверьте, что data_aggregator.py запущен.")
        return
    
    # Боковая панель с информацией
    with st.sidebar:
        st.header("ℹ️ Информация")
        
        if 'last_update' in data:
            st.metric(
                "Последнее обновление",
                format_timestamp(data['last_update'])
            )
        
        if 'summary' in data:
            summary = data['summary']
            st.metric("Всего стратегий", summary.get('strategies_count', 0))
            st.metric("Активных стратегий", summary.get('active_strategies', 0))
            st.metric("Всего сделок", summary.get('total_trades', 0))
            st.metric("Общая прибыль", f"{summary.get('total_profit', 0):.4f}")
        
        # Кнопка обновления
        if st.button("🔄 Обновить данные"):
            st.cache_data.clear()
            st.rerun()
    
    # Основной контент
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📈 Общая статистика")
        
        if 'summary' in data:
            summary = data['summary']
            
            # Метрики
            metric_cols = st.columns(4)
            with metric_cols[0]:
                st.metric("Стратегии", summary.get('strategies_count', 0))
            with metric_cols[1]:
                st.metric("Активные", summary.get('active_strategies', 0))
            with metric_cols[2]:
                st.metric("Сделки", summary.get('total_trades', 0))
            with metric_cols[3]:
                st.metric("Прибыль", f"{summary.get('total_profit', 0):.4f}")
    
    with col2:
        st.header("⏰ Время работы")
        if 'last_update' in data:
            st.metric("Обновлено", format_timestamp(data['last_update']))
    
    # Графики
    st.markdown("---")
    
    # Статус стратегий
    if 'summary' in data:
        st.subheader("📊 Статус стратегий")
        status_chart = create_strategy_status_chart(data['summary'])
        if status_chart:
            st.plotly_chart(status_chart, use_container_width=True)
    
    # Анализ прибыли
    if 'profit_analysis' in data:
        st.subheader("💰 Анализ прибыли")
        profit_chart = create_profit_chart(data['profit_analysis'])
        if profit_chart:
            st.plotly_chart(profit_chart, use_container_width=True)
        
        # Детальная таблица прибыли
        profit_data = data['profit_analysis']
        if 'by_strategy' in profit_data:
            profit_df = pd.DataFrame(profit_data['by_strategy']).T
            st.dataframe(profit_df, use_container_width=True)
    
    # Временная шкала сделок
    if 'recent_trades' in data:
        st.subheader("📅 Временная шкала сделок")
        timeline_chart = create_trades_timeline(data['recent_trades'])
        if timeline_chart:
            st.plotly_chart(timeline_chart, use_container_width=True)
    
    # Последние сделки
    if 'recent_trades' in data and data['recent_trades']:
        st.subheader("🔄 Последние сделки")
        
        # Фильтры
        col1, col2, col3 = st.columns(3)
        with col1:
            strategy_filter = st.selectbox(
                "Стратегия",
                ["Все"] + list(set(trade.get('strategy', 'Unknown') for trade in data['recent_trades']))
            )
        
        with col2:
            profit_filter = st.selectbox(
                "Прибыль",
                ["Все", "Прибыльные", "Убыточные"]
            )
        
        with col3:
            limit = st.slider("Количество сделок", 10, 100, 50)
        
        # Фильтруем сделки
        filtered_trades = data['recent_trades'][:limit]
        
        if strategy_filter != "Все":
            filtered_trades = [t for t in filtered_trades if t.get('strategy') == strategy_filter]
        
        if profit_filter == "Прибыльные":
            filtered_trades = [t for t in filtered_trades if t.get('profit_ratio', 0) > 0]
        elif profit_filter == "Убыточные":
            filtered_trades = [t for t in filtered_trades if t.get('profit_ratio', 0) < 0]
        
        # Создаем DataFrame
        if filtered_trades:
            trades_df = pd.DataFrame(filtered_trades)
            
            # Выбираем нужные колонки
            display_columns = ['strategy', 'pair', 'open_date', 'close_date', 'profit_ratio', 'stake_amount']
            available_columns = [col for col in display_columns if col in trades_df.columns]
            
            if available_columns:
                display_df = trades_df[available_columns].copy()
                
                # Форматируем даты
                for col in ['open_date', 'close_date']:
                    if col in display_df.columns:
                        display_df[col] = pd.to_datetime(display_df[col]).dt.strftime("%Y-%m-%d %H:%M")
                
                # Форматируем прибыль
                if 'profit_ratio' in display_df.columns:
                    display_df['profit_ratio'] = display_df['profit_ratio'].apply(
                        lambda x: f"{float(x):.4f}" if pd.notna(x) else "N/A"
                    )
                
                st.dataframe(display_df, use_container_width=True)
            else:
                st.warning("Нет доступных колонок для отображения")
        else:
            st.info("Нет сделок, соответствующих выбранным фильтрам")
    
    # Детальная информация по стратегиям
    if 'strategies' in data:
        st.markdown("---")
        st.subheader("🔍 Детальная информация по стратегиям")
        
        strategy_names = list(data['strategies'].keys())
        selected_strategy = st.selectbox("Выберите стратегию", strategy_names)
        
        if selected_strategy:
            strategy_data = data['strategies'][selected_strategy]
            
            if 'error' not in strategy_data:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Стратегия:** {strategy_data['strategy_name']}")
                    st.write(f"**Время обновления:** {format_timestamp(strategy_data['timestamp'])}")
                    st.write(f"**Доступные таблицы:** {', '.join(strategy_data.get('tables', []))}")
                
                with col2:
                    if 'data' in strategy_data and 'trades' in strategy_data['data']:
                        trades = strategy_data['data']['trades']
                        st.write(f"**Количество сделок:** {len(trades)}")
                        
                        if trades:
                            # Статистика по сделкам
                            profits = [t.get('profit_ratio', 0) for t in trades if isinstance(t, dict)]
                            profits = [p for p in profits if pd.notna(p) and isinstance(p, (int, float))]
                            
                            if profits:
                                st.write(f"**Средняя прибыль:** {np.mean(profits):.4f}")
                                st.write(f"**Максимальная прибыль:** {max(profits):.4f}")
                                st.write(f"**Минимальная прибыль:** {min(profits):.4f}")
                
                # Показываем данные стратегии
                if 'data' in strategy_data:
                    for table_name, table_data in strategy_data['data'].items():
                        if isinstance(table_data, list) and table_data:
                            st.write(f"**Таблица {table_name}:**")
                            df = pd.DataFrame(table_data)
                            st.dataframe(df.head(20), use_container_width=True)
                        elif isinstance(table_data, dict) and 'error' in table_data:
                            st.error(f"Ошибка в таблице {table_name}: {table_data['error']}")
            else:
                st.error(f"Ошибка стратегии: {strategy_data['error']}")
    
    # Автообновление
    if st.checkbox("🔄 Автообновление каждые 30 секунд"):
        time.sleep(30)
        st.cache_data.clear()
        st.rerun()

if __name__ == "__main__":
    main()
