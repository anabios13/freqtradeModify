#!/bin/bash
# Скрипт для запуска автоматически сгенерированной системы FreqTrade

COMPOSE_FILE="docker-compose-auto.yml"

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
