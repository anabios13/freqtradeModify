#!/bin/bash
set -euo pipefail

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции логирования
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверяем, что скрипт запущен от root или с sudo
if [[ $EUID -ne 0 ]]; then
   log_error "Этот скрипт должен быть запущен с правами root (sudo)"
   exit 1
fi

# Конфигурация
FREQTRADE_DIR="/opt/freqtrade"
FREQTRADE_USER="freqtrader"
DOCKER_GROUP="docker"

log_info "🚀 Настройка сервера для FreqTrade с Git-деплоем..."

# 1. Обновляем систему
log_info "📦 Обновляем систему..."
apt-get update
apt-get upgrade -y

# 2. Устанавливаем необходимые пакеты
log_info "📥 Устанавливаем необходимые пакеты..."
apt-get install -y \
    git \
    curl \
    wget \
    htop \
    nano \
    vim \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# 3. Устанавливаем Docker
log_info "🐳 Устанавливаем Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    log_success "Docker установлен"
else
    log_info "Docker уже установлен"
fi

# 4. Устанавливаем Docker Compose
log_info "📋 Устанавливаем Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    log_success "Docker Compose установлен"
else
    log_info "Docker Compose уже установлен"
fi

# 5. Создаем пользователя для FreqTrade
log_info "👤 Создаем пользователя $FREQTRADE_USER..."
if ! id "$FREQTRADE_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$FREQTRADE_USER"
    usermod -aG sudo "$FREQTRADE_USER"
    log_success "Пользователь $FREQTRADE_USER создан"
else
    log_info "Пользователь $FREQTRADE_USER уже существует"
fi

# 6. Добавляем пользователя в группу docker
log_info "🔐 Настраиваем права Docker..."
usermod -aG docker "$FREQTRADE_USER"
systemctl enable docker
systemctl start docker

# 7. Создаем структуру директорий
log_info "📁 Создаем структуру директорий..."
mkdir -p "$FREQTRADE_DIR"/{app,deploy.git,logs,backups}
chown -R "$FREQTRADE_USER:$FREQTRADE_USER" "$FREQTRADE_DIR"

# 8. Настраиваем bare Git репозиторий
log_info "🔧 Настраиваем Git репозиторий..."
cd "$FREQTRADE_DIR/deploy.git"
git init --bare

# 9. Создаем post-receive hook
log_info "🎣 Создаем Git hook..."
cat > hooks/post-receive <<'HOOK'
#!/usr/bin/env bash
set -euo pipefail

# Конфигурация
WORKTREE="/opt/freqtrade/app"
COMPOSE_DIR="/opt/freqtrade"
LOG_FILE="/opt/freqtrade/deploy.log"

# Логирование
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "🚀 Начало деплоя..."

