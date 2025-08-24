#!/usr/bin/env python3
"""
Скрипт для копирования баз данных из контейнеров стратегий
в общую папку для data-aggregator
"""

import os
import shutil
import subprocess
import time
from pathlib import Path
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(cmd):
    """Выполняет команду и возвращает результат"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        logger.error(f"Ошибка выполнения команды '{cmd}': {e}")
        return False, "", str(e)

def copy_database_from_container(container_name, source_path, target_path):
    """Копирует базу данных из контейнера"""
    try:
        # Создаем целевую папку
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Копируем файл из контейнера
        cmd = f"docker cp {container_name}:{source_path} {target_path}"
        success, stdout, stderr = run_command(cmd)
        
        if success:
            logger.info(f"✅ Скопирована БД из {container_name}: {source_path} -> {target_path}")
            return True
        else:
            logger.error(f"❌ Ошибка копирования из {container_name}: {stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка копирования БД из {container_name}: {e}")
        return False

def main():
    """Основная функция"""
    logger.info("🚀 Запуск копирования баз данных стратегий...")
    
    # Папка для общих баз данных
    shared_db_dir = Path("/tmp/shared_databases")
    shared_db_dir.mkdir(exist_ok=True)
    
    # Конфигурация стратегий и их контейнеров
    strategies = {
        'bandtastic': {
            'container': 'ft_bandtastic_02-local',
            'db_file': 'Bandtastic.sqlite'
        },
        'rsi': {
            'container': 'ft_rsistrategy_14-local', 
            'db_file': 'RsiStrategy.sqlite'
        },
        'strategy001': {
            'container': 'ft_strategy001_16-local',
            'db_file': 'Strategy001.sqlite'
        },
        'bandtastic_freqai': {
            'container': 'ft_bandtasticfreqai_04-local',
            'db_file': 'BandtasticFreqAI.sqlite'
        },
        'bandtastic_freqai_hyperopt': {
            'container': 'ft_bandtasticfreqaihyperopt_06-local',
            'db_file': 'BandtasticFreqAIHyperOpt.sqlite'
        },
        'freqai_example': {
            'container': 'ft_freqaiexamplestrategy_08-local',
            'db_file': 'FreqaiExampleStrategy.sqlite'
        },
        'highfreq_ai': {
            'container': 'ft_highfreqaistrategy_10-local',
            'db_file': 'HighFreqAIStrategy.sqlite'
        },
        'highfreq_ai_hyperopt': {
            'container': 'ft_highfreqaistrategyhyperopt_12-local',
            'db_file': 'HighFreqAIStrategyHyperOpt.sqlite'
        }
    }
    
    copied_count = 0
    
    for strategy_name, config in strategies.items():
        container_name = config['container']
        db_file = config['db_file']
        
        source_path = f"/app/user_data/dryrun_db/{db_file}"
        target_path = shared_db_dir / db_file
        
        logger.info(f"📋 Копирование БД для {strategy_name}...")
        
        if copy_database_from_container(container_name, source_path, target_path):
            copied_count += 1
    
    logger.info(f"✅ Копирование завершено! Скопировано {copied_count} из {len(strategies)} баз данных")
    logger.info(f"📁 Общая папка: {shared_db_dir}")
    
    # Показываем содержимое общей папки
    if shared_db_dir.exists():
        logger.info("📊 Содержимое общей папки:")
        for file_path in shared_db_dir.glob("*.sqlite"):
            size = file_path.stat().st_size
            logger.info(f"  📄 {file_path.name} ({size} bytes)")

if __name__ == "__main__":
    main()
