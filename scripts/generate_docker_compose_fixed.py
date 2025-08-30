"""
Streamlit Dashboard для FreqTrade
- Гибкая мапа контейнеров (через /app/user_data/containers.json)
- Реальная интерпретация статусов (active / no_data / error)
- Фильтр по датам (N дней ≤ 100 или произвольный период)
- Корректная сортировка сделок по датам
"""

from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
from pathlib import Path
import time
from datetime import datetime, timedelta, date
import numpy as np
from typing import Dict, Any, List, Optional

# ---------- Page setup ----------
st.set_page_config(
    page_title="FreqTrade Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Dashboard")
st.markdown("---")


# ---------- Utils ----------

def get_container_info(strategy_name: str) -> tuple[str, Optional[int]]:
    """Имя контейнера и порт API. Сначала пробуем /app/user_data/containers.json, затем дефолты."""
    default_mapping = {
        'bandtastic': ('ft_bandtastic_02-local', 8100),
        'rsi': ('ft_rsistrategy_14-local', 8106),
        'strategy001': ('ft_strategy001_16-local', 8107),
        'bandtastic_freqai': ('ft_bandtasticfreqai_04-local', 8101),
        'bandtastic_freqai_hyperopt': ('ft_bandtasticfreqaihyperopt_06-local', 8102),
        'freqai_example': ('ft_freqaiexamplestrategy_08-local', 8103),
        'highfreq_ai': ('ft_highfreqaistrategy_10-local', 8104),
        'highfreq_ai_hyperopt': ('ft_highfreqaistrategyhyperopt_12-local', 8105),
    }
    try:
        cfg = Path("/app/user_data/containers.json")
        if cfg.exists():
            with open(cfg, "r", encoding="utf-8") as f:
                external = json.load(f)
            if strategy_name in external:
                val = external[strategy_name]
                if isinstance(val, list) and len(val) >= 2:
                    return str(val[0]), int(val[1])
                if isinstance(val, dict):
                    return str(val.get("name", strategy_name)), int(val.get("port")) if val.get("port") else None
    except Exception:
        pass
    return default_mapping.get(strategy_name, (strategy_name, None))


