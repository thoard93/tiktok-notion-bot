# TikTok Shop Notion Automation Bot

Telegram bot that automates daily video lineup creation for TikTok Shop UGC content.

## Features

- 📸 Send earnings screenshots from TikTok Shop
- 🤖 AI-powered OCR extracts product sales data
- 📦 Matches products to Chelsea's inventory
- 🆕 Prioritizes New Sample products for testing
- 📋 Generates 60 daily videos (20 per account)
- ✅ Creates entries directly in Notion

## Video Distribution Logic

- **Gymgoer1993**: Gets ALL new samples + top sellers (priority account)
- **Dealrush93**: Gets overflow new samples + offset sellers
- **Datburgershop93**: Gets remaining overflow + variety sellers

Each account gets 20 videos:
- 6 products × 3 videos (2 Sound Method + 1 MOF)
- 1 product × 2 videos (1 Sound Method + 1 MOF)

## Setup

### 1. Create GitHub Repository

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/tiktok-notion-bot.git
git push -u origin main
```

### 2. Deploy to Render

1. Go to [render.com](https://render.com) and connect your GitHub
2. Create a new **Background Worker** (not Web Service)
3. Connect your repository
4. Set environment variables:
   - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
   - `TELEGRAM_CHAT_ID`: Your Telegram chat ID
   - `ANTHROPIC_API_KEY`: Your Anthropic API key
   - `NOTION_API_KEY`: Your Notion integration token

### 3. Get Notion API Key

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Create a new integration
3. Copy the "Internal Integration Token"
4. Share your TikTok Shop UGC VIDEO Tracker database with the integration

## Usage

1. Send earnings screenshots to the Telegram bot
2. Use `/generate` when all screenshots are sent
3. Review the proposed lineup
4. Reply `confirm` to create in Notion or `cancel` to abort

## Commands

- `/start` - Show help
- `/generate` - Process screenshots and generate lineup
- `/clear` - Clear current screenshots
- `/status` - Check how many screenshots collected

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Your Telegram user ID |
| `ANTHROPIC_API_KEY` | Claude API key |
| `NOTION_API_KEY` | Notion integration token |
