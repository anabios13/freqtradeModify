# Скрипт для запуска автоматически сгенерированной системы FreqTrade на Windows

param(
    [string]$ComposeFile = "docker-compose-auto.yml"
)

Write-Host "🚀 Запуск системы FreqTrade..." -ForegroundColor Green
Write-Host "📁 Используется файл: $ComposeFile" -ForegroundColor Cyan

# Проверяем существование файла
if (-not (Test-Path $ComposeFile)) {
    Write-Host "❌ Файл $ComposeFile не найден!" -ForegroundColor Red
    Write-Host "Запустите сначала: python scripts/generate_docker_compose.py" -ForegroundColor Yellow
    exit 1
}

# Останавливаем существующие сервисы
Write-Host "🛑 Остановка существующих сервисов..." -ForegroundColor Yellow
docker-compose -f $ComposeFile down

# Запускаем новые сервисы
Write-Host "▶️  Запуск сервисов..." -ForegroundColor Green
docker-compose -f $ComposeFile up -d

# Показываем статус
Write-Host "📊 Статус сервисов:" -ForegroundColor Cyan
docker-compose -f $ComposeFile ps

Write-Host ""
Write-Host "🌐 Streamlit дашборд доступен по адресу: http://localhost:8501" -ForegroundColor Green
Write-Host "📝 Логи data-aggregator: docker-compose -f $ComposeFile logs data-aggregator" -ForegroundColor Cyan
Write-Host "🔄 Перезапуск: docker-compose -f $ComposeFile restart" -ForegroundColor Cyan
Write-Host "⏹️  Остановка: docker-compose -f $ComposeFile down" -ForegroundColor Cyan

Write-Host ""
Write-Host "💡 Полезные команды:" -ForegroundColor Yellow
Write-Host "   Просмотр логов: docker-compose -f $ComposeFile logs -f" -ForegroundColor White
Write-Host "   Перезапуск стратегии: docker-compose -f $ComposeFile restart <service_name>" -ForegroundColor White
Write-Host "   Мониторинг ресурсов: docker stats" -ForegroundColor White
