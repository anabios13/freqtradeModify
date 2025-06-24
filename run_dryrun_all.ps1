$strategies = @(
    "Bandtastic","RsiStrategy","ScalpingStrategy",
    "Strategy001","Strategy002","Strategy003",
    "Strategy004","Strategy005"
)
$cfgDir = "user_data/dryrun_configs"
$pidDir = "user_data/dryrun_logs"

foreach ($s in $strategies) {
    Write-Host "Запуск $s..."
    $cfg = "$cfgDir\config_$s.json"
    # запускаем freqtrade (он сам пишет в logfile)
    $proc = Start-Process -FilePath "freqtrade" `
        -ArgumentList "trade --config `"$cfg`"" `
        -WorkingDirectory (Get-Location) `
        -PassThru

    # сохраняем его PID
    $proc.Id > "$pidDir\$s.pid"
    Start-Sleep -Seconds 1
}

Write-Host "✅ Все стратегии запущены."
