#!/bin/bash
set -euo pipefail

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

show_help() {
    echo "FreqTrade Local Testing Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start                    - Запустить все сервисы для тестирования"
    echo "  stop                     - Остановить все сервисы"
    echo "  restart                  - Перезапустить все сервисы"
    echo "  status                   - Показать статус всех сервисов"
    echo "  logs [SERVICE]           - Показать логи всех сервисов или конкретного"
    echo "  test-strategy SERVICE    - Перезапустить конкретную стратегию (тест изоляции)"
    echo "  cleanup                  - Очистить все данные и тома"
    echo "  help                     - Показать эту справку"
    echo ""
    echo "Services:"
    echo "  ft-bandtastic            - Стратегия Bandtastic"
    echo "  ft-rsi                   - Стратегия RSI"
    echo "  ft-strategy001           - Стратегия 001"
    echo "  ft-bandtastic-freqai     - FreqAI Bandtastic"
    echo "  ft-highfreq-ai           - FreqAI High Frequency"
    echo "  ft-freqai-example        - FreqAI Example"
    echo "  streamlit                - Streamlit дашборд"
    echo ""
    echo "Examples:"
    echo "  $0 start                 # Запустить все"
    echo "  $0 test-strategy ft-rsi  # Перезапустить только RSI стратегию"
    echo "  $0 logs ft-bandtastic    # Логи Bandtastic"
}

# Проверяем, что мы в корне проекта
check_project_root() {
    if [ ! -f "docker-compose-local-test.yml" ]; then
        log_error "Этот скрипт должен быть запущен в корне проекта FreqTrade"
        log_info "Перейдите в папку с docker-compose-local-test.yml"
        exit 1
    fi
}

# Проверяем Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker не установлен"
        log_info "Установите Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker не запущен или нет прав"
        log_info "Запустите Docker и убедитесь, что у вас есть права на его использование"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose не установлен"
        log_info "Установите Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
}

# Создаем необходимые директории
create_directories() {
    log_info "📁 Создаем необходимые директории..."
    
    mkdir -p user_data/{configs,strategies,logs,databases,models,freqaimodels}
    
    # Копируем конфиги если их нет
    if [ ! -f "user_data/configs/config_bandtastic.json" ]; then
        log_info "📋 Копируем конфиги стратегий..."
        cp deploy/configs/*.json user_data/configs/
        log_success "Конфиги скопированы"
    fi
    
    log_success "Директории созданы"
}

# Запуск всех сервисов
start_services() {
    log_info "🚀 Запускаем все сервисы для тестирования..."
    
    create_directories
    
    # Запускаем с локальным docker-compose
    docker-compose -f docker-compose-local-test.yml up -d
    
    log_success "Все сервисы запущены!"
    log_info "🌐 Streamlit дашборд: http://localhost:8501"
    log_info "📊 Проверить статус: $0 status"
    log_info "📝 Просмотр логов: $0 logs"
}

# Остановка всех сервисов
stop_services() {
    log_info "🛑 Останавливаем все сервисы..."
    
    docker-compose -f docker-compose-local-test.yml down
    
    log_success "Все сервисы остановлены"
}

# Перезапуск всех сервисов
restart_services() {
    log_info "🔄 Перезапускаем все сервисы..."
    
    docker-compose -f docker-compose-local-test.yml restart
    
    log_success "Все сервисы перезапущены"
}

# Показать статус
show_status() {
    log_info "📊 Статус сервисов:"
    
    docker-compose -f docker-compose-local-test.yml ps
}

# Показать логи
show_logs() {
    local service="${1:-}"
    
    if [ -n "$service" ]; then
        log_info "📝 Логи сервиса $service:"
        docker-compose -f docker-compose-local-test.yml logs -f "$service"
    else
        log_info "📝 Логи всех сервисов:"
        docker-compose -f docker-compose-local-test.yml logs -f
    fi
}

# Тест изоляции стратегий
test_strategy_isolation() {
    local service="$1"
    
    if [ -z "$service" ]; then
        log_error "Укажите сервис для тестирования"
        log_info "Пример: $0 test-strategy ft-rsi"
        exit 1
    fi
    
    log_info "🧪 Тестируем изоляцию стратегии: $service"
    log_info "Перезапускаем только $service, остальные должны продолжать работать..."
    
    # Останавливаем только указанный сервис
    docker-compose -f docker-compose-local-test.yml stop "$service"
    
    log_info "⏸️  $service остановлен. Проверяем, что остальные работают..."
    sleep 3
    
    # Показываем статус
    docker-compose -f docker-compose-local-test.yml ps
    
    log_info "🔄 Запускаем $service заново..."
    docker-compose -f docker-compose-local-test.yml up -d "$service"
    
    log_success "Тест изоляции завершен!"
    log_info "Проверьте, что $service перезапустился, а остальные продолжают работать"
}

# Очистка данных
cleanup_data() {
    log_warning "🗑️  Очищаем все данные и тома..."
    log_warning "Это действие НЕОБРАТИМО! Все данные будут удалены!"
    
    read -p "Вы уверены? (y/N): " -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_info "Очистка отменена"
        exit 0
    fi
    
    log_info "Останавливаем сервисы..."
    docker-compose -f docker-compose-local-test.yml down
    
    log_info "Удаляем тома..."
    docker volume rm $(docker volume ls -q | grep "_local$") 2>/dev/null || true
    
    log_info "Удаляем локальные данные..."
    rm -rf user_data/{logs,databases,models,freqaimodels}/* 2>/dev/null || true
    
    log_success "Очистка завершена"
}

# Основная логика
main() {
    check_project_root
    check_docker
    
    case "${1:-help}" in
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "${2:-}"
            ;;
        test-strategy)
            test_strategy_isolation "$2"
            ;;
        cleanup)
            cleanup_data
            ;;
        help|*)
            show_help
            ;;
    esac
}

# Запуск
main "$@"
