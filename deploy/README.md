# 🚀 FreqTrade Production Deployment с Git-синхронизацией

Полная система развертывания FreqTrade на удаленном сервере с автоматическим перезапуском стратегий при изменении кода.

## 🎯 Что это дает

- **Изолированные стратегии**: Каждая стратегия работает в отдельном Docker контейнере
- **Автоматический деплой**: Изменили код → `git push` → стратегия перезапустилась автоматически
- **Непрерывность FreqAI**: Обучение других стратегий не прерывается при обновлении одной
- **Изолированные данные**: Каждая стратегия имеет свои модели, БД и логи в Docker томах
- **Мониторинг**: Streamlit дашборд для просмотра результатов всех стратегий
- **Минимум зависимостей**: Только Docker + Git + Bash

## 🏗️ Архитектура

```
Локальная машина                    Удаленный сервер
┌─────────────────┐                 ┌─────────────────────────────────┐
│                 │                 │                                 │
│  Ваш код       │  git push       │  Bare Git repo                   │
│  FreqTrade     │ ──────────────→ │  (deploy.git)                    │
│                 │                 │                                 │
│  git remote    │                 │  ↓ post-receive hook             │
│  add prod      │                 │                                 │
└─────────────────┘                 │  Рабочая копия (app/)           │
                                    │  ↓                              │
                                    │  Docker Compose                 │
                                    │  ┌─────────────────────────────┐│
                                    │  │ ft-bandtastic              ││
                                    │  │ ft-rsi                     ││
                                    │  │ ft-strategy001             ││
                                    │  │ ft-bandtastic-freqai       ││
                                    │  │ ft-highfreq-ai             ││
                                    │  │ ft-freqai-example          ││
                                    │  │ streamlit                  ││
                                    │  └─────────────────────────────┘│
                                    └─────────────────────────────────┘
```

## 📋 Требования

### На удаленном сервере

- Ubuntu 20.04+ / Debian 11+
- Минимум 8GB RAM
- Минимум 4 CPU ядра
- 50GB свободного места
- Root доступ или sudo права

### На локальной машине

- Git
- SSH клиент
- Bash (Linux/macOS) или Git Bash (Windows)

## 🚀 Быстрый старт

### 1. Настройка удаленного сервера

```bash
# Подключаемся к серверу
ssh root@your-server-ip

# Скачиваем и запускаем скрипт настройки
wget https://raw.githubusercontent.com/your-repo/freqtrade/main/deploy/setup-server.sh
chmod +x setup-server.sh
sudo ./setup-server.sh
```

Скрипт автоматически:

- Установит Docker и Docker Compose
- Создаст пользователя `freqtrader`
- Настроит Git репозиторий с hooks
- Создаст структуру директорий
- Настроит systemd сервис
- Откроет порты в firewall

### 2. Настройка локальной машины

```bash
# Клонируем ваш проект (если еще не сделали)
git clone https://github.com/your-username/your-freqtrade-repo
cd your-freqtrade-repo

# Делаем скрипт исполняемым
chmod +x deploy/setup-local.sh

# Настраиваем SSH подключение
./deploy/setup-local.sh setup-ssh freqtrader your-server-ip

# Добавляем удаленный репозиторий
./deploy/setup-local.sh add-remote freqtrader your-server-ip
```

### 3. Первый деплой

```bash
# Пушим код на сервер
./deploy/setup-local.sh deploy
```

Сервер автоматически:

- Склонирует ваш код
- Запустит все Docker контейнеры
- Запустит стратегии и Streamlit дашборд

## 🔧 Управление

### Локальные команды

```bash
# Деплой изменений
./deploy/setup-local.sh deploy

# Проверка статуса сервера
./deploy/setup-local.sh status freqtrader your-server-ip

# Просмотр логов
./deploy/setup-local.sh logs freqtrader your-server-ip ft-bandtastic
```

### Удаленные команды (через SSH)

```bash
# Подключение к серверу
ssh freqtrader@your-server-ip

# Управление сервисами
sudo /opt/freqtrade/manage.sh start          # Запустить все
sudo /opt/freqtrade/manage.sh stop           # Остановить все
sudo /opt/freqtrade/manage.sh restart ft-bandtastic  # Перезапустить одну
sudo /opt/freqtrade/manage.sh status         # Статус
sudo /opt/freqtrade/manage.sh logs ft-bandtastic     # Логи стратегии
sudo /opt/freqtrade/manage.sh backup         # Создать бэкап
```

## 📊 Мониторинг

### Streamlit дашборд

- URL: `http://your-server-ip:8501`
- Показывает результаты всех стратегий
- Read-only доступ к базам данных и логам

### Логи

- Логи деплоя: `/opt/freqtrade/deploy.log`
- Логи стратегий: `sudo /opt/freqtrade/manage.sh logs SERVICE_NAME`
- Docker логи: `docker compose logs -f SERVICE_NAME`

## 🔄 Рабочий процесс

### Обычная разработка

1. **Редактируете стратегию** локально
2. **Коммитите изменения**: `git add . && git commit -m "Update strategy"`
3. **Деплоите**: `./deploy/setup-local.sh deploy`
4. **Сервер автоматически**:
   - Определяет какие файлы изменились
   - Перезапускает только затронутые стратегии
   - Остальные стратегии продолжают работать

### Примеры изменений