# Проверяем аргументы
if [ $# -ne 3 ]; then
    log "❌ Неверное количество аргументов: $#"
    exit 1
fi

oldrev="$1"
newrev="$2"
refname="$3"

log "📝 Обновление: $oldrev -> $newrev ($refname)"

# Работаем только с main веткой
if [[ "$refname" != "refs/heads/main" ]]; then
    log "⚠️  Пропускаем ветку: $refname"
    exit 0
fi

# Первый деплой (когда старый ревиз — нули)
if [[ "$oldrev" =~ ^0+$ ]]; then
    log "🎯 Первый деплой - создаем рабочую копию"
    if [ ! -d "$WORKTREE/.git" ]; then
        mkdir -p "$WORKTREE"
        git --work-tree="$WORKTREE" --git-dir="$(pwd)" checkout -f "$newrev"
    else
        git --work-tree="$WORKTREE" --git-dir="$(pwd)" checkout -f "$newrev"
    fi
    
    cd "$COMPOSE_DIR"
    log "🚀 Запускаем все сервисы..."
    docker compose up -d
    log "✅ Первый деплой завершен"
    exit 0
fi

# Обычный обновляющий деплой
log "📥 Обновляем рабочую копию..."
git --work-tree="$WORKTREE" --git-dir="$(pwd)" checkout -f "$newrev"

# Получаем список измененных файлов
log "🔍 Анализируем изменения..."
CHANGED_FILES=$(git --git-dir="$(pwd)" diff --name-only "$oldrev" "$newrev" || true)

if [ -z "$CHANGED_FILES" ]; then
    log "ℹ️  Файлы не изменились"
    exit 0
fi

log "📋 Измененные файлы:"
echo "$CHANGED_FILES" | while read -r file; do
    log "   - $file"
done

# Маппинг: какие файлы → какой сервис перезапускать
RESTART_SERVICES=""

# Обычные стратегии
if echo "$CHANGED_FILES" | grep -qE 'user_data/strategies/Bandtastic\.py|user_data/configs/config_bandtastic\.json'; then
    RESTART_SERVICES="$RESTART_SERVICES ft-bandtastic"
    log "🔄 Будет перезапущен: ft-bandtastic"
fi

if echo "$CHANGED_FILES" | grep -qE 'user_data/strategies/RsiStrategy\.py|user_data/configs/config_rsi\.json'; then
    RESTART_SERVICES="$RESTART_SERVICES ft-rsi"
    log "🔄 Будет перезапущен: ft-rsi"
fi

if echo "$CHANGED_FILES" | grep -qE 'user_data/strategies/Strategy001\.py|user_data/configs/config_strategy001\.json'; then
    RESTART_SERVICES="$RESTART_SERVICES ft-strategy001"
    log "🔄 Будет перезапущен: ft-strategy001"
fi

# FreqAI стратегии
if echo "$CHANGED_FILES" | grep -qE 'user_data/strategies/BandtasticFreqAI\.py|user_data/configs/config_bandtastic_freqai\.json'; then
    RESTART_SERVICES="$RESTART_SERVICES ft-bandtastic-freqai"
    log "🔄 Будет перезапущен: ft-bandtastic-freqai"
fi

if echo "$CHANGED_FILES" | grep -qE 'user_data/strategies/HighFreqAIStrategy\.py|user_data/configs/config_highfreq_ai\.json'; then
    RESTART_SERVICES="$RESTART_SERVICES ft-highfreq-ai"
    log "🔄 Будет перезапущен: ft-highfreq-ai"
fi

if echo "$CHANGED_FILES" | grep -qE 'user_data/strategies/FreqAIExampleStrategy\.py|user_data/configs/config_freqai_example\.json'; then
    RESTART_SERVICES="$RESTART_SERVICES ft-freqai-example"
    log "🔄 Будет перезапущен: ft-freqai-example"
fi

# Если меняли общие файлы/compose/дашборд — поднимаем всех
if echo "$CHANGED_FILES" | grep -qE '(^|/)docker-compose\.yml|(^|/)scripts/|(^|/)requirements\.txt|(^|/)\.env'; then
    log "🔄 Общие файлы изменены - перезапускаем все сервисы"
    cd "$COMPOSE_DIR"
    docker compose up -d
    log "✅ Все сервисы перезапущены"
    exit 0
fi

# Точечный перезапуск
if [ -n "$RESTART_SERVICES" ]; then
    log "🎯 Перезапускаем сервисы: $RESTART_SERVICES"
    cd "$COMPOSE_DIR"
    
    # Останавливаем только нужные сервисы
    docker compose stop $RESTART_SERVICES
    
    # Ждем завершения
    sleep 5
    
    # Запускаем заново
    docker compose up -d $RESTART_SERVICES
    
    log "✅ Сервисы перезапущены: $RESTART_SERVICES"
else
    log "ℹ️  Нет стратегий для перезапуска"
fi

log "🎉 Деплой завершен успешно"
HOOK

chmod +x hooks/post-receive
chown -R "$FREQTRADE_USER:$FREQTRADE_USER" "$FREQTRADE_DIR/deploy.git"

# 10. Создаем .env файл
log_info "⚙️  Создаем .env файл..."
cat > "$FREQTRADE_DIR/.env" <<'ENV'
# FreqTrade Production Environment
COMPOSE_PROJECT_NAME=freqtrade-prod

# Exchange credentials (заполните своими данными)
EXCHANGE_NAME=bybit
EXCHANGE_KEY=your_exchange_key_here
EXCHANGE_SECRET=your_exchange_secret_here

# Telegram (опционально)
TELEGRAM_TOKEN=your_telegram_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# Database
DB_URL=sqlite:///user_data/databases/

# Logging
LOG_LEVEL=INFO
LOG_FILE=user_data/logs/

# FreqAI settings
FREQAI_MODEL_PATH=user_data/freqaimodels/
FREQAI_CACHE_PATH=user_data/models/
ENV

chown "$FREQTRADE_USER:$FREQTRADE_USER" "$FREQTRADE_DIR/.env"

# 11. Создаем docker-compose.yml
log_info "🐳 Создаем docker-compose.yml..."
cat > "$FREQTRADE_DIR/docker-compose.yml" <<'COMPOSE'
version: "3.8"

services:
  # Обычные стратегии
  ft-bandtastic:
    image: freqtradeorg/freqtrade:stable_freqaitorch
    container_name: ft-bandtastic
    restart: unless-stopped
    working_dir: /app
    command: >
      trade
      --config user_data/configs/config_bandtastic.json
      --strategy Bandtastic
      --disable-api-server
    volumes:
      - ./app:/app:ro
      - bandtastic_models:/app/user_data/models
      - bandtastic_db:/app/user_data/databases
      - bandtastic_logs:/app/user_data/logs
      - bandtastic_freqai:/app/user_data/freqaimodels
    environment:
      - PYTHONPATH=/app
      - FREQTRADE_USER_DATA_DIR=/app/user_data
      - FREQTRADE_LOG_LEVEL=INFO
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 2G
        reservations:
          cpus: "0.5"
          memory: 1G

  ft-rsi:
    image: freqtradeorg/freqtrade:stable_freqaitorch
    container_name: ft-rsi
    restart: unless-stopped
    working_dir: /app
    command: >
      trade
      --config user_data/configs/config_rsi.json
      --strategy RsiStrategy
      --disable-api-server
    volumes:
      - ./app:/app:ro
      - rsi_models:/app/user_data/models
      - rsi_db:/app/user_data/databases
      - rsi_logs:/app/user_data/logs
      - rsi_freqai:/app/user_data/freqaimodels
    environment:
      - PYTHONPATH=/app
      - FREQTRADE_USER_DATA_DIR=/app/user_data
      - FREQTRADE_LOG_LEVEL=INFO
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 2G
        reservations:
          cpus: "0.5"
          memory: 1G

  ft-strategy001:
    image: freqtradeorg/freqtrade:stable_freqaitorch
    container_name: ft-strategy001
    restart: unless-stopped
    working_dir: /app
    command: >
      trade
      --config user_data/configs/config_strategy001.json
      --strategy Strategy001
      --disable-api-server
    volumes:
      - ./app:/app:ro
      - s001_models:/app/user_data/models
      - s001_db:/app/user_data/databases
      - s001_logs:/app/user_data/logs
      - s001_freqai:/app/user_data/freqaimodels
    environment:
      - PYTHONPATH=/app
      - FREQTRADE_USER_DATA_DIR=/app/user_data
      - FREQTRADE_LOG_LEVEL=INFO
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 2G
        reservations:
          cpus: "0.5"
          memory: 1G

  # FreqAI стратегии
  ft-bandtastic-freqai:
    image: freqtradeorg/freqtrade:stable_freqaitorch
    container_name: ft-bandtastic-freqai
    restart: unless-stopped
    working_dir: /app
    command: >
      trade
      --config user_data/configs/config_bandtastic_freqai.json
      --strategy BandtasticFreqAI
      --freqaimodel LightGBMRegressor
      --disable-api-server
    volumes:
      - ./app:/app:ro
      - bandtastic_freqai_models:/app/user_data/models
      - bandtastic_freqai_db:/app/user_data/databases
      - bandtastic_freqai_logs:/app/user_data/logs
      - bandtastic_freqai_freqai:/app/user_data/freqaimodels
    environment:
      - PYTHONPATH=/app
      - FREQTRADE_USER_DATA_DIR=/app/user_data
      - FREQTRADE_LOG_LEVEL=INFO
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 4G
        reservations:
          cpus: "1.0"
          memory: 2G

  ft-highfreq-ai:
    image: freqtradeorg/freqtrade:stable_freqaitorch
    container_name: ft-highfreq-ai
    restart: unless-stopped
    working_dir: /app
    command: >
      trade
      --config user_data/configs/config_highfreq_ai.json
      --strategy HighFreqAIStrategy
      --freqaimodel LightGBMRegressor
      --disable-api-server
    volumes:
      - ./app:/app:ro
      - highfreq_ai_models:/app/user_data/models
      - highfreq_ai_db:/app/user_data/databases
      - highfreq_ai_logs:/app/user_data/logs
      - highfreq_ai_freqai:/app/user_data/freqaimodels
    environment:
      - PYTHONPATH=/app
      - FREQTRADE_USER_DATA_DIR=/app/user_data
      - FREQTRADE_LOG_LEVEL=INFO
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 4G
        reservations:
          cpus: "1.0"
          memory: 2G

  ft-freqai-example:
    image: freqtradeorg/freqtrade:stable_freqaitorch
    container_name: ft-freqai-example
    restart: unless-stopped
    working_dir: /app
    command: >
      trade
      --config user_data/configs/config_freqai_example.json
      --strategy FreqAIExampleStrategy
      --freqaimodel LightGBMRegressor
      --disable-api-server
    volumes:
      - ./app:/app:ro
      - freqai_example_models:/app/user_data/models
      - freqai_example_db:/app/user_data/databases
      - freqai_example_logs:/app/user_data/logs
      - freqai_example_freqai:/app/user_data/freqaimodels
    environment:
      - PYTHONPATH=/app
      - FREQTRADE_USER_DATA_DIR=/app/user_data
      - FREQTRADE_LOG_LEVEL=INFO
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 4G
        reservations:
          cpus: "1.0"
          memory: 2G

  # Streamlit дашборд
  streamlit:
    image: python:3.11-slim
    container_name: freqtrade-dashboard
    restart: unless-stopped
    working_dir: /app/scripts
    command: >
      bash -c "
        apt-get update && apt-get install -y procps net-tools curl wget &&
        pip install streamlit plotly pandas numpy &&
        streamlit run strategy_dashboardWEB.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true
      "
    volumes:
      - ./app:/app:ro
      # Read-only доступ к базам данных для мониторинга
      - bandtastic_db:/app/user_data/databases:ro
      - rsi_db:/app/user_data/databases:ro
      - s001_db:/app/user_data/databases:ro
      - bandtastic_freqai_db:/app/user_data/databases:ro
      - highfreq_ai_db:/app/user_data/databases:ro
      - freqai_example_db:/app/user_data/databases:ro
      # Read-only доступ к логам
      - bandtastic_logs:/app/user_data/logs:ro
      - rsi_logs:/app/user_data/logs:ro
      - s001_logs:/app/user_data/logs:ro
      - bandtastic_freqai_logs:/app/user_data/logs:ro
      - highfreq_ai_logs:/app/user_data/logs:ro
      - freqai_example_logs:/app/user_data/logs:ro
    ports:
      - "8501:8501"
    environment:
      - PYTHONPATH=/app
      - PYTHONUNBUFFERED=1
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 2G
        reservations:
          cpus: "0.5"
          memory: 1G

volumes:
  # Обычные стратегии
  bandtastic_models:
  bandtastic_db:
  bandtastic_logs:
  bandtastic_freqai:
  
  rsi_models:
  rsi_db:
  rsi_logs:
  rsi_freqai:
  
  s001_models:
  s001_db:
  s001_logs:
  s001_freqai:
  
  # FreqAI стратегии
  bandtastic_freqai_models:
  bandtastic_freqai_db:
  bandtastic_freqai_logs:
  bandtastic_freqai_freqai:
  
  highfreq_ai_models:
  highfreq_ai_db:
  highfreq_ai_logs:
  highfreq_ai_freqai:
  
  freqai_example_models:
  freqai_example_db:
  freqai_example_logs:
  freqai_example_freqai:
COMPOSE

chown "$FREQTRADE_USER:$FREQTRADE_USER" "$FREQTRADE_DIR/docker-compose.yml"

# 12. Создаем скрипт управления
log_info "🔧 Создаем скрипт управления..."
cat > "$FREQTRADE_DIR/manage.sh" <<'MANAGE'
#!/bin/bash
set -euo pipefail

FREQTRADE_DIR="/opt/freqtrade"
COMPOSE_FILE="$FREQTRADE_DIR/docker-compose.yml"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    echo "FreqTrade Management Script"
    echo ""
    echo "Usage: $0 [COMMAND] [SERVICE]"
    echo ""
    echo "Commands:"
    echo "  start [SERVICE]     - Запустить все сервисы или конкретный"
    echo "  stop [SERVICE]      - Остановить все сервисы или конкретный"
    echo "  restart [SERVICE]   - Перезапустить все сервисы или конкретный"
    echo "  status              - Показать статус всех сервисов"
    echo "  logs [SERVICE]      - Показать логи всех сервисов или конкретного"
    echo "  update              - Обновить код из Git и перезапустить"
    echo "  backup              - Создать бэкап данных"
    echo "  help                - Показать эту справку"
    echo ""
    echo "Services:"
    echo "  ft-bandtastic       - Стратегия Bandtastic"
    echo "  ft-rsi              - Стратегия RSI"
    echo "  ft-strategy001      - Стратегия 001"
    echo "  ft-bandtastic-freqai - FreqAI Bandtastic"
    echo "  ft-highfreq-ai      - FreqAI High Frequency"
    echo "  ft-freqai-example   - FreqAI Example"
    echo "  streamlit           - Streamlit дашборд"
}

