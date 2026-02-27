#!/bin/bash
set -e

echo "🔧 Running entrypoint..."

# Wait for database to be ready
echo "⏳ Waiting for database..."
python << 'EOF'
import os, time, sys
import psycopg2

db_url = os.environ.get("DATABASE_URL", "")
max_retries = 30
retry = 0
while retry < max_retries:
    try:
        conn = psycopg2.connect(db_url)
        conn.close()
        print("✅ Database is ready!")
        sys.exit(0)
    except psycopg2.OperationalError:
        retry += 1
        print(f"   Database not ready, retrying ({retry}/{max_retries})...")
        time.sleep(2)

print("❌ Could not connect to database")
sys.exit(1)
EOF

# Run migrations
echo "📦 Running migrations..."
python manage.py migrate --noinput

# Execute the main command (CMD from Dockerfile or docker-compose)
echo "🚀 Starting: $@"
exec "$@"
