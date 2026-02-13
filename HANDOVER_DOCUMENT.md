# TikTok Notion Bot - Complete Handover Document

## Project Overview

**Project Name:** TikTok Notion Bot  
**Purpose:** Automated daily video lineup generation for TikTok Shop affiliate marketing  
**Owner:** Thomas (thoardyr)  
**Status:** Production (Deployed on Render)  
**Last Updated:** January 2026

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Deployment](#deployment)
4. [Configuration](#configuration)
5. [Features & Workflows](#features--workflows)
6. [Code Structure](#code-structure)
7. [Database Schema](#database-schema)
8. [Troubleshooting](#troubleshooting)
9. [Future Improvements](#future-improvements)

---

## System Overview

### What It Does

The TikTok Notion Bot automates the daily workflow of generating video content lineups for TikTok Shop affiliate marketing across three accounts. It:

1. **Processes earnings screenshots** from TikTok Shop
2. **Extracts product sales data** using Claude AI (OCR + smart matching)
3. **Generates optimized video lineups** based on sales performance
4. **Creates Notion database entries** for each video to be created
5. **Manages new product samples** with priority testing

### Business Context

- **3 TikTok Accounts:** Gymgoer1993, Dealrush93, Datburgershop93
- **Daily Video Output:** 35 videos total (15 + 10 + 10)
- **Product Inventory:** 200+ products tracked in Notion
- **Video Styles:** Sound Method, Crying MOF (Gymgoer), Snapchat MOF (others)

### Key Benefits

- **Saves ~2 hours daily** on manual lineup planning
- **Data-driven decisions** based on actual sales performance
- **Smart product matching** handles typos and variations
- **New sample prioritization** ensures fresh products get tested
- **Zero manual Notion data entry** - fully automated

---

## Architecture

### High-Level Components

```
┌─────────────────┐
│  User (Thomas)  │
└────────┬────────┘
         │ Screenshots
         ▼
┌─────────────────────────┐
│   Telegram Bot          │
│   (@tiktok_notion_bot)  │
└─────────┬───────────────┘
          │
          ├──► Claude API (Vision + OCR)
          │
          ├──► Notion API (Database)
          │
          └──► Anthropic Claude Sonnet 4
```

### Technology Stack

- **Language:** Python 3.13
- **Bot Framework:** python-telegram-bot
- **AI Provider:** Anthropic Claude API (Sonnet 4)
- **Database:** Notion API (Multi-select properties)
- **Hosting:** Render (Background Worker, Starter tier)
- **Version Control:** GitHub (thoardyr/tiktok-notion-bot)

### External Dependencies

| Service | Purpose | API Key Required |
|---------|---------|------------------|
| Telegram | Bot interface | `TELEGRAM_BOT_TOKEN` |
| Anthropic | AI vision/text processing | `ANTHROPIC_API_KEY` |
| Notion | Database management | `NOTION_API_KEY` |

---

## Deployment

### Current Deployment

**Platform:** Render  
**Service Type:** Background Worker  
**Instance:** Starter ($7/month, 512MB RAM, 0.5 CPU)  
**Repository:** https://github.com/thoardyr/tiktok-notion-bot  
**Branch:** `main` (auto-deploy enabled)

### Environment Variables (Render)

```bash
TELEGRAM_BOT_TOKEN=<bot_token>
NOTION_API_KEY=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
ANTHROPIC_API_KEY=<anthropic_key>
NOTION_DATABASE_ID=26d2b61d-84d1-8029-969d-d25728061db8
```

### Deployment Process

1. **Push to GitHub:** Changes to `main` branch trigger auto-deploy
2. **Render Build:** Installs dependencies from `requirements.txt`
3. **Bot Restart:** New instance starts, old instance terminates (30-60s overlap)
4. **Telegram Conflict:** Temporary "terminated by other getUpdates" errors during switchover (normal)

### Requirements File

```txt
python-telegram-bot==21.0.1
anthropic==0.21.3
httpx==0.27.0
```

---

## Configuration

### TikTok Accounts

```python
TIKTOK_ACCOUNTS = [
    "Gymgoer1993",      # 15 videos/day
    "Dealrush93",       # 10 videos/day
    "Datburgershop93"   # 10 videos/day
]
```

### Video Distribution

| Account | Products | Videos | Format |
|---------|----------|--------|--------|
| Gymgoer1993 | 5 | 15 | 5 products × 3 videos (2 Sound + 1 Crying MOF) |
| Dealrush93 | 4 | 10 | 3 products × 3 videos + 1 product × 1 video (Sound) |
| Datburgershop93 | 4 | 10 | 3 products × 3 videos + 1 product × 1 video (Sound) |

### Video Styles

- **Sound Method:** Primary style (2 per product)
- **Crying MOF:** Gymgoer1993 only (1 per product)
- **Snapchat MOF:** Dealrush93 & Datburgershop93 (1 per product)

### Notion Database

**Database ID:** `26d2b61d-84d1-8029-969d-d25728061db8`  
**Name:** Chelsea Video Tracker  
**Location:** Outside of any Claude Project

#### Properties

| Property | Type | Purpose |
|----------|------|---------|
| Amount of vids | Title | Always "1" (1 entry = 1 video) |
| Creator | Select | Always "Chelsea" |
| Products | Multi-select | Product name from inventory |
| Video Style | Select | Sound Method, Crying MOF, Snapchat MOF |
| TikTok Account | Select | Gymgoer1993, Dealrush93, Datburgershop93 |
| Status | Status | Not Started (default) |
| Due Date | Date | Tomorrow's date (YYYY-MM-DD) |
| New Sample | Checkbox | True if testing new product |

---

## Features & Workflows

### 1. Daily Lineup Generation (`/generate`)

**User Action:**
1. Take screenshots of TikTok Shop earnings
2. Send screenshots to bot via Telegram
3. Type `/generate`

**Bot Process:**
1. Fetches product inventory from Notion (208+ products)
2. Identifies New Samples (products with "New Sample" checkbox)
3. Sends screenshots to Claude API for OCR/extraction
4. Smart matches extracted products to inventory (handles typos)
5. Sorts products by units sold (high to low)
6. Generates lineup with priority:
   - New Samples first (distributed across accounts)
   - Top sellers by performance
   - Rotation products to fill remaining slots
7. Shows preview with product list and video counts
8. Waits for "confirm" or "cancel"

**On Confirm:**
1. Deletes old entries for tomorrow's date (if any)
2. Creates 35 new Notion entries (15 + 10 + 10)
3. Each entry tagged with correct account, product, style, date

**Commands:**
- `/start` - Show help
- `/status` - Check screenshot count
- `/clear` - Clear screenshots and start over
- `/generate` - Process and generate lineup

---

### 2. New Sample Management (`/newsample`)

**User Action:**
1. Type `/newsample` to enter new sample mode
2. Send screenshots from TikTok Shop showing new products
3. Type `/addsample` to process

**Bot Process:**
1. Claude analyzes screenshots
2. Extracts product names
3. Shortens/cleans names (e.g., "COSRX Advanced Snail 96 Mucin..." → "COSRX Snail Mucin")
4. Adds to Notion Products dropdown (auto-created)
5. Creates entry with "New Sample" checkbox checked
6. Product will be prioritized in next `/generate`

**Product Naming Rules:**
- Keep brand name if recognizable
- Remove filler words: "for", "with", "and", "pack of"
- Target 3-6 words max
- Title Case formatting

**Note:** Cannot set purple color via API (Notion limit >100 options). Manually change color in Notion UI if desired.

---

### 3. Smart Product Matching

**Problem:** TikTok Shop product names often have typos, inconsistent capitalization, or extra words.

**Solution:** Claude AI does fuzzy matching against inventory list.

**Examples:**
- "OPTIMUM NUTRITION Protein" → matches "Optimum Nutrition Whey Protein"
- "bloom greens powder" → matches "Bloom Super Greens"
- "cosrx snail mucin essense" (typo) → matches "COSRX Snail Mucin Essence"

**Matching Logic:**
- Exact match first
- Fuzzy match on brand + key words
- Claude decides best match from inventory list
- If no good match, excludes product (rare)

---

### 4. New Sample Detection

**How It Works:**
- Any entry with "New Sample" checkbox = new sample
- Bot fetches all entries where checkbox is checked
- Extracts unique product names from those entries
- Prioritizes those products in lineup generation

**Distribution:**
1. Gymgoer1993 gets first 2 new samples
2. Dealrush93 gets next new sample
3. Datburgershop93 gets next new sample
4. Cycle repeats if more samples exist

**To Mark Product as New Sample:**
- Create Notion entry with the product
- Check "New Sample" checkbox
- Or use `/newsample` workflow

**To Stop Testing:**
- Uncheck "New Sample" on all entries with that product
- Product becomes normal rotation product

---

### 5. Entry Replacement Logic

**Daily Cleanup:**
- Before creating new entries, bot deletes old entries for tomorrow's date
- Only deletes entries matching: Gymgoer1993, Dealrush93, or Datburgershop93
- Uses Due Date + TikTok Account filters (safe, won't delete other creators' entries)

**Filter Query:**
```json
{
  "and": [
    {"property": "Due Date", "date": {"equals": "YYYY-MM-DD"}},
    {"or": [
      {"property": "TikTok Account", "select": {"equals": "Gymgoer1993"}},
      {"property": "TikTok Account", "select": {"equals": "Dealrush93"}},
      {"property": "TikTok Account", "select": {"equals": "Datburgershop93"}}
    ]}
  ]
}
```

---

## Code Structure

### Main Components

**File:** `main.py` (1,133 lines)

```
main.py
├── Configuration
│   ├── API Keys
│   ├── TikTok Accounts
│   └── Fallback Product List
│
├── NotionClient Class
│   ├── get_entries_by_date()      # Query entries for deletion
│   ├── delete_entry()             # Delete single entry
│   ├── delete_entries_by_date()   # Bulk delete by date
│   ├── create_page()              # Create Notion entry
│   ├── add_product_to_schema()    # Check product exists
│   └── create_new_sample_entry()  # Create new sample entry
│
├── AI Processing Functions
│   ├── detect_image_type()                # Detect PNG/JPEG/etc
│   ├── process_screenshots_with_claude()  # OCR + extraction
│   ├── match_products_to_inventory()      # Smart matching (dummy - Claude does it)
│   └── extract_new_sample_products()      # New sample name extraction
│
├── Lineup Generation
│   ├── fetch_chelsea_products_from_notion() # Get inventory + new samples
│   ├── generate_daily_lineup()             # Core lineup algorithm
│   └── format_lineup_preview()             # Format preview message
│
├── Notion Operations
│   └── create_notion_entries()  # Bulk create entries
│
├── Telegram Handlers
│   ├── start_command()           # /start
│   ├── handle_photo()            # Photo upload handler
│   ├── newsample_command()       # /newsample
│   ├── process_new_sample_photo() # New sample photo handler
│   ├── addsample_command()       # /addsample
│   ├── generate_command()        # /generate
│   ├── handle_message()          # Text (confirm/cancel)
│   ├── clear_command()           # /clear
│   └── status_command()          # /status
│
└── main()  # Bot startup
```

---

## Database Schema

### Notion Multi-Select Options

**Products Property:**
- 200+ options (dynamic, auto-created when used)
- Various colors (manually set in Notion UI)
- New products get random color (API limitation)

**Video Style Property:**
- Sound Method
- Crying MOF
- Snapchat MOF
- Talking (legacy, not used)
- MOF (legacy, replaced by Crying/Snapchat)

**TikTok Account Property:**
- Gymgoer1993
- Dealrush93
- Datburgershop93

**Creator Property:**
- Chelsea (only value used by bot)
- Other values exist (user's buddy uses same template)

**Status Property:**
- Not Started (default)
- In Progress
- Completed
- (User manages these manually)

---

## Troubleshooting

### Common Issues

#### 1. "Conflict: terminated by other getUpdates request"

**Cause:** Deployment overlap - old bot instance still running while new one starts  
**Impact:** Harmless, self-resolves in 30-60 seconds  
**Action:** Wait for deployment to complete

---

#### 2. "Message is too long" (Telegram Error)

**Cause:** Too many new samples detected (>195)  
**Fix:** Already handled - bot truncates to first 5 new samples in message  
**Prevention:** Uncheck old new samples that finished testing

---

#### 3. "TypeError: '<' not supported between instances of 'int' and 'NoneType'"

**Cause:** Some products have `None` for units_sold (Claude couldn't extract number)  
**Fix:** Already handled - treats `None` as `0` when sorting  
**Code:**
```python
available_products.sort(
    key=lambda x: x["units_sold"] if x["units_sold"] is not None else 0, 
    reverse=True
)
```

---

#### 4. "Error updating schema: 400 - body.properties.Products.multi_select.options.length should be ≤ '100'"

**Cause:** Notion API limits schema updates to 100 options when >100 options exist  
**Fix:** Skip schema update entirely, let entry creation auto-add new products  
**Impact:** Can't control color of new products (get random color)

---

#### 5. `httpx.ReadTimeout`

**Cause:** Render free tier network slowness, default 5s timeout too short  
**Fix:** Set 30-second timeout on all httpx clients  
**Code:**
```python
async with httpx.AsyncClient(timeout=30.0) as client:
```

---

#### 6. Bot doesn't detect new products I just added to Notion

**Issue:** Added products to dropdown but no entries exist yet  
**Detection Method:** Bot finds new samples from entries with checkbox checked, not from dropdown  
**Solution:** Either:
- Use `/newsample` workflow (recommended)
- Manually create entry with product and check "New Sample" box

---

#### 7. Old entries not being deleted

**Check:**
1. Render logs show "Looking for entries to delete with due date: YYYY-MM-DD"
2. Should show "Found X entries to delete"
3. If "Found 0" but entries exist, check:
   - Entry Due Date matches tomorrow
   - Entry TikTok Account is Gymgoer1993, Dealrush93, or Datburgershop93
   - Database ID is correct in environment variables

---

### Debugging Tips

**View Render Logs:**
1. Go to Render dashboard
2. Click "tiktok-notion-bot"
3. Click "Logs" in left sidebar
4. Set to "Live tail"

**Key Log Messages:**
```
Starting TikTok Notion Bot...
Database ID: 26d2b61d-84d1-8029-969d-d25728061db8
Notion API Key present: True
Anthropic API Key present: True
Bot is running...
```

**Test API Keys:**
```bash
# Test Notion
curl https://api.notion.com/v1/databases/26d2b61d-84d1-8029-969d-d25728061db8 \
  -H "Authorization: Bearer YOUR_NOTION_KEY" \
  -H "Notion-Version: 2022-06-28"

# Test Anthropic
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: YOUR_ANTHROPIC_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-20250514","max_tokens":100,"messages":[{"role":"user","content":"test"}]}'
```

---

## Future Improvements

### Potential Features

1. **Video Performance Tracking**
   - Track which videos get views/sales
   - Use performance data to optimize lineup algorithm
   - Penalize consistently poor-performing products

2. **Automated Screenshot Collection**
   - Connect to TikTok Shop API (if available)
   - Auto-fetch daily earnings data
   - Eliminate manual screenshot step

3. **Multi-User Support**
   - Allow buddy to use same bot with different accounts
   - Add user authentication/permissions
   - Separate product inventories per user

4. **Smart Video Style Selection**
   - Track which styles perform best per product category
   - Auto-assign optimal style based on product type
   - A/B test new styles

5. **Product Category Tagging**
   - Categorize products (supplements, skincare, etc.)
   - Ensure variety across categories in lineup
   - Filter/search by category

6. **Webhook Integration**
   - Push completed entries to Zapier/Make
   - Trigger video generation workflows
   - Sync status updates back to Notion

7. **Analytics Dashboard**
   - Web UI showing:
     - Top performing products
     - Account performance comparison
     - New sample success rate
     - Video output trends

8. **Bulk Product Import**
   - Upload CSV of new products
   - Auto-add to inventory with metadata
   - Bulk mark as new samples

9. **Scheduled Daily Run**
   - Auto-generate lineup at specific time
   - Send preview to Telegram for approval
   - Reduce manual trigger requirement

10. **Voice Notes Support**
    - Record voice note with product names
    - Transcribe + add as new samples
    - Faster than screenshots

---

## API Rate Limits

### Notion API
- **Rate Limit:** 3 requests per second
- **Current Mitigation:** 0.3s delay between operations (within limit)
- **Bulk Operations:** Creating 35 entries takes ~15 seconds

### Anthropic API
- **Rate Limit:** Varies by plan (likely 50 req/min on default)
- **Current Usage:** 1-2 requests per lineup generation (low)
- **Cost:** ~$0.05 per lineup (100 tokens in, 500 tokens out)

### Telegram API
- **Rate Limit:** 30 messages per second per bot
- **Current Usage:** <5 messages per workflow (well within limit)

---

## Security Considerations

### API Keys
- **Storage:** Environment variables on Render (secure)
- **Rotation:** Should rotate annually or if compromised
- **Scope:** Keys have minimum required permissions

### Data Privacy
- **Screenshots:** Processed by Anthropic API (check their data policy)
- **Notion Data:** Shared database with buddy (be aware)
- **Telegram:** Messages visible to Telegram (use for non-sensitive data only)

### Access Control
- **Bot Access:** Only authorized Telegram user ID(s) should use bot
- **Notion Database:** Anyone with database ID + API key can modify
- **GitHub Repo:** Private repository (keep it that way)

---

## Contact & Support

### Owner
- **Name:** Thomas
- **GitHub:** thoardyr
- **TikTok Accounts:** @Gymgoer1993, @Dealrush93, @Datburgershop93

### External Resources
- **Notion API Docs:** https://developers.notion.com/
- **Anthropic API Docs:** https://docs.anthropic.com/
- **python-telegram-bot Docs:** https://docs.python-telegram-bot.org/

### Maintenance Schedule
- **Code Review:** Monthly (check for API deprecations)
- **Dependency Updates:** Quarterly
- **Cost Review:** Monthly ($7 Render + ~$5 Anthropic)

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| Jan 2026 | 1.0 | Initial deployment |
| Jan 9, 2026 | 1.1 | Added new sample workflow, fixed multi-data source issue |
| Jan 10, 2026 | 1.2 | Changed video distribution (15/10/10), updated MOF styles |
| Jan 16, 2026 | 1.3 | Fixed None sorting bug, added 30s timeouts |

---

## Quick Start (For New Developer)

1. **Clone Repository:**
   ```bash
   git clone https://github.com/thoardyr/tiktok-notion-bot.git
   cd tiktok-notion-bot
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Environment Variables:**
   ```bash
   export TELEGRAM_BOT_TOKEN="your_token"
   export NOTION_API_KEY="your_key"
   export ANTHROPIC_API_KEY="your_key"
   export NOTION_DATABASE_ID="26d2b61d-84d1-8029-969d-d25728061db8"
   ```

4. **Run Locally:**
   ```bash
   python main.py
   ```

5. **Test on Telegram:**
   - Open Telegram
   - Search for your bot
   - Send `/start`
   - Send test screenshot
   - Run `/generate`

6. **Deploy to Render:**
   - Connect GitHub repo
   - Add environment variables
   - Deploy

---

## Emergency Contacts

### If Bot Goes Down
1. Check Render logs for errors
2. Verify environment variables are set
3. Test API keys manually
4. Restart service on Render
5. If all else fails: Manually create Notion entries (fallback)

### If Notion API Changes
- Monitor Notion changelog: https://developers.notion.com/changelog
- Update API version in headers if required
- Test locally before deploying

### If Anthropic API Changes
- Monitor Anthropic changelog
- Update model string if deprecated
- Adjust token limits if pricing changes

---

**Document End**

*This handover document contains all information needed to understand, maintain, and extend the TikTok Notion Bot. Keep this document updated as the system evolves.*
