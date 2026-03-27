$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $BackendDir

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if (-not $env:DATABASE_URL) {
  $env:DATABASE_URL = "mysql+pymysql://root:root@127.0.0.1:3306/exam_recognition?charset=utf8mb4"
}

if (-not $env:LIBREOFFICE_CMD) {
  $env:LIBREOFFICE_CMD = "soffice"
}

python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
