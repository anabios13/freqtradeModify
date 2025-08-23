# FreqTrade Local Setup Script для Windows PowerShell
# Требует Git Bash или WSL для работы с SSH

param(
    [Parameter(Position=0)]
    [string]$Command = "help",
    
    [Parameter(Position=1)]
    [string]$ServerUser = "",
    
    [Parameter(Position=2)]
    [string]$ServerIP = ""
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
    Write-Host "FreqTrade Local Setup Script для Windows" -ForegroundColor $White
    Write-Host ""
    Write-Host "Использование: .\setup-local.ps1 [КОМАНДА] [ПАРАМЕТРЫ]" -ForegroundColor $White
    Write-Host ""
    Write-Host "Команды:" -ForegroundColor $White
    Write-Host "  setup-ssh SERVER_USER SERVER_IP    - Настроить SSH подключение" -ForegroundColor $White
    Write-Host "  add-remote SERVER_USER SERVER_IP   - Добавить удаленный репозиторий" -ForegroundColor $White
    Write-Host "  deploy                              - Деплой на сервер" -ForegroundColor $White
    Write-Host "  status SERVER_USER SERVER_IP        - Проверить статус сервера" -ForegroundColor $White
    Write-Host "  logs SERVER_USER SERVER_IP SERVICE  - Просмотр логов" -ForegroundColor $White
    Write-Host "  help                                - Показать эту справку" -ForegroundColor $White
    Write-Host ""
    Write-Host "Примеры:" -ForegroundColor $White
    Write-Host "  .\setup-local.ps1 setup-ssh freqtrader 192.168.1.100" -ForegroundColor $White
    Write-Host "  .\setup-local.ps1 add-remote freqtrader 192.168.1.100" -ForegroundColor $White
    Write-Host "  .\setup-local.ps1 deploy" -ForegroundColor $White
    Write-Host "  .\setup-local.ps1 status freqtrader 192.168.1.100" -ForegroundColor $White
    Write-Host ""
    Write-Host "Примечание: Требуется Git Bash или WSL для работы с SSH" -ForegroundColor $Yellow
}

# Проверяем, что мы в Git репозитории
function Test-GitRepo {
    if (-not (Test-Path ".git")) {
        Write-Error "Этот скрипт должен быть запущен в Git репозитории"
        exit 1
    }
}

# Проверяем наличие Git Bash
function Test-GitBash {
    $gitBashPath = "C:\Program Files\Git\bin\bash.exe"
    if (-not (Test-Path $gitBashPath)) {
        Write-Error "Git Bash не найден. Установите Git for Windows: https://git-scm.com/download/win"
        exit 1
    }
    return $gitBashPath
}

# Настройка SSH подключения
function Setup-SSH {
    param([string]$ServerUser, [string]$ServerIP)
    
    Write-Info "🔑 Настройка SSH подключения к $ServerUser@$ServerIP..."
    
    $gitBash = Test-GitBash
    
    # Проверяем существование SSH ключа
    $sshKeyPath = "$env:USERPROFILE\.ssh\id_ed25519"
    if (-not (Test-Path $sshKeyPath)) {
        Write-Info "Создаем новый SSH ключ..."
        & $gitBash -c "ssh-keygen -t ed25519 -C 'freqtrade-prod' -f ~/.ssh/id_ed25519 -N ''"
        if ($LASTEXITCODE -eq 0) {
            Write-Success "SSH ключ создан"
        } else {
            Write-Error "Ошибка при создании SSH ключа"
            exit 1
        }
    } else {
        Write-Info "SSH ключ уже существует"
    }
    
    # Копируем публичный ключ на сервер
    Write-Info "Копируем публичный ключ на сервер..."
    & $gitBash -c "ssh-copy-id -i ~/.ssh/id_ed25519.pub $ServerUser@$ServerIP"
    if ($LASTEXITCODE -eq 0) {
        Write-Success "SSH ключ скопирован на сервер"
    } else {
        Write-Error "Ошибка при копировании SSH ключа"
        exit 1
    }
    
    # Тестируем подключение
    Write-Info "Тестируем SSH подключение..."
    $testResult = & $gitBash -c "ssh -o ConnectTimeout=10 $ServerUser@$ServerIP 'echo SSH подключение работает!'"
    if ($LASTEXITCODE -eq 0) {
        Write-Success "SSH подключение настроено успешно!"
    } else {
        Write-Error "Не удалось установить SSH подключение"
        exit 1
    }
}

