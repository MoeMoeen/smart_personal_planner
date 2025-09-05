#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Starting Smart Planner Dev Server with ngrok + Telegram webhook..."

# --- Config ---
UPDATE_ENV=false
for arg in "$@"; do  # Parse command-line arguments- example: --update-env
  if [ "$arg" == "--update-env" ]; then
    UPDATE_ENV=true
  fi
done

# --- 1. Kill any previous ngrok ---
pkill -f ngrok || true

# --- 2. Start ngrok in background ---
ngrok http 8000 > /tmp/ngrok.log &
sleep 2

# --- 3. Extract fresh ngrok URL ---
NGROK_URL=$(curl --silent http://127.0.0.1:4040/api/tunnels \
    | jq -r '.tunnels[0].public_url')

if [ -z "$NGROK_URL" ]; then
  echo "❌ Could not get ngrok URL"
  exit 1
fi

WEBHOOK_URL="$NGROK_URL/telegram/webhook"

# --- 4. Reset Telegram webhook ---
echo "🧹 Deleting old Telegram webhook..."
curl -s -X POST https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/deleteWebhook | jq

echo "🔗 Setting Telegram webhook to $WEBHOOK_URL"
curl -s -X POST https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook \
    -d "url=$WEBHOOK_URL" | jq

# --- 5. Export to runtime env ---
export TELEGRAM_WEBHOOK_URL="$WEBHOOK_URL"
export TELEGRAM_MODE=webhook

# --- 6. Optional: Update .env file ---
if $UPDATE_ENV; then
  if grep -q "^TELEGRAM_WEBHOOK_URL=" .env; then
    sed -i.bak "s|^TELEGRAM_WEBHOOK_URL=.*|TELEGRAM_WEBHOOK_URL=$WEBHOOK_URL|" .env
  else
    echo "TELEGRAM_WEBHOOK_URL=$WEBHOOK_URL" >> .env
  fi
  echo "📝 Updated .env with TELEGRAM_WEBHOOK_URL=$WEBHOOK_URL"
fi

# --- 7. Run FastAPI ---
echo "⚡ Starting FastAPI server..."
uvicorn app.main:app --reload --port 8000