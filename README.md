# OpenRouter Price Alert Bot

Monitor OpenRouter model pricing and get a weekly digest in Discord.

## Features

- **Weekly digest** — A Discord embed every Monday summarizing the past week's changes
- **New models** — Alerts when new models are added
- **Free models** — Lists all free models with context length
- **Price drops** — Notifies when model prices decrease

## Running Locally

```bash
pip install -r requirements.txt
export DISCORD_WEBHOOK="your_webhook_url"
python main.py           # daily mode (accumulates changes to weekly file)
python main.py --weekly  # weekly mode (sends digest embed, clears accumulated data)
```

Set `TEST_DISCORD=1` to print output to console instead of sending to Discord.

## Automated Runs

The bot runs daily at 9:00 AM UTC via GitHub Actions:
- **Mon–Sun** — Runs in daily mode, fetches models, detects changes, and accumulates them into `weekly_updates.json`
- **Monday** — Runs in weekly mode, generates and sends a Discord embed digest of the past week, then clears the accumulated data

You can also trigger it manually from the Actions tab.

## What It Does

1. Fetches all models from OpenRouter API
2. Compares with previous snapshot
3. Accumulates detected changes:
   - New models added
   - Models that went free
   - Price drops
4. On Monday: sends a Discord embed digest summarizing the week
5. Saves new snapshot for next run
