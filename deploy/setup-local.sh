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
    echo "FreqTrade Local Setup Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  setup-ssh SERVER_USER SERVER_IP    - Настроить SSH подключение"
    echo "  add-remote SERVER_USER SERVER_IP   - Добавить удаленный репозиторий"
    echo "  deploy                              - Деплой на сервер"
    echo "  status SERVER_USER SERVER_IP        - Проверить статус сервера"
    echo "  logs SERVER_USER SERVER_IP SERVICE  - Просмотр логов"
    echo "  help                                - Показать эту справку"
    echo ""
    echo "Examples:"
    echo "  $0 setup-ssh freqtrader 192.168.1.100"
    echo "  $0 add-remote freqtrader 192.168.1.100"
    echo "  $0 deploy"
    echo "  $0 status freqtrader 192.168.1.100"
}

# Проверяем, что мы в Git репозитории
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Этот скрипт должен быть запущен в Git репозитории"
        exit 1
    fi
}

# Настройка SSH подключения
setup_ssh() {
    local server_user="$1"
    local server_ip="$2"
    
    log_info "🔑 Настройка SSH подключения к $server_user@$server_ip..."
    
    # Проверяем существование SSH ключа
    if [ ! -f ~/.ssh/id_ed25519 ]; then
        log_info "Создаем новый SSH ключ..."
        ssh-keygen -t ed25519 -C "freqtrade-prod" -f ~/.ssh/id_ed25519 -N ""
        log_success "SSH ключ создан"
    else
        log_info "SSH ключ уже существует"
    fi
    
    # Копируем публичный ключ на сервер
    log_info "Копируем публичный ключ на сервер..."
    ssh-copy-id -i ~/.ssh/id_ed25519.pub "$server_user@$server_ip"
    
    # Тестируем подключение
    log_info "Тестируем SSH подключение..."
    if ssh -o ConnectTimeout=10 "$server_user@$server_ip" "echo 'SSH подключение работает!'"; then
        log_success "SSH подключение настроено успешно!"
    else
        log_error "Не удалось установить SSH подключение"
        exit 1
    fi
}

# Добавление удаленного репозитория
add_remote() {
    local server_user="$1"
    local server_ip="$2"
    
    check_git_repo
    
    log_info "🔗 Добавляем удаленный репозиторий..."
    
    # Удаляем существующий remote если есть
    if git remote get-url prod > /dev/null 2>&1; then
        log_info "Удаляем существующий remote 'prod'..."
        git remote remove prod
    fi
    
    # Добавляем новый remote
    local remote_url="$server_user@$server_ip:/opt/freqtrade/deploy.git"
    git remote add prod "$remote_url"
    
    log_success "Удаленный репозиторий добавлен: $remote_url"
    
    # Тестируем подключение
    log_info "Тестируем подключение к удаленному репозиторию..."
    if git ls-remote prod > /dev/null 2>&1; then
        log_success "Подключение к удаленному репозиторию работает!"
    else
        log_error "Не удалось подключиться к удаленному репозиторию"
        exit 1
    fi
}

# Деплой на сервер
deploy() {
    check_git_repo
    
    log_info "🚀 Деплой на сервер..."
    
    # Проверяем, что есть remote prod
    if ! git remote get-url prod > /dev/null 2>&1; then
        log_error "Remote 'prod' не настроен. Сначала выполните: $0 add-remote USER IP"
        exit 1
    fi
    
    # Проверяем статус Git
    if ! git diff-index --quiet HEAD --; then
        log_warning "У вас есть незакоммиченные изменения!"
        echo "Хотите продолжить? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log_info "Деплой отменен"
            exit 0
        fi
    fi
    
    # Коммитим изменения если есть
    if ! git diff-index --quiet HEAD --; then
        log_info "Коммитим изменения..."
        git add .
        git commit -m "Auto-deploy: $(date '+%Y-%m-%d %H:%M:%S')"
    fi
    
    # Пушим на сервер
    log_info "Пушим изменения на сервер..."
    if git push prod main; then
        log_success "Деплой завершен успешно!"
        log_info "Сервер автоматически перезапустит измененные стратегии"
    else
        log_error "Ошибка при деплое"
        exit 1
    fi
}

# Проверка статуса сервера
check_status() {
    local server_user="$1"
    local server_ip="$2"
    
    log_info "📊 Проверка статуса сервера $server_user@$server_ip..."
    
    ssh "$server_user@$server_ip" "sudo /opt/freqtrade/manage.sh status"
}

# Просмотр логов
view_logs() {
    local server_user="$1"
    local server_ip="$2"
    local service="${3:-}"
    
    log_info "📝 Просмотр логов сервера $server_user@$server_ip..."
    
    if [ -n "$service" ]; then
        ssh "$server_user@$server_ip" "sudo /opt/freqtrade/manage.sh logs $service"
    else
        ssh "$server_user@$server_ip" "sudo /opt/freqtrade/manage.sh logs"
    fi
}

# Основная логика
case "${1:-help}" in
    setup-ssh)
        if [ $# -ne 3 ]; then
            log_error "Использование: $0 setup-ssh SERVER_USER SERVER_IP"
            exit 1
        fi
        setup_ssh "$2" "$3"
        ;;
    add-remote)
        if [ $# -ne 3 ]; then
            log_error "Использование: $0 add-remote SERVER_USER SERVER_IP"
            exit 1
        fi
        add_remote "$2" "$3"
        ;;
    deploy)
        deploy
        ;;
    status)
        if [ $# -ne 3 ]; then
            log_error "Использование: $0 status SERVER_USER SERVER_IP"
            exit 1
        fi
        check_status "$2" "$3"
        ;;
    logs)
        if [ $# -lt 3 ] || [ $# -gt 4 ]; then
            log_error "Использование: $0 logs SERVER_USER SERVER_IP [SERVICE]"
            exit 1
        fi
        view_logs "$2" "$3" "${4:-}"
        ;;
    help|*)
        show_help
        ;;
esac
