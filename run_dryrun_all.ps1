# Папки с конфигами и для PID-файлов
$cfgDir = "user_data/dryrun_configs"
$pidDir = "user_data/dryrun_logs"

# Убедимся, что папка для PID-файлов существует
if (-not (Test-Path $pidDir)) {
    New-Item -Path $pidDir -ItemType Directory | Out-Null
}

# Находим все файлы config_*.json и запускаем для каждого Freqtrade
Get-ChildItem -Path $cfgDir -Filter "config_*.json" | ForEach-Object {
    $cfgFile = $_.FullName
    # Имя стратегии — это имя файла без префикса 'config_' и суффикса '.json'
    $strategy = $_.BaseName -replace '^config_', ''

    Write-Host "Запуск стратегии '$strategy'..."

    $proc = Start-Process -FilePath "freqtrade" `
        -ArgumentList "trade --config `"$cfgFile`"" `
        -WorkingDirectory (Get-Location) `
        -PassThru

    # Сохраняем PID в отдельный файл
    $pidFile = Join-Path $pidDir ("{0}.pid" -f $strategy)
    $proc.Id | Out-File -FilePath $pidFile -Encoding ascii

    Start-Sleep -Seconds 1
}

Write-Host "✅ Все стратегии запущены."
