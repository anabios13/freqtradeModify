# 🧪 Локальное тестирование FreqTrade Production

## 🎯 Цель

Протестировать систему локально перед развертыванием на удаленном сервере. Убедиться, что:

- ✅ Все стратегии запускаются в отдельных контейнерах
- ✅ Изоляция данных работает корректно
- ✅ Перезапуск одной стратегии не влияет на другие
- ✅ Streamlit дашборд отображает данные всех стратегий

## 📋 Требования для локального тестирования

### Windows

- Docker Desktop для Windows
- PowerShell 5.0+
- Минимум 8GB RAM
- Минимум 4 CPU ядра

### Linux/macOS

- Docker Engine
- Docker Compose
- Bash
- Минимум 8GB RAM
- Минимум 4 CPU ядра

## 🚀 Быстрый старт локального тестирования

### 1. Подготовка проекта

```bash
# Убедитесь, что вы в корне проекта FreqTrade
cd /path/to/your/freqtrade-project

# Проверьте наличие файлов
ls -la docker-compose-local-test.yml
ls -la deploy/test-local.sh
ls -la deploy/test-local.ps1
```

### 2. Запуск системы

#### Linux/macOS:

```bash
# Делаем скрипт исполняемым
chmod +x deploy/test-local.sh

# Запускаем все сервисы
./deploy/test-local.sh start
```

#### Windows:

```powershell
# Запускаем все сервисы
.\deploy\test-local.ps1 start
```

**Скрипт автоматически:**

- ✅ Создаст необходимые директории
- ✅ Скопирует конфиги стратегий
- ✅ Запустит все Docker контейнеры
- ✅ Настроит изолированные тома для каждой стратегии

### 3. Проверка работы

```bash
# Проверить статус всех сервисов
./deploy/test-local.sh status

# Открыть Streamlit дашборд
# http://localhost:8501
```

## 🧪 Тестирование изоляции стратегий

### Тест 1: Перезапуск одной стратегии

```bash
# Linux/macOS
./deploy/test-local.sh test-strategy ft-rsi

# Windows
.\deploy\test-local.ps1 test-strategy ft-rsi
```

**Что происходит:**

1. Останавливается только `ft-rsi`
2. Остальные стратегии продолжают работать
3. `ft-rsi` перезапускается заново
4. Проверяется, что изоляция работает

### Тест 2: Проверка логов

```bash
# Логи конкретной стратегии
./deploy/test-local.sh logs ft-bandtastic

# Логи всех сервисов
./deploy/test-local.sh logs
```

### Тест 3: Проверка данных

```bash
# Проверить, что у каждой стратегии свои тома
docker volume ls | grep "_local"

# Должно быть 24 тома:
# - 6 стратегий × 4 тома (models, db, logs, freqai)
```

## 📊 Мониторинг локальной системы

### Streamlit дашборд

- **URL**: `http://localhost:8501`
- **Функции**:
  - Просмотр результатов всех стратегий
  - Анализ производительности
  - Мониторинг FreqAI моделей

### Docker контейнеры

```bash
# Статус контейнеров
docker ps

# Использование ресурсов
docker stats

# Логи в реальном времени
docker-compose -f docker-compose-local-test.yml logs -f
```

## 🔍 Что тестировать

### 1. Изоляция данных

- ✅ Каждая стратегия имеет свои тома
- ✅ Модели не смешиваются между стратегиями
- ✅ Базы данных изолированы
- ✅ Логи разделены

### 2. Производительность

- ✅ Стратегии не конкурируют за ресурсы
- ✅ FreqAI обучение не прерывается
- ✅ Память и CPU ограничены для каждого контейнера

### 3. Сетевая изоляция

- ✅ Каждый контейнер работает независимо
- ✅ Нет конфликтов портов
- ✅ Streamlit доступен на 8501

### 4. Управление жизненным циклом

- ✅ Перезапуск одной стратегии не влияет на другие
- ✅ Автоматический restart при сбоях
- ✅ Graceful shutdown

## 🚨 Устранение проблем

### Проблема: Недостаточно памяти

```bash
# Остановить все сервисы
./deploy/test-local.sh stop

# Увеличить лимиты в docker-compose-local-test.yml
# Или запустить только часть стратегий
docker-compose -f docker-compose-local-test.yml up -d ft-bandtastic ft-rsi streamlit
```

### Проблема: Конфликт портов

```bash
# Проверить, что занято порт 8501
netstat -tulpn | grep 8501

# Изменить порт в docker-compose-local-test.yml
ports:
  - "8502:8501"  # Внешний порт 8502
```

### Проблема: Ошибки в логах

```bash
# Просмотреть логи проблемного сервиса
./deploy/test-local.sh logs ft-bandtastic

# Перезапустить конкретный сервис
docker-compose -f docker-compose-local-test.yml restart ft-bandtastic
```

## 🔄 Переход к продакшену

### После успешного локального тестирования:

1. **Проверьте конфиги**:

   ```bash
   # Убедитесь, что все конфиги корректны
   cat user_data/configs/config_bandtastic.json
   ```

2. **Настройте продакшен**:

   ```bash
   # На удаленном сервере
   ./deploy/setup-server.sh

   # На локальной машине
   ./deploy/setup-local.sh setup-ssh freqtrader your-server-ip
   ./deploy/setup-local.sh add-remote freqtrader your-server-ip
   ```

3. **Деплой на продакшен**:
   ```bash
   ./deploy/setup-local.sh deploy
   ```

## 📝 Полезные команды

### Управление сервисами

```bash
# Запуск
./deploy/test-local.sh start

# Остановка
./deploy/test-local.sh stop

# Перезапуск
./deploy/test-local.sh restart

# Статус
./deploy/test-local.sh status
```

### Мониторинг

```bash
# Логи всех сервисов
./deploy/test-local.sh logs

# Логи конкретного сервиса
./deploy/test-local.sh logs ft-bandtastic

# Тест изоляции
./deploy/test-local.sh test-strategy ft-rsi
```

### Очистка

```bash
# Очистить все данные (НЕОБРАТИМО!)
./deploy/test-local.sh cleanup
```

## 🎯 Результат тестирования

После успешного локального тестирования вы должны убедиться, что:

1. **Все 6 стратегий** запускаются в отдельных контейнерах
2. **Изоляция данных** работает корректно
3. **Перезапуск одной стратегии** не влияет на другие
4. **FreqAI обучение** не прерывается при обновлениях
5. **Streamlit дашборд** отображает данные всех стратегий
6. **Ресурсы** ограничены и не конфликтуют

## 🚀 Следующий шаг

После успешного локального тестирования переходите к развертыванию на удаленном сервере:

1. **Настройка сервера**: `./deploy/setup-server.sh`
2. **Настройка локальной машины**: `./deploy/setup-local.sh`
3. **Первый деплой**: `./deploy/setup-local.sh deploy`

---

**🎉 Локальное тестирование завершено! Система готова к продакшену!**