cd "$FREQTRADE_DIR"

case "${1:-help}" in
    start)
        if [ -n "${2:-}" ]; then
            log_info "Запускаем сервис: $2"
            docker compose -f "$COMPOSE_FILE" up -d "$2"
        else
            log_info "Запускаем все сервисы..."
            docker compose -f "$COMPOSE_FILE" up -d
        fi
        log_success "Готово!"
        ;;
    stop)
        if [ -n "${2:-}" ]; then
            log_info "Останавливаем сервис: $2"
            docker compose -f "$COMPOSE_FILE" stop "$2"
        else
            log_info "Останавливаем все сервисы..."
            docker compose -f "$COMPOSE_FILE" stop
        fi
        log_success "Готово!"
        ;;
    restart)
        if [ -n "${2:-}" ]; then
            log_info "Перезапускаем сервис: $2"
            docker compose -f "$COMPOSE_FILE" restart "$2"
        else
            log_info "Перезапускаем все сервисы..."
            docker compose -f "$COMPOSE_FILE" restart
        fi
        log_success "Готово!"
        ;;
    status)
        log_info "Статус сервисов:"
        docker compose -f "$COMPOSE_FILE" ps
        ;;
    logs)
        if [ -n "${2:-}" ]; then
            log_info "Логи сервиса $2:"
            docker compose -f "$COMPOSE_FILE" logs -f "$2"
        else
            log_info "Логи всех сервисов:"
            docker compose -f "$COMPOSE_FILE" logs -f
        fi
        ;;
    update)
        log_info "Обновляем код из Git..."
        cd "$FREQTRADE_DIR/app"
        git pull origin main
        cd "$FREQTRADE_DIR"
        log_info "Перезапускаем все сервисы..."
        docker compose -f "$COMPOSE_FILE" up -d
        log_success "Обновление завершено!"
        ;;
    backup)
        log_info "Создаем бэкап данных..."
        BACKUP_DIR="$FREQTRADE_DIR/backups/$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        
        # Бэкап баз данных
        docker compose -f "$COMPOSE_FILE" exec -T ft-bandtastic sqlite3 /app/user_data/databases/bandtastic.sqlite ".backup $BACKUP_DIR/bandtastic.sqlite" || true
        docker compose -f "$COMPOSE_FILE" exec -T ft-rsi sqlite3 /app/user_data/databases/rsi.sqlite ".backup $BACKUP_DIR/rsi.sqlite" || true
        
        # Бэкап моделей
        cp -r "$FREQTRADE_DIR/app/user_data/models" "$BACKUP_DIR/" || true
        cp -r "$FREQTRADE_DIR/app/user_data/freqaimodels" "$BACKUP_DIR/" || true
        
        log_success "Бэкап создан в: $BACKUP_DIR"
        ;;
    help|*)
        show_help
        ;;
