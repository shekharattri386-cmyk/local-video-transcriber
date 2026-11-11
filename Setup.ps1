param([switch]$CpuOnly, [switch]$DownloadModel)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
foreach ($toolName in @('ffmpeg', 'node')) {
    if (-not (Get-Command $toolName -ErrorAction SilentlyContinue)) {
        throw "$toolName is missing from PATH. See README.md prerequisites, then reopen your terminal."
    }
}
$pythonExe = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        & uv venv --python 3.12 .venv
    } else {
        & py -3.12 -m venv .venv
    }
    if ($LASTEXITCODE -ne 0) { throw 'Could not create Python 3.12 environment. Install Python 3.12 or uv.' }
}
& $pythonExe -c "import sys; assert sys.version_info[:2] == (3, 12), 'Python 3.12 is required'; import tkinter"
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 with Tkinter is required.' }
$requirementsPath = if ($CpuOnly) { 'requirements.txt' } else { 'requirements-gpu.txt' }
if (Get-Command uv -ErrorAction SilentlyContinue) {
    & uv pip install --python $pythonExe -r $requirementsPath
} else {
    & $pythonExe -m pip install -r $requirementsPath
}
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
if ($DownloadModel) {
    $deviceName = if ($CpuOnly) { 'cpu' } else { 'cuda' }
    & $pythonExe transcribe.py --prepare --device $deviceName
    if ($LASTEXITCODE -ne 0) { throw 'Model preparation failed. Check the preceding error.' }
}
Write-Host 'Setup complete. Double-click Start.cmd.'
if ($CpuOnly) { Write-Host 'Select cpu in the app before starting transcription.' }
if (-not $DownloadModel) { Write-Host 'First transcription downloads the Whisper turbo model (several GB of free disk recommended).' }
