# OpenRouter Price Alert Bot

Monitor OpenRouter model pricing and get alerts in Discord when something changes.

## Features

- **New models** - Alerts when new models are added
- **Free models** - Lists all free models with context length
- **Price drops** - Notifies when model prices decrease

## Setup

1. **Create Discord webhook:**
   - Server Settings → Integrations → Webhooks
   - Create new webhook, copy URL

2. **Add secret to GitHub:**
   - Repository Settings → Secrets and variables → Actions
   - Add `DISCORD_WEBHOOK` with your webhook URL

## Running Locally

```bash
pip install -r requirements.txt
export DISCORD_WEBHOOK="your_webhook_url"
python main.py
```

## Automated Runs

The bot runs daily at 9:00 AM UTC via GitHub Actions. You can also trigger it manually from the Actions tab.

## What It Does

1. Fetches all models from OpenRouter API
2. Compares with previous snapshot
3. Sends Discord alert if:
   - New models added
   - Models went free
   - Prices dropped
4. Posts list of current free models
5. Saves new snapshot for next run