esac
MANAGE

chmod +x "$FREQTRADE_DIR/manage.sh"
chown "$FREQTRADE_USER:$FREQTRADE_USER" "$FREQTRADE_DIR/manage.sh"

# 13. Создаем systemd сервис для автозапуска
log_info "🔧 Создаем systemd сервис..."
cat > /etc/systemd/system/freqtrade.service <<'SERVICE'
[Unit]
Description=FreqTrade Trading Bot
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/freqtrade
ExecStart=/opt/freqtrade/manage.sh start
ExecStop=/opt/freqtrade/manage.sh stop
ExecReload=/opt/freqtrade/manage.sh restart
User=freqtrader
Group=freqtrader

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable freqtrade.service

# 14. Настраиваем firewall (если включен)
if command -v ufw &> /dev/null; then
    log_info "🔥 Настраиваем firewall..."
    ufw allow 22/tcp    # SSH
    ufw allow 8501/tcp  # Streamlit
    ufw --force enable
    log_success "Firewall настроен"
fi

# 15. Создаем README
log_info "📖 Создаем документацию..."
cat > "$FREQTRADE_DIR/README.md" <<'README'
# FreqTrade Production Server

## Структура проекта
```
/opt/freqtrade/
├── app/                    # Рабочая копия кода
├── deploy.git/            # Bare Git репозиторий
├── logs/                  # Логи деплоя
├── backups/               # Бэкапы данных
├── docker-compose.yml     # Docker Compose конфигурация
├── .env                   # Переменные окружения
├── manage.sh              # Скрипт управления
└── README.md              # Эта документация
```

