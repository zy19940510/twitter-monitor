# Twitter/X For You Smart Monitor

[中文](README.zh-CN.md) | English

A **LangGraph**-based Twitter monitoring system that automatically fetches For You recommendations → AI analysis → pushes to Telegram.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Latest-green.svg)](https://github.com/langchain-ai/langgraph)

## Features

- 🔄 **Automated Fetching**: Uses agent-browser via CDP to scrape Twitter For You timeline
- 🤖 **AI Analysis**: Support for 7 LLM providers with one-click switching
- 📱 **Real-time Push**: Analysis results pushed to Telegram
- 🔐 **CDP Mode**: Connect to Chrome Debug, reuse login state, no repeated logins
- 🔒 **Login Verification**: Auto-detect login status with clear error messages
- 🏗️ **LangGraph**: State machine workflow, easy to extend

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph StateGraph                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   START → [fetch] → [filter] ─┬─→ [analyse] → [push] → END  │
│                               │                             │
│                               └─→ END (skip if no new)       │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Nodes:
├── fetch    → FetchAgent (agent-browser scraping)
├── filter   → Filter processed tweets (SQLite dedup)
├── analyse  → AnalyseAgent (LLM analysis)
└── push     → PushAgent (Telegram push)
```

## Quick Start

### 1. Install Dependencies

```bash
# Clone the project
git clone https://github.com/yourusername/twitter-monitor.git
cd twitter-monitor

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install agent-browser (requires Node.js)
npm install -g @browserbase/agent-browser
```

### 2. Configuration

```bash
cp .env.example .env
vim .env  # or use your preferred editor
```

Key configurations:

```bash
# LLM Provider (choose one)
LLM_PROVIDER=local  # Options: local/ark/one/anthropic/openai/ollama/gemini

# Telegram Push
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Chrome Configuration (adjust for your OS)
# macOS
CHROME_PATH=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome
# Linux
# CHROME_PATH=/usr/bin/google-chrome
# Windows
# CHROME_PATH=C:/Program Files/Google/Chrome/Application/chrome.exe

CHROME_USER_DATA_DIR=~/.chrome-debug-profile
CDP_PORT=9222

# Optional Configurations
SCROLL_COUNT=20              # Number of scrolls (controls tweet quantity)
MAX_TWEETS_TO_ANALYZE=20     # Max tweets to analyze
MAX_TWEETS_TO_DISPLAY=10     # Max tweets to display in Telegram
DB_RETENTION_DAYS=7          # Data retention days
```

### 3. First-time Twitter Login

```bash
./login.sh
```

**Workflow**:
1. Script auto-starts Chrome in Debug mode (CDP port 9222)
2. Visit https://x.com/home and login in browser
3. Return to terminal and press Enter after login
4. Auto-save login state
5. **Browser closes automatically** (saves resources)

⚠️ **Important**: When logging in, ensure:
1. Complete username and password entry
2. Complete all verification steps (email/phone)
3. **Wait until you see the tweet feed on homepage**
4. Wait for page to fully load before pressing Enter

Verify login status:
```bash
./check_login.sh
```

### 4. Test Run

```bash
source .venv/bin/activate
python3 test_login_detection.py  # Test login and fetch
```

### 5. Production Run

```bash
source .venv/bin/activate
python3 graph.py
```

### 6. Setup Cron Job

```bash
crontab -e
# Add (runs every 10 minutes):
*/10 * * * * /path/to/twitter-monitor/run.sh
```

## Project Structure

```
twitter-monitor/
├── graph.py                     # LangGraph workflow (main entry)
├── test_login_detection.py     # Login status test script
├── agents/
│   ├── base.py                  # Agent base class
│   ├── llm_factory.py           # LLM factory (multi-provider)
│   ├── fetch_agent/             # Fetch agent (CDP + login verification)
│   ├── analyse_agent/           # Analysis agent (LLM)
│   └── push_agent/              # Push agent (Telegram)
├── .env.example                 # Configuration template
├── .gitignore                   # Git ignore rules
├── requirements.txt             # Python dependencies
├── run.sh                       # Cron startup script
├── login.sh                     # CDP login script
└── check_login.sh               # Login status check

~/.twitter-monitor/
├── twitter_auth.json            # Twitter login state (CDP saved)
├── twitter_monitor.db           # SQLite dedup database
└── logs/                        # Run logs
```

## LLM Provider Support

| Provider | Config Prefix | Description |
|----------|---------------|-------------|
| `local` | `LOCAL_*` | Local reverse proxy (default, OpenAI compatible) |
| `openai` | `OPENAI_*` | OpenAI Official |
| `anthropic` | `ANTHROPIC_*` | Anthropic Official |
| `ollama` | `OLLAMA_*` | Ollama local models |
| `ark` | `ARK_*` | Volcano Engine Ark |
| `one` | `ONE_*` | LB One API |
| `gemini` | `GEMINI_*` | Google Gemini |

Switch provider by changing `LLM_PROVIDER=xxx` in `.env`.

## Configuration Reference

See [Configuration Documentation](README.zh-CN.md#配置说明) for detailed configuration options.

## Output Example

```
[20:30:15] Starting LangGraph workflow

[Node: fetch] Fetching tweets...
  → Got 25 tweets
[Node: filter] Filtering new tweets...
  → 8 new tweets
[Node: analyse] AI analyzing...
  → Analysis complete (using local/claude-sonnet-4-5)
[Node: push] Pushing to Telegram...
  → Push successful

[Completed] Time: 12.3s
✅ Successfully analyzed 8 tweets
```

## Troubleshooting

### Problem: Not Logged In

```bash
./login.sh  # Re-login
```

### Problem: Chrome Fails to Start

Check if `CHROME_PATH` in `.env` is correct for your OS.

### Problem: Push Failed

Check Telegram configuration in `.env`.

### Problem: Missing Packages

```bash
pip install -r requirements.txt
npm install -g @browserbase/agent-browser
```

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Tech Stack

- **Workflow Engine**: LangGraph StateGraph
- **Browser Automation**: agent-browser (Playwright)
- **LLM**: LangChain + OpenAI SDK (multi-provider)
- **Data Storage**: SQLite
- **Push**: Telegram Bot API
- **Scheduling**: cron

## Roadmap

- [ ] Multi-language translation
- [ ] Obsidian integration
- [ ] Trend tracking
- [ ] Keyword alerts
- [ ] Multi-agent collaboration

## Support

If you find this project helpful, please give it a ⭐️ on GitHub!

For issues and feature requests, please use [GitHub Issues](https://github.com/yourusername/twitter-monitor/issues).
