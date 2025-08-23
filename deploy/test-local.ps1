# FreqTrade Local Testing Script для Windows
# Требует Docker Desktop для Windows

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

# Цвета для вывода
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Blue"
$White = "White"

# Функции логирования
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Red
}

function Show-Help {
    Write-Host "FreqTrade Local Testing Script для Windows" -ForegroundColor $White
    Write-Host ""
    Write-Host "Использование: .\test-local.ps1 [КОМАНДА]" -ForegroundColor $White
    Write-Host ""
    Write-Host "Команды:" -ForegroundColor $White
    Write-Host "  start                    - Запустить все сервисы для тестирования" -ForegroundColor $White
    Write-Host "  stop                     - Остановить все сервисы" -ForegroundColor $White
    Write-Host "  restart                  - Перезапустить все сервисы" -ForegroundColor $White
    Write-Host "  status                   - Показать статус всех сервисов" -ForegroundColor $White
    Write-Host "  logs [SERVICE]           - Показать логи всех сервисов или конкретного" -ForegroundColor $White
    Write-Host "  test-strategy SERVICE    - Перезапустить конкретную стратегию (тест изоляции)" -ForegroundColor $White
    Write-Host "  cleanup                  - Очистить все данные и тома" -ForegroundColor $White
    Write-Host "  help                     - Показать эту справку" -ForegroundColor $White
    Write-Host ""
    Write-Host "Services:" -ForegroundColor $White
    Write-Host "  ft-bandtastic            - Стратегия Bandtastic" -ForegroundColor $White
    Write-Host "  ft-rsi                   - Стратегия RSI" -ForegroundColor $White
    Write-Host "  ft-strategy001           - Стратегия 001" -ForegroundColor $White
    Write-Host "  ft-bandtastic-freqai     - FreqAI Bandtastic" -ForegroundColor $White
    Write-Host "  ft-highfreq-ai           - FreqAI High Frequency" -ForegroundColor $White
    Write-Host "  ft-freqai-example        - FreqAI Example" -ForegroundColor $White
    Write-Host "  streamlit                - Streamlit дашборд" -ForegroundColor $White
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor $White
    Write-Host "  .\test-local.ps1 start                 # Запустить все" -ForegroundColor $White
    Write-Host "  .\test-local.ps1 test-strategy ft-rsi  # Перезапустить только RSI стратегию" -ForegroundColor $White
    Write-Host "  .\test-local.ps1 logs ft-bandtastic    # Логи Bandtastic" -ForegroundColor $White
}

# Проверяем, что мы в корне проекта
function Test-ProjectRoot {
    if (-not (Test-Path "docker-compose-local-test.yml")) {
        Write-Error "Этот скрипт должен быть запущен в корне проекта FreqTrade"
        Write-Info "Перейдите в папку с docker-compose-local-test.yml"
        exit 1
    }
}

# Проверяем Docker
function Test-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "Docker не установлен"
        Write-Info "Установите Docker Desktop: https://www.docker.com/products/docker-desktop/"
        exit 1
    }

    try {
        docker info | Out-Null
    } catch {
        Write-Error "Docker не запущен или нет прав"
        Write-Info "Запустите Docker Desktop и убедитесь, что у вас есть права на его использование"
        exit 1
    }

    if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
        Write-Error "Docker Compose не установлен"
        Write-Info "Установите Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    }
}

# Создаем необходимые директории
function New-Directories {
    Write-Info "📁 Создаем необходимые директории..."
    
    New-Item -ItemType Directory -Force -Path "user_data\configs" | Out-Null
    New-Item -ItemType Directory -Force -Path "user_data\strategies" | Out-Null
    New-Item -ItemType Directory -Force -Path "user_data\logs" | Out-Null
    New-Item -ItemType Directory -Force -Path "user_data\databases" | Out-Null
    New-Item -ItemType Directory -Force -Path "user_data\models" | Out-Null
    New-Item -ItemType Directory -Force -Path "user_data\freqaimodels" | Out-Null
    
    # Копируем конфиги если их нет
    if (-not (Test-Path "user_data\configs\config_bandtastic.json")) {
        Write-Info "📋 Копируем конфиги стратегий..."
        Copy-Item "deploy\configs\*.json" "user_data\configs\" -Force
        Write-Success "Конфиги скопированы"
    }
    
    Write-Success "Директории созданы"
}

