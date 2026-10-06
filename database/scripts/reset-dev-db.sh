#!/usr/bin/env bash
# Drop and recreate all domain tables, apply migrations in order, load seed data.
# DEV/TEST ONLY. Requires the database and roles from database/schema/000_roles_and_database.sql.
#
# Env: POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_OWNER_USER, POSTGRES_OWNER_PASSWORD
set -euo pipefail

cd "$(dirname "$0")/.."

export PGHOST="${POSTGRES_HOST:-localhost}"
export PGPORT="${POSTGRES_PORT:-5432}"
export PGDATABASE="${POSTGRES_DB:-mortgage_intel}"
export PGUSER="${POSTGRES_OWNER_USER:-mortgage_owner}"
export PGPASSWORD="${POSTGRES_OWNER_PASSWORD:?Set POSTGRES_OWNER_PASSWORD}"

case "$PGHOST" in
  localhost|127.0.0.1|postgres) ;;
  *) echo "Refusing to reset non-local host '$PGHOST'" >&2; exit 1 ;;
esac

PSQL=(psql -v ON_ERROR_STOP=1 -q)

echo "Dropping domain tables in $PGDATABASE@$PGHOST:$PGPORT ..."
"${PSQL[@]}" -c "DROP TABLE IF EXISTS document, delinquency, servicing_history, payment, loan, mortgage, borrower CASCADE;"

for f in migrations/*.sql; do
  echo "Applying $f"
  "${PSQL[@]}" -f "$f"
done

echo "Loading seed/seed_mortgage_data.sql"
"${PSQL[@]}" -f seed/seed_mortgage_data.sql

"${PSQL[@]}" -c "SELECT 'borrower' t, COUNT(*) FROM borrower UNION ALL SELECT 'mortgage', COUNT(*) FROM mortgage UNION ALL SELECT 'loan', COUNT(*) FROM loan UNION ALL SELECT 'payment', COUNT(*) FROM payment UNION ALL SELECT 'servicing_history', COUNT(*) FROM servicing_history UNION ALL SELECT 'delinquency', COUNT(*) FROM delinquency UNION ALL SELECT 'document', COUNT(*) FROM document;"
echo "Done."
