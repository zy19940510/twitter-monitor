# Twitter Monitor - 快速参考

## 核心文件

### 配置
- **.env.example** - 配置模板（复制为 .env）
- **.env** - 实际配置（包含敏感信息，不提交到 Git）
- **.gitignore** - Git 忽略规则

### 脚本
- **login.sh** - CDP 登录脚本，启动 Chrome 并保存登录态
- **check_login.sh** - 检查登录态是否有效
- **run.sh** - Cron 定时任务启动脚本

### Python
- **graph.py** - 主程序，LangGraph 工作流
- **test_login_detection.py** - 登录状态测试
- **requirements.txt** - Python 依赖

### 文档
- **README.md** - 完整文档
- **QUICK_REFERENCE.md** - 本文件

## 快速开始

```bash
# 0. 配置
cp .env.example .env
vim .env  # 填写配置

# 1. 安装依赖
pip install -r requirements.txt
npm install -g @browserbase/agent-browser

# 2. 登录（首次）
./login.sh

# 3. 验证
./check_login.sh

# 4. 测试
python3 test_login_detection.py

# 5. 运行
python3 graph.py

# 6. 定时任务
crontab -e
# 添加: */10 * * * * /path/to/twitter-monitor/run.sh
```

## 核心配置

### 必需配置
```bash
LLM_PROVIDER=local              # LLM 提供商
TELEGRAM_BOT_TOKEN=xxx          # Telegram Bot Token
TELEGRAM_CHAT_ID=xxx            # Telegram Chat ID
```

### Chrome 配置（按操作系统调整）
```bash
# macOS
CHROME_PATH=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome
CHROME_USER_DATA_DIR=~/.chrome-debug-profile

# Linux
CHROME_PATH=/usr/bin/google-chrome
CHROME_USER_DATA_DIR=~/.chrome-debug-profile

# Windows
CHROME_PATH=C:/Program Files/Google/Chrome/Application/chrome.exe
CHROME_USER_DATA_DIR=%USERPROFILE%\.chrome-debug-profile
```

### 可选配置
```bash
CDP_PORT=9222                   # CDP 端口
SCROLL_COUNT=20                 # 滚动次数
MAX_TWEETS_TO_ANALYZE=20        # 分析推文数
MAX_TWEETS_TO_DISPLAY=10        # 显示推文数
DB_RETENTION_DAYS=7             # 数据保留天数
LOG_DIR=~/.twitter-monitor/logs # 日志目录
```

## 架构

```
CDP 模式（按需启动）:
  login.sh → 启动 Chrome → 登录 → 保存 → 关闭
    ↓
  登录态持久保存到 {DATA_DIR}/twitter_auth.json
    ↓
  graph.py → 自动启动 Chrome → 加载登录态 → 抓取 → 关闭
    ↓
  节省资源，无需手动管理
```

## LLM Provider 支持

| Provider | 配置前缀 | 说明 |
|----------|----------|------|
| local | LOCAL_* | 本地反向代理 |
| openai | OPENAI_* | OpenAI 官方 |
| anthropic | ANTHROPIC_* | Anthropic 官方 |
| ollama | OLLAMA_* | Ollama 本地模型 |
| ark | ARK_* | 火山方舟 |
| one | ONE_* | LB One API |
| gemini | GEMINI_* | Google Gemini |

## 优势

- ✅ **按需启动** - 用时启动，用完关闭
- ✅ **一次登录，永久使用** - 登录态持久保存
- ✅ **Google 账号登录** - 可以快速登录
- ✅ **自动化管理** - 无需手动启动/关闭 Chrome
- ✅ **节省资源** - 不占用后台资源
- ✅ **跨平台** - 支持 macOS, Linux, Windows
- ✅ **多 LLM 支持** - 7 种 Provider 一键切换
- ✅ **环境变量配置** - 易于定制和部署

## 故障排除

### 问题：未登录
```bash
./login.sh  # 重新登录
```

### 问题：Chrome 启动失败
检查 `.env` 中的 `CHROME_PATH` 是否正确

### 问题：推送失败
检查 `.env` 中的 Telegram 配置

### 问题：找不到包
```bash
pip install -r requirements.txt
npm install -g @browserbase/agent-browser
```