## Управление

### Основные команды
```bash
# Запуск всех сервисов
sudo /opt/freqtrade/manage.sh start

# Остановка всех сервисов
sudo /opt/freqtrade/manage.sh stop

# Перезапуск конкретной стратегии
sudo /opt/freqtrade/manage.sh restart ft-bandtastic

# Просмотр статуса
sudo /opt/freqtrade/manage.sh status

# Просмотр логов
sudo /opt/freqtrade/manage.sh logs ft-bandtastic

# Создание бэкапа
sudo /opt/freqtrade/manage.sh backup
```

### Git деплой
```bash
# Добавить удаленный репозиторий на локальной машине
git remote add prod ssh-user@your-server:/opt/freqtrade/deploy.git

# Деплой
git push prod main
```

## Мониторинг
- Streamlit дашборд: http://your-server:8501
- Логи деплоя: /opt/freqtrade/deploy.log
- Docker логи: docker compose logs -f

## Безопасность
- Все сервисы запускаются в изолированных контейнерах
- Данные хранятся в именованных Docker томах
- Read-only доступ к коду для контейнеров
- Отдельные тома для каждой стратегии

## Troubleshooting
1. Проверить статус: `sudo /opt/freqtrade/manage.sh status`
2. Просмотреть логи: `sudo /opt/freqtrade/manage.sh logs`
3. Перезапустить сервис: `sudo /opt/freqtrade/manage.sh restart SERVICE_NAME`
4. Проверить логи деплоя: `tail -f /opt/freqtrade/deploy.log`
README

