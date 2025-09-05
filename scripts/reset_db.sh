#!/usr/bin/env bash
set -euo pipefail

# =========================
# Smart Planner DB Reset
# =========================

# 1. Load environment variables
if [ -f .env ]; then
  # Strip out comments and export
  export $(grep -v '^#' .env | xargs)
fi

if [ -z "${DATABASE_URL:-}" ]; then
  echo "❌ DATABASE_URL not set in environment or .env"
  exit 1
fi

echo "⚠️ WARNING: This will DROP and recreate the database schema."
read -p "Are you sure? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
  echo "❌ Aborted."
  exit 1
fi

DB_NAME="smartplanner_db"
DB_USER="smartplanner_user"
ALEMBIC_INI="/home/moemoeen/Documents/GitHub/Python_Projects_Personal/smart_personal_planner/alembic.ini"

# 2. Drop + recreate public schema
echo "⚠️ Dropping and recreating schema 'public'..."
psql "$DATABASE_URL" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# 3. Reset Alembic versioning
echo "⚠️ Resetting Alembic version table..."
alembic -c "$ALEMBIC_INI" downgrade base

# 4. Clean up leftover enums
echo "⚠️ Dropping leftover enums if they exist..."
psql "$DATABASE_URL" <<'SQL'
DO $$
DECLARE r RECORD;
BEGIN
  FOR r IN (SELECT typname FROM pg_type WHERE typcategory = 'E') LOOP
    EXECUTE format('DROP TYPE IF EXISTS %I CASCADE;', r.typname);
  END LOOP;
END$$;
SQL

# 5. Apply all migrations from scratch
echo "🚀 Applying migrations..."
alembic -c "$ALEMBIC_INI" upgrade head

echo "✅ Database reset complete!"