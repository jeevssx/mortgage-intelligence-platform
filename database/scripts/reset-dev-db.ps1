# Drop and recreate all domain tables, apply migrations in order, load seed data.
# DEV/TEST ONLY. Requires the database and roles from database/schema/000_roles_and_database.sql.
#
# Env: POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_OWNER_USER, POSTGRES_OWNER_PASSWORD
$ErrorActionPreference = 'Stop'

$dbRoot = Split-Path -Parent $PSScriptRoot

$env:PGHOST     = if ($env:POSTGRES_HOST) { $env:POSTGRES_HOST } else { 'localhost' }
$env:PGPORT     = if ($env:POSTGRES_PORT) { $env:POSTGRES_PORT } else { '5432' }
$env:PGDATABASE = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { 'mortgage_intel' }
$env:PGUSER     = if ($env:POSTGRES_OWNER_USER) { $env:POSTGRES_OWNER_USER } else { 'mortgage_owner' }
if (-not $env:POSTGRES_OWNER_PASSWORD) { throw 'Set POSTGRES_OWNER_PASSWORD' }
$env:PGPASSWORD = $env:POSTGRES_OWNER_PASSWORD

if ($env:PGHOST -notin @('localhost', '127.0.0.1', 'postgres')) {
    throw "Refusing to reset non-local host '$($env:PGHOST)'"
}

function Invoke-Psql([string[]]$PsqlArgs) {
    & psql -v ON_ERROR_STOP=1 -q @PsqlArgs
    if ($LASTEXITCODE -ne 0) { throw "psql failed: $PsqlArgs" }
}

Write-Host "Dropping domain tables in $($env:PGDATABASE)@$($env:PGHOST):$($env:PGPORT) ..."
Invoke-Psql @('-c', 'DROP TABLE IF EXISTS document, delinquency, servicing_history, payment, loan, mortgage, borrower CASCADE;')

Get-ChildItem (Join-Path $dbRoot 'migrations') -Filter '*.sql' | Sort-Object Name | ForEach-Object {
    Write-Host "Applying $($_.Name)"
    Invoke-Psql @('-f', $_.FullName)
}

Write-Host 'Loading seed_mortgage_data.sql'
Invoke-Psql @('-f', (Join-Path $dbRoot 'seed\seed_mortgage_data.sql'))

Invoke-Psql @('-c', "SELECT 'borrower' t, COUNT(*) FROM borrower UNION ALL SELECT 'mortgage', COUNT(*) FROM mortgage UNION ALL SELECT 'payment', COUNT(*) FROM payment UNION ALL SELECT 'delinquency', COUNT(*) FROM delinquency;")
Write-Host 'Done.'
