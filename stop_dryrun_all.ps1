# stop_dryrun_all.ps1

# Собираем все .pid-файлы
$pidFiles = Get-ChildItem -Path "user_data\dryrun_logs" -Filter "*.pid" -ErrorAction SilentlyContinue
if (-not $pidFiles) {
    Write-Host "No PID files found, nothing to stop."
    exit
}

foreach ($file in $pidFiles) {
    $name = $file.BaseName
    try {
        # 1) Прочитать строку и обрезать пробелы
        $text = Get-Content -Path $file.FullName -ErrorAction Stop
        $value = $text.Trim()

        # 2) Попробовать распарсить в int через out-параметр parsedPid
        [int]$parsedPid = 0
        if (-not [int]::TryParse($value, [ref]$parsedPid)) {
            throw "Invalid PID file content: '$value'"
        }

        # 3) Если процесс существует — остановить
        $proc = Get-Process -Id $parsedPid -ErrorAction SilentlyContinue
        if ($proc) {
            Stop-Process -Id $parsedPid -Force -ErrorAction Stop
            Write-Host "Process '$name' (PID $parsedPid) stopped."
        }
        else {
            Write-Warning "Process '$name' (PID $parsedPid) not running."
        }
    }
    catch {
        Write-Warning "Failed to stop '$name': $_"
    }
    finally {
        # 4) Всегда убрать .pid-файл
        Remove-Item -Path $file.FullName -Force -ErrorAction SilentlyContinue
    }
}