# Добавление удаленного репозитория
function Add-Remote {
    param([string]$ServerUser, [string]$ServerIP)
    
    Test-GitRepo
    $gitBash = Test-GitBash
    
    Write-Info "🔗 Добавляем удаленный репозиторий..."
    
    # Удаляем существующий remote если есть
    $remoteExists = git remote get-url prod 2>$null
    if ($remoteExists) {
        Write-Info "Удаляем существующий remote 'prod'..."
        git remote remove prod
    }
    
    # Добавляем новый remote
    $remoteUrl = "$ServerUser@$ServerIP:/opt/freqtrade/deploy.git"
    git remote add prod $remoteUrl
    
    Write-Success "Удаленный репозиторий добавлен: $remoteUrl"
    
    # Тестируем подключение
    Write-Info "Тестируем подключение к удаленному репозиторию..."
    $testResult = & $gitBash -c "git ls-remote prod"
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Подключение к удаленному репозиторию работает!"
    } else {
        Write-Error "Не удалось подключиться к удаленному репозиторию"
        exit 1
    }
}

# Деплой на сервер
function Deploy {
    Test-GitRepo
    $gitBash = Test-GitBash
    
    Write-Info "🚀 Деплой на сервер..."
    
    # Проверяем, что есть remote prod
    $remoteExists = git remote get-url prod 2>$null
    if (-not $remoteExists) {
        Write-Error "Remote 'prod' не настроен. Сначала выполните: .\setup-local.ps1 add-remote USER IP"
        exit 1
    }
    
    # Проверяем статус Git
    $gitStatus = git status --porcelain
    if ($gitStatus) {
        Write-Warning "У вас есть незакоммиченные изменения!"
        $response = Read-Host "Хотите продолжить? (y/N)"
        if ($response -notmatch "^[Yy]$") {
            Write-Info "Деплой отменен"
            exit 0
        }
    }
    
    # Коммитим изменения если есть
    if ($gitStatus) {
        Write-Info "Коммитим изменения..."
        git add .
        git commit -m "Auto-deploy: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    }
    
    # Пушим на сервер
    Write-Info "Пушим изменения на сервер..."
    if (git push prod main) {
        Write-Success "Деплой завершен успешно!"
        Write-Info "Сервер автоматически перезапустит измененные стратегии"
    } else {
        Write-Error "Ошибка при деплое"
        exit 1
    }
}

# Проверка статуса сервера
function Check-Status {
    param([string]$ServerUser, [string]$ServerIP)
    
    $gitBash = Test-GitBash
    
    Write-Info "📊 Проверка статуса сервера $ServerUser@$ServerIP..."
    
    & $gitBash -c "ssh $ServerUser@$ServerIP 'sudo /opt/freqtrade/manage.sh status'"
}

# Просмотр логов
function View-Logs {
    param([string]$ServerUser, [string]$ServerIP, [string]$Service = "")
    
    $gitBash = Test-GitBash
    
    Write-Info "📝 Просмотр логов сервера $ServerUser@$ServerIP..."
    
    if ($Service) {
        & $gitBash -c "ssh $ServerUser@$ServerIP 'sudo /opt/freqtrade/manage.sh logs $Service'"
    } else {
        & $gitBash -c "ssh $ServerUser@$ServerIP 'sudo /opt/freqtrade/manage.sh logs'"
    }
}

# Основная логика
switch ($Command.ToLower()) {
    "setup-ssh" {
        if (-not $ServerUser -or -not $ServerIP) {
            Write-Error "Использование: .\setup-local.ps1 setup-ssh SERVER_USER SERVER_IP"
            exit 1
        }
        Setup-SSH $ServerUser $ServerIP
    }
    "add-remote" {
        if (-not $ServerUser -or -not $ServerIP) {
            Write-Error "Использование: .\setup-local.ps1 add-remote SERVER_USER SERVER_IP"
            exit 1
        }
        Add-Remote $ServerUser $ServerIP
    }
    "deploy" {
        Deploy
    }
    "status" {
        if (-not $ServerUser -or -not $ServerIP) {
            Write-Error "Использование: .\setup-local.ps1 status SERVER_USER SERVER_IP"
            exit 1
        }
        Check-Status $ServerUser $ServerIP
    }
    "logs" {
        if (-not $ServerUser -or -not $ServerIP) {
            Write-Error "Использование: .\setup-local.ps1 logs SERVER_USER SERVER_IP [SERVICE]"
            exit 1
        }
        View-Logs $ServerUser $ServerIP $args[3]
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
