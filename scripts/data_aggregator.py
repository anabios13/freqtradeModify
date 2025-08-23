#!/usr/bin/env python3
"""
Data Aggregator для FreqTrade стратегий
Собирает данные из всех стратегий и предоставляет их для Streamlit дашборда
"""

import os
import json
import sqlite3
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime, timedelta
import time
from typing import Dict, List, Any, Optional
import threading

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FreqTradeDataAggregator:
    """Агрегатор данных FreqTrade стратегий"""
    
    def __init__(self, user_data_dir: str = "/app/user_data", trades_limit: int = None):
        self.user_data_dir = Path(user_data_dir)
        self.trades_limit = trades_limit  # None = все сделки, число = ограничение
        self.cache = {}
        self.cache_timestamp = {}
        self.cache_ttl = 300  # 5 минут
        self.lock = threading.Lock()
        
        # Конфигурация стратегий - используем базы данных из dryrun_db
        self.strategies = {
            'bandtastic': {
                'db_path': '/app/user_data/dryrun_db/Bandtastic.sqlite',
                'logs_path': '/app/user_data/logs',
                'models_path': '/app/user_data/models',
                'freqai_path': '/app/user_data/freqaimodels'
            },
            'rsi': {
                'db_path': '/app/user_data/dryrun_db/RsiStrategy.sqlite',
                'logs_path': '/app/user_data/logs',
                'models_path': '/app/user_data/models',
                'freqai_path': '/app/user_data/freqaimodels'
            },
            'strategy001': {
                'db_path': '/app/user_data/dryrun_db/Strategy001.sqlite',
                'logs_path': '/app/user_data/logs',
                'models_path': '/app/user_data/models',
                'freqai_path': '/app/user_data/freqaimodels'
            },
            'bandtastic_freqai': {
                'db_path': '/app/user_data/dryrun_db/BandtasticFreqAI.sqlite',
                'logs_path': '/app/user_data/logs',
                'models_path': '/app/user_data/models',
                'freqai_path': '/app/user_data/freqaimodels'
            },
            'highfreq_ai': {
                'db_path': '/app/user_data/dryrun_db/HighFreqAIStrategy.sqlite',
                'logs_path': '/app/user_data/logs',
                'models_path': '/app/user_data/models',
                'freqai_path': '/app/user_data/freqaimodels'
            },
            'freqai_example': {
                'db_path': '/app/user_data/dryrun_db/FreqaiExampleStrategy.sqlite',
                'logs_path': '/app/user_data/logs',
                'models_path': '/app/user_data/models',
                'freqai_path': '/app/user_data/freqaimodels'
            }
        }
        
        # Создаем папку для агрегированных данных
        self.output_dir = Path("/tmp/aggregated_data")
        self.output_dir.mkdir(exist_ok=True)
        
        logger.info(f"Data Aggregator инициализирован. Выходная папка: {self.output_dir}")
    
    def get_strategy_data(self, strategy_name: str) -> Dict[str, Any]:
        """Получает данные для конкретной стратегии"""
        try:
            strategy_config = self.strategies.get(strategy_name)
            if not strategy_config:
                return {"error": f"Стратегия {strategy_name} не найдена"}
            
            db_path = Path(strategy_config['db_path'])
            
            if not db_path.exists():
                return {"error": f"База данных не найдена: {db_path}"}
            
            # Подключаемся к базе данных
            conn = sqlite3.connect(str(db_path))
            
            # Получаем список таблиц
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            strategy_data = {
                "strategy_name": strategy_name,
                "timestamp": datetime.now().isoformat(),
                "tables": tables,
                "data": {}
            }
            
            # Получаем данные из основных таблиц
            for table in tables:
                try:
                    if table == 'trades':
                        # Получаем сделки с возможным ограничением
                        query = "SELECT * FROM trades ORDER BY close_date DESC"
                        if self.trades_limit:
                            query += f" LIMIT {self.trades_limit}"
                        df = pd.read_sql_query(query, conn)
                        trades_count = len(df)
                        strategy_data["data"]["trades"] = df.to_dict('records')
                        logger.info(f"Загружено {trades_count} сделок для стратегии {strategy_name}")
                        
                    elif table == 'trade_history':
                        # Получаем историю сделок с возможным ограничением
                        query = "SELECT * FROM trade_history ORDER BY close_date DESC"
                        if self.trades_limit:
                            query += f" LIMIT {self.trades_limit}"
                        df = pd.read_sql_query(query, conn)
                        strategy_data["data"]["trade_history"] = df.to_dict('records')
                        
                    elif table == 'pairlock':
                        # Получаем блокировки пар
                        df = pd.read_sql_query("SELECT * FROM pairlock", conn)
                        strategy_data["data"]["pairlock"] = df.to_dict('records')
                        
                    elif table == 'pairlock_history':
                        # Получаем историю блокировок
                        df = pd.read_sql_query("SELECT * FROM pairlock_history", conn)
                        strategy_data["data"]["pairlock_history"] = df.to_dict('records')
                        
                    elif table == 'whitelist':
                        # Получаем белый список пар
                        df = pd.read_sql_query("SELECT * FROM whitelist", conn)
                        strategy_data["data"]["whitelist"] = df.to_dict('records')
                        
                    elif table == 'blacklist':
                        # Получаем черный список пар
                        df = pd.read_sql_query("SELECT * FROM blacklist", conn)
                        strategy_data["data"]["blacklist"] = df.to_dict('records')
                        
                    elif table == 'trades_analysis':
                        # Получаем анализ сделок
                        df = pd.read_sql_query("SELECT * FROM trades_analysis", conn)
                        strategy_data["data"]["trades_analysis"] = df.to_dict('records')
                        
                except Exception as e:
                    logger.warning(f"Ошибка при чтении таблицы {table}: {e}")
                    strategy_data["data"][table] = {"error": str(e)}
            
            conn.close()
            return strategy_data
            
        except Exception as e:
            logger.error(f"Ошибка при получении данных стратегии {strategy_name}: {e}")
            return {"error": str(e)}
    
    def get_all_strategies_data(self) -> Dict[str, Any]:
        """Получает данные всех стратегий"""
        with self.lock:
            current_time = time.time()
            
            # Проверяем кэш
            if 'all_strategies' in self.cache:
                if current_time - self.cache_timestamp.get('all_strategies', 0) < self.cache_ttl:
                    logger.info("Возвращаем данные из кэша")
                    return self.cache['all_strategies']
            
            logger.info("Собираем данные всех стратегий...")
            
            all_data = {
                "timestamp": datetime.now().isoformat(),
                "strategies": {},
                "summary": {
                    "total_strategies": len(self.strategies),
                    "active_strategies": 0,
                    "total_trades": 0,
                    "total_profit": 0.0
                }
            }
            
            total_trades = 0
            total_profit = 0.0
            active_strategies = 0
            
            for strategy_name in self.strategies.keys():
                strategy_data = self.get_strategy_data(strategy_name)
                
                if "error" not in strategy_data:
                    active_strategies += 1
                    
                    # Подсчитываем статистику
                    if "trades" in strategy_data.get("data", {}):
                        trades = strategy_data["data"]["trades"]
                        total_trades += len(trades)
                        
                        # Считаем общую прибыль
                        for trade in trades:
                            if isinstance(trade, dict):
                                # Пробуем разные поля для прибыли
                                profit_value = None
                                if "profit_ratio" in trade:
                                    profit_value = trade["profit_ratio"]
                                elif "realized_profit" in trade:
                                    # Конвертируем realized_profit в процент от stake_amount
                                    try:
                                        stake_amount = float(trade.get("stake_amount", 1))
                                        if stake_amount > 0:
                                            profit_value = float(trade["realized_profit"]) / stake_amount
                                    except (ValueError, TypeError):
                                        pass
                                elif "close_profit" in trade:
                                    # Конвертируем close_profit в процент от stake_amount
                                    try:
                                        stake_amount = float(trade.get("stake_amount", 1))
                                        if stake_amount > 0:
                                            profit_value = float(trade["close_profit"]) / stake_amount
                                    except (ValueError, TypeError):
                                        pass
                                
                                if profit_value is not None:
                                    try:
                                        profit_ratio = float(profit_value)
                                        if not pd.isna(profit_ratio):
                                            total_profit += profit_ratio
                                    except (ValueError, TypeError):
                                        pass
                
                all_data["strategies"][strategy_name] = strategy_data
            
            # Обновляем сводку
            all_data["summary"]["active_strategies"] = active_strategies
            all_data["summary"]["total_trades"] = total_trades
            all_data["summary"]["total_profit"] = round(total_profit, 4)
            
            # Сохраняем в кэш
            self.cache['all_strategies'] = all_data
            self.cache_timestamp['all_strategies'] = current_time
            
            # Сохраняем в файл для Streamlit
            output_file = self.output_dir / "all_strategies_data.json"
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(all_data, f, ensure_ascii=False, indent=2, default=str)
                logger.info(f"Данные сохранены в {output_file}")
            except Exception as e:
                logger.error(f"Ошибка при сохранении файла: {e}")
            
            return all_data
    
    def get_strategy_summary(self) -> Dict[str, Any]:
        """Получает краткую сводку по всем стратегиям"""
        all_data = self.get_all_strategies_data()
        
        summary = {
            "timestamp": all_data["timestamp"],
            "strategies_count": all_data["summary"]["total_strategies"],
            "active_strategies": all_data["summary"]["active_strategies"],
            "total_trades": all_data["summary"]["total_trades"],
            "total_profit": all_data["summary"]["total_profit"],
            "strategies": {}
        }
        
        for strategy_name, strategy_data in all_data["strategies"].items():
            if "error" not in strategy_data:
                trades_count = len(strategy_data.get("data", {}).get("trades", []))
                summary["strategies"][strategy_name] = {
                    "status": "active",
                    "trades_count": trades_count,
                    "last_update": strategy_data.get("timestamp", "")
                }
            else:
                summary["strategies"][strategy_name] = {
                    "status": "error",
                    "error": strategy_data["error"],
                    "last_update": datetime.now().isoformat()
                }
        
        return summary
    
    def get_recent_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Получает последние сделки всех стратегий"""
        all_data = self.get_all_strategies_data()
        recent_trades = []
        
        for strategy_name, strategy_data in all_data["strategies"].items():
            if "error" not in strategy_data:
                trades = strategy_data.get("data", {}).get("trades", [])
                for trade in trades:
                    if isinstance(trade, dict):
                        trade["strategy"] = strategy_name
                        recent_trades.append(trade)
        
        # Сортируем по дате закрытия, обрабатывая None значения
        recent_trades.sort(
            key=lambda x: x.get("close_date", "") or x.get("open_date", ""),
            reverse=True
        )
        
        return recent_trades[:limit]
    
    def get_profit_analysis(self) -> Dict[str, Any]:
        """Получает анализ прибыли по стратегиям"""
        all_data = self.get_all_strategies_data()
        
        profit_analysis = {
            "timestamp": all_data["timestamp"],
            "by_strategy": {},
            "total": {
                "trades": 0,
                "profit": 0.0,
                "winning_trades": 0,
                "losing_trades": 0
            }
        }
        
        total_trades = 0
        total_profit = 0.0
        total_winning = 0
        total_losing = 0
        
        for strategy_name, strategy_data in all_data["strategies"].items():
            if "error" not in strategy_data:
                trades = strategy_data.get("data", {}).get("trades", [])
                strategy_trades = 0
                strategy_profit = 0.0
                strategy_winning = 0
                strategy_losing = 0
                
                for trade in trades:
                    if isinstance(trade, dict):
                        # Пробуем разные поля для прибыли
                        profit_value = None
                        if "profit_ratio" in trade:
                            profit_value = trade["profit_ratio"]
                        elif "realized_profit" in trade:
                            # Конвертируем realized_profit в процент от stake_amount
                            try:
                                stake_amount = float(trade.get("stake_amount", 1))
                                if stake_amount > 0:
                                    profit_value = float(trade["realized_profit"]) / stake_amount
                            except (ValueError, TypeError):
                                pass
                        elif "close_profit" in trade:
                            # Конвертируем close_profit в процент от stake_amount
                            try:
                                stake_amount = float(trade.get("stake_amount", 1))
                                if stake_amount > 0:
                                    profit_value = float(trade["close_profit"]) / stake_amount
                            except (ValueError, TypeError):
                                pass
                        
                        if profit_value is not None:
                            try:
                                profit_ratio = float(profit_value)
                                if not pd.isna(profit_ratio):
                                    strategy_trades += 1
                                    strategy_profit += profit_ratio
                                    
                                    if profit_ratio > 0:
                                        strategy_winning += 1
                                    elif profit_ratio < 0:
                                        strategy_losing += 1
                            except (ValueError, TypeError):
                                pass
                
                profit_analysis["by_strategy"][strategy_name] = {
                    "trades": strategy_trades,
                    "profit": round(strategy_profit, 4),
                    "winning_trades": strategy_winning,
                    "losing_trades": strategy_losing,
                    "win_rate": round(strategy_winning / max(strategy_trades, 1) * 100, 2)
                }
                
                total_trades += strategy_trades
                total_profit += strategy_profit
                total_winning += strategy_winning
                total_losing += strategy_losing
        
        profit_analysis["total"]["trades"] = total_trades
        profit_analysis["total"]["profit"] = round(total_profit, 4)
        profit_analysis["total"]["winning_trades"] = total_winning
        profit_analysis["total"]["losing_trades"] = total_losing
        profit_analysis["total"]["win_rate"] = round(total_winning / max(total_trades, 1) * 100, 2)
        
        return profit_analysis
    
    def export_for_streamlit(self):
        """Экспортирует все данные для Streamlit в удобном формате"""
        logger.info("Экспортируем данные для Streamlit...")
        
        # Основные данные
        all_data = self.get_all_strategies_data()
        
        # Сводка
        summary = self.get_strategy_summary()
        
        # Анализ прибыли
        profit_analysis = self.get_profit_analysis()
        
        # Последние сделки
        recent_trades = self.get_recent_trades(100)
        
        # Создаем структуру для Streamlit
        streamlit_data = {
            "last_update": datetime.now().isoformat(),
            "summary": summary,
            "profit_analysis": profit_analysis,
            "recent_trades": recent_trades,
            "strategies": all_data["strategies"]
        }
        
        # Сохраняем в файл
        output_file = self.output_dir / "streamlit_data.json"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(streamlit_data, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"Данные для Streamlit сохранены в {output_file}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении данных для Streamlit: {e}")
            return False

def main():
    """Основная функция для запуска агрегатора"""
    aggregator = FreqTradeDataAggregator()
    
    # Экспортируем данные для Streamlit
    success = aggregator.export_for_streamlit()
    
    if success:
        print("✅ Данные успешно экспортированы для Streamlit")
        print(f"📁 Файл: {aggregator.output_dir}/streamlit_data.json")
        
        # Показываем краткую статистику
        summary = aggregator.get_strategy_summary()
        print(f"\n📊 Статистика:")
        print(f"   Всего стратегий: {summary['strategies_count']}")
        print(f"   Активных: {summary['active_strategies']}")
        print(f"   Всего сделок: {summary['total_trades']}")
        print(f"   Общая прибыль: {summary['total_profit']:.4f}")
    else:
        print("❌ Ошибка при экспорте данных")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