chown "$FREQTRADE_USER:$FREQTRADE_USER" "$FREQTRADE_DIR/README.md"

# 16. Финальные настройки
log_info "🔐 Настраиваем права доступа..."
chown -R "$FREQTRADE_USER:$FREQTRADE_USER" "$FREQTRADE_DIR"

# 17. Выводим итоговую информацию
log_success "🎉 Настройка сервера завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Настройте SSH ключи для пользователя $FREQTRADE_USER"
echo "2. Отредактируйте /opt/freqtrade/.env с вашими данными"
echo "3. Добавьте удаленный репозиторий на локальной машине:"
echo "   git remote add prod $FREQTRADE_USER@$(hostname):/opt/freqtrade/deploy.git"
echo "4. Сделайте первый push: git push prod main"
echo ""
echo "📊 Управление сервисами:"
echo "   sudo /opt/freqtrade/manage.sh start|stop|restart|status"
echo ""
echo "🌐 Streamlit дашборд будет доступен на порту 8501"
echo "📁 Все файлы находятся в /opt/freqtrade/"
echo ""
echo "🔐 Пользователь: $FREQTRADE_USER"
echo "🐳 Docker группа: $DOCKER_GROUP"
echo "📝 Логи деплоя: /opt/freqtrade/deploy.log"