# Запуск всех сервисов
function Start-Services {
    Write-Info "🚀 Запускаем все сервисы для тестирования..."
    
    New-Directories
    
    # Запускаем с локальным docker-compose
    docker-compose -f docker-compose-local-test.yml up -d
    
    Write-Success "Все сервисы запущены!"
    Write-Info "🌐 Streamlit дашборд: http://localhost:8501"
    Write-Info "📊 Проверить статус: .\test-local.ps1 status"
    Write-Info "📝 Просмотр логов: .\test-local.ps1 logs"
}

# Остановка всех сервисов
function Stop-Services {
    Write-Info "🛑 Останавливаем все сервисы..."
    
    docker-compose -f docker-compose-local-test.yml down
    
    Write-Success "Все сервисы остановлены"
}

# Перезапуск всех сервисов
function Restart-Services {
    Write-Info "🔄 Перезапускаем все сервисы..."
    
    docker-compose -f docker-compose-local-test.yml restart
    
    Write-Success "Все сервисы перезапущены"
}

# Показать статус
function Show-Status {
    Write-Info "📊 Статус сервисов:"
    
    docker-compose -f docker-compose-local-test.yml ps
}

# Показать логи
function Show-Logs {
    param([string]$Service = "")
    
    if ($Service) {
        Write-Info "📝 Логи сервиса $Service:"
        docker-compose -f docker-compose-local-test.yml logs -f $Service
    } else {
        Write-Info "📝 Логи всех сервисов:"
        docker-compose -f docker-compose-local-test.yml logs -f
    }
}

# Тест изоляции стратегий
function Test-StrategyIsolation {
    param([string]$Service)
    
    if (-not $Service) {
        Write-Error "Укажите сервис для тестирования"
        Write-Info "Пример: .\test-local.ps1 test-strategy ft-rsi"
        exit 1
    }
    
    Write-Info "🧪 Тестируем изоляцию стратегии: $Service"
    Write-Info "Перезапускаем только $Service, остальные должны продолжать работать..."
    
    # Останавливаем только указанный сервис
    docker-compose -f docker-compose-local-test.yml stop $Service
    
    Write-Info "⏸️  $Service остановлен. Проверяем, что остальные работают..."
    Start-Sleep -Seconds 3
    
    # Показываем статус
    docker-compose -f docker-compose-local-test.yml ps
    
    Write-Info "🔄 Запускаем $Service заново..."
    docker-compose -f docker-compose-local-test.yml up -d $Service
    
    Write-Success "Тест изоляции завершен!"
    Write-Info "Проверьте, что $Service перезапустился, а остальные продолжают работать"
}

# Очистка данных
function Clear-Data {
    Write-Warning "🗑️  Очищаем все данные и тома..."
    Write-Warning "Это действие НЕОБРАТИМО! Все данные будут удалены!"
    
    $response = Read-Host "Вы уверены? (y/N)"
    if ($response -notmatch "^[Yy]$") {
        Write-Info "Очистка отменена"
        exit 0
    }
    
    Write-Info "Останавливаем сервисы..."
    docker-compose -f docker-compose-local-test.yml down
    
    Write-Info "Удаляем тома..."
    docker volume ls -q | Where-Object { $_ -match "_local$" } | ForEach-Object { docker volume rm $_ } 2>$null
    
    Write-Info "Удаляем локальные данные..."
    Remove-Item "user_data\logs\*" -Force -Recurse -ErrorAction SilentlyContinue
    Remove-Item "user_data\databases\*" -Force -Recurse -ErrorAction SilentlyContinue
    Remove-Item "user_data\models\*" -Force -Recurse -ErrorAction SilentlyContinue
    Remove-Item "user_data\freqaimodels\*" -Force -Recurse -ErrorAction SilentlyContinue
    
    Write-Success "Очистка завершена"
}

# Основная логика
function Main {
    Test-ProjectRoot
    Test-Docker
    
    switch ($Command.ToLower()) {
        "start" {
            Start-Services
        }
        "stop" {
            Stop-Services
        }
        "restart" {
            Restart-Services
        }
        "status" {
            Show-Status
        }
        "logs" {
            Show-Logs $args[1]
        }
        "test-strategy" {
            Test-StrategyIsolation $args[1]
        }
        "cleanup" {
            Clear-Data
        }
        "help" {
            Show-Help
        }
        default {
            Write-Error "Неизвестная команда: $Command"
            Show-Help
            exit 1
        }
    }
}

# Запуск
Main
