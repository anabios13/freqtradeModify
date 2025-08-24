#!/usr/bin/env python3
"""
Автоматическая генерация docker-compose файла для FreqTrade
Загружает все стратегии и конфигурации из папок и создает соответствующие сервисы
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
import argparse
from datetime import datetime

class DockerComposeGenerator:
    """Генератор docker-compose файла для FreqTrade"""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.strategies_dir = self.base_dir / "user_data" / "strategies"
        self.configs_dir = self.base_dir / "user_data" / "dryrun_configs"
        self.scripts_dir = self.base_dir / "scripts"
        
        # Шаблоны для определения типа стратегии
        self.freqai_patterns = [
            r'freqai', r'FreqAI', r'hyperopt', r'HyperOpt'
        ]
        
        # Стратегии, которые нужно исключить
        self.exclude_patterns = [
            r'StopLossTrail'
        ]
        
        # Счетчики для именования
        self.service_counter = 0
        self.port_counter = 0  # Счетчик для портов API
        
    def is_freqai_strategy(self, strategy_name: str) -> bool:
        """Определяет, является ли стратегия FreqAI"""
        strategy_lower = strategy_name.lower()
        return any(re.search(pattern, strategy_lower) for pattern in self.freqai_patterns)
    
    def should_exclude_strategy(self, strategy_name: str) -> bool:
        """Определяет, нужно ли исключить стратегию"""
        strategy_lower = strategy_name.lower()
        return any(re.search(pattern, strategy_lower) for pattern in self.exclude_patterns)
    
    def get_strategy_files(self) -> List[Tuple[str, Path]]:
        """Получает список файлов стратегий"""
        strategies = []
        
        if not self.strategies_dir.exists():
            print(f"Папка стратегий не найдена: {self.strategies_dir}")
            return strategies
        
        for file_path in self.strategies_dir.glob("*.py"):
            if file_path.name.startswith("__"):
                continue
                
            strategy_name = file_path.stem
            
            # Пропускаем исключенные стратегии
            if self.should_exclude_strategy(strategy_name):
                print(f"Пропускаем стратегию: {strategy_name} (исключена)")
                continue
            
            strategies.append((strategy_name, file_path))
            print(f"Найдена стратегия: {strategy_name}")
        
        return strategies
    
    def get_config_files(self) -> List[Tuple[str, Path]]:
        """Получает список файлов конфигураций"""
        configs = []
        
        if not self.configs_dir.exists():
            print(f"Папка конфигураций не найдена: {self.configs_dir}")
            return configs
        
        for file_path in self.configs_dir.glob("config_*.json"):
            config_name = file_path.stem.replace("config_", "")
            configs.append((config_name, file_path))
            print(f"Найдена конфигурация: {config_name}")
        
        return configs
    
    def find_matching_config(self, strategy_name: str, configs: List[Tuple[str, Path]]) -> Path:
        """Находит подходящую конфигурацию для стратегии"""
        # Сортируем конфигурации по длине названия (от длинных к коротким)
        # Это обеспечивает приоритет более специфичных конфигураций
        sorted_configs = sorted(configs, key=lambda x: len(x[0]), reverse=True)
        
        # Ищем точное совпадение
        for config_name, config_path in sorted_configs:
            if config_name.lower() == strategy_name.lower():
                return config_path
        
        # Ищем конфигурацию, которая содержит полное название стратегии
        # Это обеспечивает точное сопоставление
        for config_name, config_path in sorted_configs:
            if strategy_name.lower() in config_name.lower():
                return config_path
        
        return None
    
    def generate_service_name(self, strategy_name: str) -> str:
        """Генерирует имя сервиса для Docker"""
        # Убираем специальные символы и приводим к нижнему регистру
        service_name = re.sub(r'[^a-zA-Z0-9]', '_', strategy_name).lower()
        service_name = re.sub(r'_+', '_', service_name).strip('_')
        
        # Добавляем префикс для уникальности
        self.service_counter += 1
        return f"ft_{service_name}_{self.service_counter:02d}"
    
    def generate_container_name(self, strategy_name: str) -> str:
        """Генерирует имя контейнера"""
        service_name = self.generate_service_name(strategy_name)
        return f"{service_name}-local"
    
    def generate_volume_names(self, strategy_name: str) -> Dict[str, str]:
        """Генерирует имена томов для стратегии"""
        base_name = strategy_name.lower().replace(' ', '_')
        return {
            'models': f"{base_name}_models_local",
            'db': f"{base_name}_db_local",
            'logs': f"{base_name}_logs_local",
            'freqai': f"{base_name}_freqai_local",
            'data': f"{base_name}_data_local"
        }
    
    def get_api_port_from_config(self, strategy_name: str, config_path: Path) -> int:
        """Получает порт API из конфигурации стратегии"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Возвращаем сохраненный порт
            if "_api_port" in config_data:
                return config_data["_api_port"]
            else:
                # Если порт не найден, возвращаем порт по умолчанию
                print(f"      ⚠️  Порт API не найден для {strategy_name}, используем 8100")
                return 8100
        except Exception as e:
            print(f"      ⚠️  Ошибка чтения порта API для {strategy_name}: {e}")
            # Возвращаем порт по умолчанию
            return 8100
    
    def generate_freqtrade_service(self, strategy_name: str, config_path: Path, is_freqai: bool) -> str:
        """Генерирует сервис FreqTrade для стратегии"""
        service_name = self.generate_service_name(strategy_name)
        container_name = self.generate_container_name(strategy_name)
        volumes = self.generate_volume_names(strategy_name)
        
        # Определяем образ в зависимости от типа стратегии
        image = "freqtradeorg/freqtrade:stable_freqaitorch" if is_freqai else "freqtradeorg/freqtrade:stable"
        
        # Определяем команду (учитываем, что образ уже имеет ENTRYPOINT для freqtrade)
        if is_freqai:
            command = f'trade --config /app/user_data/configs/{config_path.name} --freqaimodel LightGBMRegressor'
        else:
            command = f'trade --config /app/user_data/configs/{config_path.name}'
        
        # Получаем порт API из конфигурации
        api_port = self.get_api_port_from_config(strategy_name, config_path)
        
        # Генерируем YAML для сервиса
        service_yaml = f"""  {service_name}:
    image: {image}
    container_name: {container_name}
    restart: unless-stopped
    working_dir: /app
    command: {command}
    ports:
      - "{api_port}:{api_port}"  # Прокидываем REST API порт наружу
    volumes:
      - ./user_data:/app/user_data:ro
      - {volumes['models']}:/app/user_data/models
      - shared_databases_local:/app/user_data/dryrun_db
      - {volumes['logs']}:/app/user_data/logs"""
        
        # Добавляем FreqAI тома если нужно
        if is_freqai:
            service_yaml += f"""
      - {volumes['freqai']}:/app/user_data/freqaimodels
      - {volumes['data']}:/app/user_data/data"""
        
        service_yaml += f"""
    environment:
      - PYTHONPATH=/app
      - PYTHONUNBUFFERED=1
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 1G
        reservations:
          cpus: "0.2"
          memory: 512M
"""
        
        return service_yaml
    
    def generate_volumes_section(self, strategies: List[Tuple[str, Path]]) -> str:
        """Генерирует секцию volumes"""
        volumes = []
        
        for strategy_name, _ in strategies:
            strategy_volumes = self.generate_volume_names(strategy_name)
            volumes.extend(strategy_volumes.values())
        
        # Добавляем общие тома
        volumes.extend([
            "aggregated_data_local",
            "shared_models_local",
            "shared_databases_local"
        ])
        
        volumes_yaml = "volumes:\n"
        for volume in sorted(set(volumes)):
            volumes_yaml += f"  {volume}:\n"
        
        return volumes_yaml
    
    def create_docker_config(self, strategy_name: str, original_config_path: Path) -> Path:
        """Создает исправленную конфигурацию для Docker"""
        # Создаем папку configs если её нет
        configs_dir = self.base_dir / "user_data" / "configs"
        configs_dir.mkdir(exist_ok=True)
        
        # Читаем оригинальную конфигурацию
        with open(original_config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # Исправляем конфигурацию для Docker
        docker_config = self.fix_config_for_docker(config_data, strategy_name)
        
        # Сохраняем исправленную конфигурацию
        docker_config_path = configs_dir / f"config_{strategy_name}.json"
        with open(docker_config_path, 'w', encoding='utf-8') as f:
            json.dump(docker_config, f, indent=2, ensure_ascii=False)
        
        print(f"    📝 Создана Docker конфигурация: {docker_config_path.name}")
        return docker_config_path
    
    def fix_config_for_docker(self, config: dict, strategy_name: str) -> dict:
        """Исправляет конфигурацию для работы в Docker"""
        # Создаем копию конфигурации
        docker_config = config.copy()
        
        # Убираем проблемные параметры логирования
        if "logfile" in docker_config:
            del docker_config["logfile"]
            print(f"      🔧 Убран параметр logfile")
        
        # ВКЛЮЧАЕМ API сервер для каждой стратегии с последовательным портом
        if "api_server" not in docker_config:
            docker_config["api_server"] = {}
        
        # Генерируем последовательный порт для стратегии (начиная с 8100)
        self.port_counter += 1
        api_port = 8100 + self.port_counter - 1
        
        docker_config["api_server"]["enabled"] = True  # ВКЛЮЧАЕМ API!
        docker_config["api_server"]["listen_ip_address"] = "0.0.0.0"
        docker_config["api_server"]["listen_port"] = api_port
        docker_config["api_server"]["username"] = "freqtrader"
        docker_config["api_server"]["password"] = "SuperSecurePassword"
        docker_config["api_server"]["verbosity"] = "info"
        
        # Сохраняем порт для использования в docker-compose
        docker_config["_api_port"] = api_port
        
        print(f"      🔧 ВКЛЮЧЕН API сервер на порту {api_port}")
        
        # Исправляем пути к базе данных для Docker
        if "db_url" in docker_config:
            # Извлекаем имя стратегии из db_url
            db_name = strategy_name
            # Используем правильный путь к существующим базам данных
            docker_config["db_url"] = f"sqlite:///user_data/dryrun_db/{db_name}.sqlite"
            print(f"      🔧 Исправлен путь к БД: {docker_config['db_url']}")
        
        # Добавляем недостающие параметры для FreqAI стратегий
        if self.is_freqai_strategy(strategy_name) and "freqai" in docker_config:
            if "feature_parameters" in docker_config["freqai"]:
                if "include_timeframes" not in docker_config["freqai"]["feature_parameters"]:
                    docker_config["freqai"]["feature_parameters"]["include_timeframes"] = ["5m"]
                if "indicator_periods_candles" not in docker_config["freqai"]["feature_parameters"]:
                    docker_config["freqai"]["feature_parameters"]["indicator_periods_candles"] = [10, 20]
                print(f"      🔧 Добавлены недостающие FreqAI параметры")
        
        return docker_config
    
    def generate_docker_compose(self, output_file: str = "docker-compose-auto.yml") -> None:
        """Генерирует полный docker-compose файл"""
        print("🔍 Поиск стратегий и конфигураций...")
        
        strategies = self.get_strategy_files()
        configs = self.get_config_files()
        
        if not strategies:
            print("❌ Стратегии не найдены!")
            return
        
        print(f"\n📊 Найдено стратегий: {len(strategies)}")
        print(f"📋 Найдено конфигураций: {len(configs)}")
        
        # Сначала определяем активные стратегии и создаем исправленные конфигурации
        print("\n🔧 Определение активных стратегий и создание конфигураций...")
        active_strategies = []
        
        for strategy_name, strategy_path in strategies:
            config_path = self.find_matching_config(strategy_name, configs)
            if config_path:
                print(f"  ✅ {strategy_name} -> {config_path.name}")
                # Создаем исправленную конфигурацию для Docker
                docker_config_path = self.create_docker_config(strategy_name, config_path)
                active_strategies.append((strategy_name, strategy_path, docker_config_path))
            else:
                print(f"  ⏭️  {strategy_name} -> конфигурация не найдена, пропускаем")
        
        if not active_strategies:
            print("  ❌ Нет активных стратегий для запуска!")
            return
        
        # Генерируем содержимое файла
        content = f"""# Автоматически сгенерированный docker-compose файл для FreqTrade
# Создан скриптом generate_docker_compose.py
# Время генерации: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

version: '3.8'

services:
  # Data Aggregator для сбора данных всех стратегий
  data-aggregator:
    image: python:3.11-slim
    container_name: data-aggregator-local
    restart: unless-stopped
    working_dir: /app
    command: >
      bash -c "
        apt-get update && apt-get install -y curl &&
        pip install pandas numpy &&
        python scripts/data_aggregator.py
      "
    volumes:
      - .:/app:ro
      - shared_models_local:/app/user_data/models:ro
      - aggregated_data_local:/tmp/aggregated_data:rw"""
        
        # Добавляем монтирование каждой базы данных в отдельную папку
        # Убираем индивидуальные тома, так как они перезаписывают друг друга
        # for strategy_name, strategy_path, config_path in active_strategies:
        #     volume_name = self.generate_volume_names(strategy_name)['db']
        #     content += f"\n      - {volume_name}:/app/user_data/dryrun_db:ro"
        
        # Добавляем общую папку для баз данных
        content += f"\n      - shared_databases_local:/app/user_data/dryrun_db:ro"
        
        content += """
    environment:
      - PYTHONPATH=/app
      - PYTHONUNBUFFERED=1
    deploy:
      resources:
        limits:
          cpus: "0.3"
          memory: 512M
        reservations:
          cpus: "0.1"
          memory: 256M

  # Streamlit дашборд
  streamlit:
    image: python:3.11-slim
    container_name: freqtrade-dashboard-local
    restart: unless-stopped
    working_dir: /app
    command: >
      bash -c "
        apt-get update && apt-get install -y curl &&
        pip install streamlit pandas plotly numpy &&
        streamlit run scripts/strategy_dashboard_restored.py --server.port 8501 --server.address 0.0.0.0
      "
    volumes:
      - .:/app:ro
      - aggregated_data_local:/tmp/aggregated_data:ro
    ports:
      - "8501:8501"
    environment:
      - PYTHONPATH=/app
      - PYTHONUNBUFFERED=1
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 1G
        reservations:
          cpus: "0.2"
          memory: 512M
    depends_on:
      - data-aggregator

"""
        
        # Добавляем сервисы для активных стратегий
        print("\n🔧 Генерация сервисов...")
        
        for strategy_name, strategy_path, docker_config_path in active_strategies:
            is_freqai = self.is_freqai_strategy(strategy_name)
            
            print(f"  🔧 Создание сервиса для {strategy_name}")
            service_yaml = self.generate_freqtrade_service(strategy_name, docker_config_path, is_freqai)
            content += service_yaml + "\n"
        
        # Добавляем секцию volumes только для активных стратегий
        content += "\n" + self.generate_volumes_section([(name, path) for name, path, _ in active_strategies])
        
        # Записываем файл
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"\n✅ Docker-compose файл создан: {output_path}")
        print(f"📊 Всего сервисов: {len(active_strategies) + 2} (активные стратегии + data-aggregator + streamlit)")
        print(f"📈 Активных стратегий: {len(active_strategies)}")
        print(f"⏭️  Пропущено стратегий: {len(strategies) - len(active_strategies)}")
        
        # Создаем также скрипт для запуска
        self.generate_launch_script(output_file)
    
    def generate_launch_script(self, compose_file: str) -> None:
        """Создает скрипт для запуска системы"""
        script_content = f"""#!/bin/bash
# Скрипт для запуска автоматически сгенерированной системы FreqTrade

COMPOSE_FILE="{compose_file}"

echo "🚀 Запуск системы FreqTrade..."
echo "📁 Используется файл: $COMPOSE_FILE"

# Проверяем существование файла
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ Файл $COMPOSE_FILE не найден!"
    echo "Запустите сначала: python scripts/generate_docker_compose.py"
    exit 1
fi

# Останавливаем существующие сервисы
echo "🛑 Остановка существующих сервисов..."
docker-compose -f "$COMPOSE_FILE" down

# Запускаем новые сервисы
echo "▶️  Запуск сервисов..."
docker-compose -f "$COMPOSE_FILE" up -d

# Показываем статус
echo "📊 Статус сервисов:"
docker-compose -f "$COMPOSE_FILE" ps

echo ""
echo "🌐 Streamlit дашборд доступен по адресу: http://localhost:8501"
echo "📝 Логи data-aggregator: docker-compose -f $COMPOSE_FILE logs data-aggregator"
echo "🔄 Перезапуск: docker-compose -f $COMPOSE_FILE restart"
echo "⏹️  Остановка: docker-compose -f $COMPOSE_FILE down"
"""
        
        script_path = Path("deploy/launch-auto.sh")
        script_path.parent.mkdir(exist_ok=True)
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # Делаем скрипт исполняемым
        os.chmod(script_path, 0o755)
        
        print(f"📜 Скрипт запуска создан: {script_path}")

def main():
    parser = argparse.ArgumentParser(description="Генератор docker-compose для FreqTrade")
    parser.add_argument("--output", "-o", default="docker-compose-auto.yml", 
                       help="Имя выходного файла (по умолчанию: docker-compose-auto.yml)")
    parser.add_argument("--base-dir", "-b", default=".", 
                       help="Базовая директория проекта (по умолчанию: текущая)")
    parser.add_argument("--create-configs", "-c", action="store_true",
                       help="Создать недостающие конфигурации")
    
    args = parser.parse_args()
    
    print("🚀 Генератор docker-compose для FreqTrade")
    print("=" * 50)
    
    generator = DockerComposeGenerator(args.base_dir)
    
    if args.create_configs:
        strategies = generator.get_strategy_files()
        configs = generator.get_config_files()
        generator.create_missing_configs(strategies, configs)
    
    generator.generate_docker_compose(args.output)
    
    print("\n🎉 Готово! Теперь можно запустить:")
    print(f"   docker-compose -f {args.output} up -d")
    print(f"   или использовать скрипт: ./deploy/launch-auto.sh")

if __name__ == "__main__":
    from datetime import datetime
    main()
