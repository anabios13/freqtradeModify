# Автоматическая система FreqTrade

## Обзор

Автоматическая система позволяет динамически создавать docker-compose файлы на основе найденных стратегий и конфигураций в папках проекта. Больше не нужно вручную редактировать docker-compose файлы при добавлении новых стратегий!

## Как это работает

1. **Автоматическое сканирование** папок `user_data/strategies` и `user_data/dryrun_configs`
2. **Определение типа стратегии** (обычная или FreqAI) по имени файла
3. **Сопоставление стратегий и конфигураций** с помощью умного алгоритма
4. **Генерация docker-compose файла** со всеми найденными сервисами
5. **Создание недостающих конфигураций** при необходимости

## Быстрый старт

### 1. Генерация docker-compose файла

```bash
# Базовая генерация
python scripts/generate_docker_compose.py

# Создать недостающие конфигурации
python scripts/generate_docker_compose.py --create-configs

# Указать выходной файл
python scripts/generate_docker_compose.py --output my-compose.yml
```

### 2. Запуск системы

**Linux/macOS:**
```bash
./deploy/launch-auto.sh
```

**Windows:**
```powershell
.\deploy\launch-auto.ps1
```

**Или вручную:**
```bash
docker-compose -f docker-compose-auto.yml up -d
```

## Структура автоматически созданных сервисов

### Обычные стратегии
- **Образ:** `freqtradeorg/freqtrade:stable`
- **Тома:** models, db, logs
- **Конфигурация:** из `user_data/dryrun_configs/`

### FreqAI стратегии
- **Образ:** `freqtradeorg/freqtrade:stable_freqaitorch`
- **Тома:** models, db, logs, freqaimodels, data
- **Конфигурация:** с включенным модулем FreqAI

### Общие сервисы
- **data-aggregator:** сбор данных всех стратегий
- **streamlit:** веб-дашборд для мониторинга

## Алгоритм определения типа стратегии

### FreqAI стратегии (включают):
- `freqai` или `FreqAI` в названии
- `hyperopt` или `HyperOpt` в названии

### Исключаемые стратегии:
- `StopLossTrail` (вспомогательные)
- `HyperOpt` (для оптимизации, не торговли)

## Сопоставление стратегий и конфигураций

1. **Прямое совпадение:** `Bandtastic.py` → `config_Bandtastic.json`
2. **Частичное совпадение:** `HighFreqAIStrategy.py` → `config_HighFreqAIStrategy.json`
3. **Автоматическое создание:** если конфигурация не найдена

## Создание недостающих конфигураций

При использовании флага `--create-configs` система автоматически создает базовые конфигурации для стратегий:

```bash
python scripts/generate_docker_compose.py --create-configs
```

### Что создается:
- Базовые параметры торговли
- Настройки биржи (Bybit)
- Список торговых пар
- FreqAI конфигурация (для AI стратегий)

## Примеры использования

### Добавление новой стратегии

1. Поместите файл стратегии в `user_data/strategies/`
2. Поместите конфигурацию в `user_data/dryrun_configs/`
3. Перегенерируйте docker-compose:
   ```bash
   python scripts/generate_docker_compose.py
   ```
4. Перезапустите систему:
   ```bash
   ./deploy/launch-auto.sh
   ```

### Изменение существующей стратегии

1. Отредактируйте файл стратегии или конфигурации
2. Перезапустите только нужный сервис:
   ```bash
   docker-compose -f docker-compose-auto.yml restart <service_name>
   ```

### Мониторинг системы

```bash
# Статус всех сервисов
docker-compose -f docker-compose-auto.yml ps

# Логи конкретной стратегии
docker-compose -f docker-compose-auto.yml logs <service_name>

# Логи data-aggregator
docker-compose -f docker-compose-auto.yml logs data-aggregator

# Мониторинг ресурсов
docker stats
```

## Структура файлов

```
freqtrade/
├── scripts/
│   ├── generate_docker_compose.py    # Генератор docker-compose
│   ├── data_aggregator.py            # Агрегатор данных
│   └── strategy_dashboard_restored.py # Streamlit дашборд
├── user_data/
│   ├── strategies/                    # Python файлы стратегий
│   ├── dryrun_configs/               # JSON конфигурации
│   └── configs/                      # Автоматически созданные конфигурации
├── deploy/
│   ├── launch-auto.sh                # Скрипт запуска (Linux/macOS)
│   ├── launch-auto.ps1               # Скрипт запуска (Windows)
│   └── AUTO_SYSTEM_README.md         # Эта документация
└── docker-compose-auto.yml           # Автоматически сгенерированный файл
```

## Преимущества автоматической системы

### ✅ Автоматизация
- Не нужно вручную редактировать docker-compose
- Автоматическое определение типа стратегии
- Создание недостающих конфигураций

### ✅ Масштабируемость
- Легко добавлять новые стратегии
- Автоматическое создание томов
- Правильное именование сервисов

### ✅ Гибкость
- Поддержка обычных и FreqAI стратегий
- Настраиваемые параметры генерации
- Возможность исключения стратегий

### ✅ Надежность
- Проверка существования файлов
- Валидация конфигураций
- Автоматическое создание папок

## Устранение неполадок

### Проблема: "Стратегии не найдены"
**Решение:** Проверьте, что папка `user_data/strategies` существует и содержит `.py` файлы

### Проблема: "Конфигурация не найдена"
**Решение:** Используйте флаг `--create-configs` для автоматического создания

### Проблема: "Ошибка Docker"
**Решение:** Проверьте, что Docker запущен и доступен

### Проблема: "Порт занят"
**Решение:** Измените порт в конфигурации или остановите конфликтующий сервис

## Расширенные возможности

### Настройка исключений
Отредактируйте `exclude_patterns` в `generate_docker_compose.py` для исключения определенных стратегий.

### Кастомные образы
Измените логику в `generate_freqtrade_service()` для использования других Docker образов.

### Дополнительные тома
Добавьте новые типы томов в `generate_volume_names()`.

## Поддержка

При возникновении проблем:
1. Проверьте логи: `docker-compose -f docker-compose-auto.yml logs`
2. Убедитесь, что все файлы на месте
3. Проверьте права доступа к папкам
4. Перегенерируйте docker-compose файл

---

**🎯 Цель:** Сделать развертывание FreqTrade максимально простым и автоматизированным!
