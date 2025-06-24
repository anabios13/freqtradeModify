# check_processes.ps1
Get-ChildItem "user_data/dryrun_logs" -Filter "*.pid" | ForEach-Object {
    $strategy = $_.BaseName
    $procId   = Get-Content $_.FullName
    $proc     = Get-Process -Id $procId -ErrorAction SilentlyContinue

    if ($proc) {
        Write-Host "✅ $strategy alive (PID $procId)"
    }
    else {
        Write-Warning "❌ $strategy not alive (PID $procId not found)"
    }
}
