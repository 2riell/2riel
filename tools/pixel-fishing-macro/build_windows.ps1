$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
function Check-Exit { if ($LASTEXITCODE -ne 0) { throw "Command failed: exit $LASTEXITCODE" } }
py -3.12 -m venv .build-venv
Check-Exit
$python = Join-Path $PSScriptRoot '.build-venv\Scripts\python.exe'
& $python -m pip install -r requirements.txt pyinstaller==6.16.0
Check-Exit
& $python -m unittest discover -v
Check-Exit
& $python -m PyInstaller --noconfirm --clean --onefile --windowed --name FishingLab --collect-submodules mss.windows --hidden-import pynput.keyboard._win32 --hidden-import pynput.mouse._win32 app.py
Check-Exit
$exe = Join-Path $PSScriptRoot 'dist\FishingLab.exe'
$process = Start-Process -FilePath $exe -ArgumentList '--smoke-test' -PassThru
if (-not $process.WaitForExit(60000)) {
    $process.Kill()
    throw 'Packaged app startup test timed out'
}
if ($process.ExitCode -ne 0) { throw "Packaged app startup failed: $($process.ExitCode)" }
Copy-Item README.md dist\README.md -Force
Get-FileHash $exe -Algorithm SHA256 | Format-List | Out-File dist\SHA256.txt
Write-Host "Ready: $exe"
