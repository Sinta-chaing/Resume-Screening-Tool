# Install pgvector for PostgreSQL 18 on Windows
# RUN AS ADMINISTRATOR (right-click PowerShell -> Run as administrator)
#
# Usage:
#   cd backend\scripts
#   .\install_pgvector.ps1

$ErrorActionPreference = "Stop"

$PgRoot = "C:\Program Files\PostgreSQL\18"
$ZipUrl = "https://github.com/andreiramani/pgvector_pgsql_windows/releases/download/0.8.6_18/vector.v0.8.6-pg18.zip"
$TempDir = Join-Path $env:TEMP "pgvector-pg18-install"
$ZipPath = Join-Path $env:TEMP "vector.v0.8.6-pg18.zip"

if (-not (Test-Path "$PgRoot\bin\psql.exe")) {
    Write-Error "PostgreSQL 18 not found at $PgRoot. Edit `$PgRoot in this script if installed elsewhere."
}

Write-Host "Downloading pgvector v0.8.6 for PostgreSQL 18..."
curl.exe -L -o $ZipPath $ZipUrl

if (Test-Path $TempDir) { Remove-Item -Recurse -Force $TempDir }
Expand-Archive -Path $ZipPath -DestinationPath $TempDir -Force

Write-Host "Stopping PostgreSQL service..."
Stop-Service -Name "postgresql-x64-18" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host "Installing pgvector files to $PgRoot ..."
Copy-Item "$TempDir\lib\vector.dll" "$PgRoot\lib\" -Force
Copy-Item "$TempDir\share\extension\*" "$PgRoot\share\extension\" -Force
New-Item -ItemType Directory -Force -Path "$PgRoot\include\server\extension\vector" | Out-Null
Copy-Item "$TempDir\include\server\extension\vector\*" "$PgRoot\include\server\extension\vector\" -Force

Write-Host "Starting PostgreSQL service..."
Start-Service -Name "postgresql-x64-18"

Write-Host ""
Write-Host "pgvector files installed successfully." -ForegroundColor Green
Write-Host ""
Write-Host "Next steps (run in your backend folder):"
Write-Host "  1. Ensure backend/.env has your DB credentials"
Write-Host "  2. python manage.py migrate"
Write-Host ""
Write-Host "Optional - enable extension manually in psql:"
Write-Host "  `"$PgRoot\bin\psql.exe`" -U postgres -d resume_screener -c `"CREATE EXTENSION IF NOT EXISTS vector;`""
