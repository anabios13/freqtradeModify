#!/usr/bin/env python3
"""
Скрипт для копирования баз данных из всех томов в общий том
"""

import shutil
import os
from pathlib import Path
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def copy_databases():
    """Копирует базы данных из всех томов в общий том"""
    
    # Создаем общую папку для баз данных
    common_db_dir = Path("/tmp/aggregated_data/databases")
    common_db_dir.mkdir(parents=True, exist_ok=True)
    
    # Список томов с базами данных
    volumes = [
        ("bandtastic_db_local", "bandtastic.sqlite"),
        ("rsi_db_local", "rsi.sqlite"),
        ("s001_db_local", "strategy001.sqlite"),
        ("bandtastic_freqai_db_local", "bandtastic_freqai.sqlite"),
        ("highfreq_ai_db_local", "highfreq_ai.sqlite"),
        ("freqai_example_db_local", "freqai_example.sqlite")
    ]
    
    copied_count = 0
    
    for volume_name, db_file in volumes:
        try:
            # Путь к базе данных в томе
            source_path = Path(f"/app/user_data/databases/{db_file}")
            
            # Путь назначения в общем томе
            dest_path = common_db_dir / db_file
            
            if source_path.exists():
                # Копируем базу данных
                shutil.copy2(source_path, dest_path)
                logger.info(f"Скопирована база данных: {db_file}")
                copied_count += 1
            else:
                logger.warning(f"База данных не найдена: {source_path}")
                
        except Exception as e:
            logger.error(f"Ошибка при копировании {db_file}: {e}")
    
    logger.info(f"Скопировано баз данных: {copied_count}")
    return copied_count

if __name__ == "__main__":
    copy_databases()