@st.cache_data(ttl=300)
def load_aggregated_data() -> Optional[Dict[str, Any]]:
    """Загружает агрегированный JSON, который готовит data_aggregator.py"""
    try:
        data_file = Path("/tmp/aggregated_data/streamlit_data.json")
        if data_file.exists():
            with open(data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        st.error("Файл с агрегированными данными не найден. Запустите data_aggregator.py")
        return None
    except Exception as e:
        st.error(f"Ошибка при загрузке данных: {e}")
        return None


def format_timestamp(ts: str) -> str:
    """ISO8601 → красивый формат. Учитываем Z (UTC)."""
    try:
        if ts.endswith("Z"):
            ts = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts


def _trade_event_dt(trade: Dict[str, Any]) -> Optional[pd.Timestamp]:
    """Время события сделки: приоритет close_date → open_date. Возвращаем pd.Timestamp (naive UTC)."""
    raw = trade.get("close_date") or trade.get("open_date")
    if not raw:
        return None
    try:
        return pd.to_datetime(raw, utc=True).tz_convert(None)
    except Exception:
        try:
            return pd.to_datetime(raw).tz_localize(None)
        except Exception:
            return None


def _get_trades_date_min_max(trades: List[Dict[str, Any]]) -> tuple[Optional[date], Optional[date]]:
    if not trades:
        return (None, None)
    dts = [_trade_event_dt(t) for t in trades]
    dts = [d for d in dts if d is not None]
    if not dts:
        return (None, None)
    return (min(dts).date(), max(dts).date())


def filter_trades_by_period(trades: List[Dict[str, Any]], start_dt: datetime, end_dt: datetime) -> List[Dict[str, Any]]:
    res = []
    for t in trades or []:
        ev = _trade_event_dt(t)
        if ev is None:
            continue
        if start_dt <= ev <= end_dt:
            res.append(t)
    return res


def recompute_profit_by_strategy(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Суммируем ABS прибыль и winrate по стратегиям для выбранного периода"""
    if not trades:
        return {"by_strategy": {}}
    per = {}
    for t in trades:
        s = t.get("strategy") or "Unknown"
        try:
            p = float(t.get("realized_profit") or 0.0)
        except Exception:
            p = 0.0
        d = per.setdefault(s, {"profit": 0.0, "wins": 0, "losses": 0, "total": 0})
        d["profit"] += p
        d["wins"] += 1 if p > 0 else 0
        d["losses"] += 1 if p < 0 else 0
        d["total"] += 1
    out = {}
    for s, d in per.items():
        total = max(d["total"], 1)
        out[s] = {"profit": d["profit"], "win_rate": (d["wins"] / total) * 100.0}
    return {"by_strategy": out}


# ---------- Charts ----------

def create_profit_chart(profit_data: Dict[str, Any]):
    if not profit_data or "by_strategy" not in profit_data or not profit_data["by_strategy"]:
        return None
    strategies = list(profit_data["by_strategy"].keys())
    profits = [profit_data["by_strategy"][s]["profit"] for s in strategies]
    win_rates = [profit_data["by_strategy"][s]["win_rate"] for s in strategies]

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Прибыль по стратегиям", "Процент выигрышных сделок"),
        vertical_spacing=0.1
    )
    fig.add_trace(go.Bar(x=strategies, y=profits, name="Прибыль"), row=1, col=1)
    fig.add_trace(go.Bar(x=strategies, y=win_rates, name="Win Rate %"), row=2, col=1)
    fig.update_layout(height=600, showlegend=False)
    return fig


def create_enhanced_trades_timeline(recent_trades: List[Dict[str, Any]]):
    if not recent_trades:
        return None
    df = pd.DataFrame(recent_trades)
    if "strategy" not in df.columns:
        df["strategy"] = "Unknown"

    # безопасное извлечение дат (close/open)
    def _get_date(row):
        raw = row.get("close_date") or row.get("open_date")
        if raw is None:
            return None
        try:
            return pd.to_datetime(raw, utc=True).date()
        except Exception:
            try:
                return pd.to_datetime(raw).date()
            except Exception:
                return None

    df["date"] = df.apply(_get_date, axis=1)
    df = df.dropna(subset=["date"])
    if df.empty:
        return None

    daily = df.groupby(["date", "strategy"]).size().reset_index(name="count")
    all_dates = sorted(daily["date"].unique())
    all_strats = sorted(daily["strategy"].unique())

    matrix = []
    for d in all_dates:
        for s in all_strats:
            exist = daily[(daily["date"] == d) & (daily["strategy"] == s)]
            cnt = int(exist.iloc[0]["count"]) if len(exist) > 0 else 0
            matrix.append({"date": d, "strategy": s, "count": cnt})

    complete = pd.DataFrame(matrix).sort_values("date")
    fig = px.bar(complete, x="date", y="count", color="strategy",
                 title="Количество сделок по дням и стратегиям", barmode="group")
    fig.update_layout(height=600, showlegend=True)
    return fig


def create_hourly_activity_chart(recent_trades: List[Dict[str, Any]]):
    if not recent_trades:
        return None
    df = pd.DataFrame(recent_trades)
    if "strategy" not in df.columns:
        df["strategy"] = "Unknown"

    def _get_hour(row):
        raw = row.get("close_date") or row.get("open_date")
        if raw is None:
            return None
        try:
            return pd.to_datetime(raw, utc=True).hour
        except Exception:
            try:
                return pd.to_datetime(raw).hour
            except Exception:
                return None

    df["hour"] = df.apply(_get_hour, axis=1)
    df = df.dropna(subset=["hour"])
    if df.empty:
        return None

    hourly = df.groupby(["hour", "strategy"]).size().reset_index(name="count").sort_values("hour")
    fig = px.bar(hourly, x="hour", y="count", color="strategy",
                 title="Активность сделок по часам (UTC)", barmode="group")
    fig.update_layout(height=400, showlegend=True)
    fig.update_xaxes(tickmode="linear", tick0=0, dtick=1)
    return fig


def create_strategy_status_chart(summary_data: Dict[str, Any]):
    if not summary_data or "strategies" not in summary_data:
        return None

    strategies = list(summary_data["strategies"].keys())
    statuses = []
    trade_counts = []

    for s in strategies:
        info = summary_data["strategies"][s]
        if info.get("status") == "active":
            statuses.append("Активна")
            trade_counts.append(info.get("trades_count", 0))
        elif info.get("status") == "error":
            statuses.append("Ошибка")
            trade_counts.append(0)
        else:
            statuses.append("Нет данных")
            trade_counts.append(0)

    from collections import Counter
    c = Counter(statuses)

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=("Статус стратегий", "Количество сделок"),
                        specs=[[{"type": "pie"}, {"type": "bar"}]])
    fig.add_trace(go.Pie(labels=list(c.keys()), values=list(c.values()), name="Статус"), row=1, col=1)
    fig.add_trace(go.Bar(x=strategies, y=trade_counts, name="Сделки"), row=1, col=2)
    fig.update_layout(height=400, showlegend=False)
    return fig


def create_detailed_strategy_status(summary_data: Dict[str, Any], all_strategies_data: Dict[str, Any]):
    if not summary_data or "strategies" not in summary_data:
        return None

    strategies = summary_data["strategies"]
    active, error = [], []

    for name, info in strategies.items():
        status = info.get("status", "no_data")
        full = all_strategies_data.get("strategies", {}).get(name, {})
        if status == "active":
            active.append({
                "name": name,
                "trades_count": info.get("trades_count", 0),
                "total_profit": float(full.get("total_profit", 0.0) or 0.0),
                "last_update": info.get("last_update", "")
            })
        elif status == "error":
            error.append({"name": name,
                          "error": info.get("error", "Неизвестная ошибка"),
                          "last_update": info.get("last_update", "")})
        else:
            # no_data → в блок ошибок с мягким текстом
            error.append({"name": name,
                          "error": "Нет данных (БД не создана или пустая).",
                          "last_update": info.get("last_update", "")})
    return {"active": active, "error": error}


# ---------- Main ----------

def main():
    data = load_aggregated_data()
    if data is None:
        st.error("Не удалось загрузить данные. Проверьте работу data_aggregator.py")
        return

    # Sidebar: общая сводка + фильтр по датам
    with st.sidebar:
        st.header("ℹ️ Информация")
        if 'last_update' in data:
            st.metric("Последнее обновление", format_timestamp(data['last_update']))
        if 'summary' in data:
            summary = data['summary']
            st.metric("Всего стратегий", summary.get('strategies_count', 0))
            st.metric("Активных стратегий", summary.get('active_strategies', 0))
            st.metric("Всего сделок", summary.get('total_trades', 0))
            st.metric("Общая прибыль", f"{summary.get('total_profit', 0):.4f}")

        st.markdown("---")
        st.header("📆 Фильтр по дате")

        all_trades = data.get("recent_trades") or []
        min_d, max_d = _get_trades_date_min_max(all_trades)
        today = date.today()
        if min_d is None or max_d is None:
            min_d, max_d = today - timedelta(days=30), today

        filter_mode = st.radio("Режим выбора диапазона", ["Последние N дней (≤ 100)", "Произвольные даты"], index=0)

        if filter_mode == "Последние N дней (≤ 100)":
            days = st.slider("Сколько дней назад включительно", 1, 100, 100, 1)
            period_end = datetime.combine(max_d, datetime.max.time())
            period_start = period_end - timedelta(days=days - 1)
        else:
            c1, c2 = st.columns(2)
            with c1:
                d_from = st.date_input("С какого числа", value=max(min_d, max_d - timedelta(days=100)),
                                       min_value=min_d, max_value=max_d)
            with c2:
                d_to = st.date_input("По какое число", value=max_d, min_value=min_d, max_value=max_d)
            if d_from > d_to:
                st.warning("Дата 'с' больше даты 'по'. Диапазон свёрнут до одного дня.")
                d_to = d_from
            period_start = datetime.combine(d_from, datetime.min.time())
            period_end = datetime.combine(d_to, datetime.max.time())

        if st.button("🔍 Применить фильтр"):
            st.session_state["_period_start"] = period_start
            st.session_state["_period_end"] = period_end

        period_start = st.session_state.get("_period_start", period_start)
        period_end = st.session_state.get("_period_end", period_end)
        st.caption(f"Выбранный период: **{period_start:%Y-%m-%d} — {period_end:%Y-%m-%d}**")

        if st.button("🔄 Обновить данные"):
            st.cache_data.clear()
            st.rerun()

    # Основные метрики за период
    col1, col2 = st.columns([2, 1])
    with col1:
        st.header("📈 Общая статистика (за период)")
    with col2:
        st.header("⏰ Время работы")
        if 'last_update' in data:
            st.metric("Обновлено", format_timestamp(data['last_update']))

    all_rec_trades = data.get("recent_trades") or []
    filtered_trades = filter_trades_by_period(all_rec_trades, period_start, period_end)

    total_trades_period = len(filtered_trades)
    profits = []
    for t in filtered_trades:
        try:
            profits.append(float(t.get("realized_profit") or 0.0))
        except Exception:
            profits.append(0.0)
    total_profit_period = float(np.nansum(profits)) if profits else 0.0
    avg_profit = (total_profit_period / total_trades_period) if total_trades_period else 0.0
    strategies_in_period = sorted(list({t.get("strategy", "Unknown") for t in filtered_trades}))

    c = st.columns(4)
    c[0].metric("Сделки (период)", total_trades_period)
    c[1].metric("Прибыль (период)", f"{total_profit_period:.4f}")
    c[2].metric("Стратегии (в периоде)", len(strategies_in_period))
    c[3].metric("Средняя прибыль/сделку", f"{avg_profit:.6f}")

    st.markdown("---")

    # Статус стратегий (из summary с реальными статусами)
    if "summary" in data:
        st.subheader("📊 Статус стратегий")
        detailed_status = create_detailed_strategy_status(data["summary"], data)
        if detailed_status:
            s1, s2 = st.columns(2)
            with s1:
                st.subheader("✅ Активные стратегии")
                if detailed_status["active"]:
                    for s in detailed_status["active"]:
                        with st.container():
                            c1, c2, c3 = st.columns([2, 1, 1])
                            c1.write(f"**{s['name']}**")
                            c2.metric("Сделки", s["trades_count"])
                            c3.metric("Прибыль", f"{s['total_profit']:.4f}")
                        container_name, api_port = get_container_info(s["name"])
                        with st.expander(f"🔗 Ссылки для {s['name']}"):
                            st.markdown(f"**Логи контейнера:**\n```bash\ndocker logs {container_name}\n```")
                            if api_port:
                                st.markdown("**REST API:**\n```bash\n"
                                            f"curl -u freqtrader:SuperSecurePassword "
                                            f"http://localhost:{api_port}/api/v1/status\n```")
                            else:
                                st.info("Порт API неизвестен (добавьте в /app/user_data/containers.json).")
                else:
                    st.info("Нет активных стратегий.")
            with s2:
                st.subheader("ℹ️ Стратегии без данных / с ошибками")
                if detailed_status["error"]:
                    for s in detailed_status["error"]:
                        with st.container():
                            st.warning(f"**{s['name']}**")
                            st.write(f"{s.get('error', 'Нет данных')}")
                            container_name, api_port = get_container_info(s["name"])
                            st.markdown(f"**Логи контейнера:**\n```bash\ndocker logs {container_name}\n```")
                            if api_port:
                                st.markdown("**REST API:**\n```bash\n"
                                            f"curl -u freqtrader:SuperSecurePassword "
                                            f"http://localhost:{api_port}/api/v1/status\n```")
                else:
                    st.success("Ошибок и пустых стратегий не обнаружено.")
        chart = create_strategy_status_chart(data["summary"])
        if chart:
            st.plotly_chart(chart, use_container_width=True)

    # Прибыль (за период)
    st.subheader("💰 Анализ прибыли (за период)")
    profit_data_period = recompute_profit_by_strategy(filtered_trades)
    profit_chart = create_profit_chart(profit_data_period)
    if profit_chart:
        st.plotly_chart(profit_chart, use_container_width=True)

    if profit_data_period.get("by_strategy"):
        st.dataframe(pd.DataFrame(profit_data_period["by_strategy"]).T, use_container_width=True)

    # Временная шкала и активность (за период)
    st.subheader("📅 Временная шкала сделок (период)")
    timeline = create_enhanced_trades_timeline(filtered_trades)
    if timeline:
        st.subheader("📊 Детальная временная шкала по стратегиям")
        st.plotly_chart(timeline, use_container_width=True)
    else:
        st.warning("Нет данных для временной шкалы.")

    hourly = create_hourly_activity_chart(filtered_trades)
    if hourly:
        st.subheader("🕐 Активность сделок по часам (период)")
        st.plotly_chart(hourly, use_container_width=True)
    else:
        st.warning("Нет данных для графика активности по часам.")