```bash
# Изменили Bandtastic стратегию → перезапустится только ft-bandtastic
vim user_data/strategies/Bandtastic.py
./deploy/setup-local.sh deploy

# Изменили конфиг RSI → перезапустится только ft-rsi
vim user_data/configs/config_rsi.json
./deploy/setup-local.sh deploy

# Изменили docker-compose.yml → перезапустятся все сервисы
vim docker-compose.yml
./deploy/setup-local.sh deploy
```

## 🐳 Docker контейнеры

### Стратегии

- **ft-bandtastic**: Обычная стратегия Bandtastic
- **ft-rsi**: RSI стратегия
- **ft-strategy001**: Стратегия 001
- **ft-bandtastic-freqai**: FreqAI версия Bandtastic
- **ft-highfreq-ai**: Высокочастотная AI стратегия
- **ft-freqai-example**: Пример FreqAI стратегии

### Мониторинг

- **streamlit**: Streamlit дашборд

### Ресурсы

- **Обычные стратегии**: 1 CPU, 2GB RAM
- **FreqAI стратегии**: 2 CPU, 4GB RAM
- **Streamlit**: 0.5 CPU, 1GB RAM

## 💾 Данные и тома

### Изолированные тома для каждой стратегии

```
bandtastic_models      # Модели Bandtastic
bandtastic_db          # База данных Bandtastic
bandtastic_logs        # Логи Bandtastic
bandtastic_freqai      # FreqAI модели Bandtastic

rsi_models            # Модели RSI
rsi_db                # База данных RSI
rsi_logs              # Логи RSI
rsi_freqai            # FreqAI модели RSI

# ... и так далее для каждой стратегии
```

### Преимущества изоляции

- **Безопасность**: Стратегии не могут повлиять друг на друга
- **Производительность**: Нет конкуренции за ресурсы
- **Отладка**: Легко найти проблему в конкретной стратегии
- **Масштабирование**: Можно запускать на разных серверах

## 🔐 Безопасность

### SSH ключи

- Автоматическая генерация Ed25519 ключей
- Копирование на сервер через `ssh-copy-id`
- Отключение парольной аутентификации

### Docker изоляция

- Каждая стратегия в отдельном контейнере
- Read-only доступ к коду
- Ограничения ресурсов (CPU, RAM)
- Сетевые изоляции

### Firewall

- Открыт только SSH (22) и Streamlit (8501)
- Все остальные порты заблокированы

## 🚨 Troubleshooting

### Проблемы с SSH

```bash
# Проверить подключение
ssh -v freqtrader@your-server-ip

# Пересоздать ключи
rm ~/.ssh/id_ed25519*
./deploy/setup-local.sh setup-ssh freqtrader your-server-ip
```

### Проблемы с Docker

```bash
# Проверить статус
sudo /opt/freqtrade/manage.sh status

# Перезапустить все
sudo /opt/freqtrade/manage.sh restart

# Просмотреть логи
sudo /opt/freqtrade/manage.sh logs
```

### Проблемы с деплоем

```bash
# Проверить логи деплоя
tail -f /opt/freqtrade/deploy.log

# Проверить Git hook
cat /opt/freqtrade/deploy.git/hooks/post-receive

# Перезапустить Git hook
chmod +x /opt/freqtrade/deploy.git/hooks/post-receive
```

## 📈 Масштабирование

### Добавление новой стратегии

1. **Создайте стратегию** в `user_data/strategies/`
2. **Создайте конфиг** в `user_data/configs/`
3. **Добавьте сервис** в `docker-compose.yml`
4. **Обновите Git hook** в `deploy/post-receive`
5. **Деплойте**: `./deploy/setup-local.sh deploy`

### Пример добавления сервиса

```yaml
# В docker-compose.yml
ft-new-strategy:
  image: freqtradeorg/freqtrade:stable_freqaitorch
  container_name: ft-new-strategy
  restart: unless-stopped
  working_dir: /app
  command: >
    trade
    --config user_data/configs/config_new_strategy.json
    --strategy NewStrategy
    --disable-api-server
  volumes:
    - ./app:/app:ro
    - new_strategy_models:/app/user_data/models
    - new_strategy_db:/app/user_data/databases
    - new_strategy_logs:/app/user_data/logs
  environment:
    - PYTHONPATH=/app
    - FREQTRADE_USER_DATA_DIR=/app/user_data
    - FREQTRADE_LOG_LEVEL=INFO
```

### Множественные серверы

Можно развернуть на нескольких серверах:

- **Сервер 1**: Стратегии 1-3
- **Сервер 2**: Стратегии 4-6
- **Сервер 3**: Мониторинг и Streamlit

## 🔄 Обновления

### Обновление FreqTrade

```bash
# На сервере
cd /opt/freqtrade
docker compose pull
docker compose up -d
```

### Обновление системы

```bash
# На сервере
sudo apt update && sudo apt upgrade -y
sudo reboot
```

## 📚 Дополнительные ресурсы

- [FreqTrade документация](https://www.freqtrade.io/en/latest/)
- [Docker Compose документация](https://docs.docker.com/compose/)
- [Git hooks документация](https://git-scm.com/docs/githooks)

## 🤝 Поддержка

При возникновении проблем:

1. Проверьте логи: `sudo /opt/freqtrade/manage.sh logs`
2. Проверьте статус: `sudo /opt/freqtrade/manage.sh status`
3. Проверьте логи деплоя: `tail -f /opt/freqtrade/deploy.log`
4. Создайте issue в репозитории

---

**🎉 Готово! Теперь у вас есть профессиональная система развертывания FreqTrade с автоматическим деплоем и изолированными стратегиями.**
