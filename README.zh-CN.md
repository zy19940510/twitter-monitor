# Twitter/X For You 智能监控系统

[English](README.md) | 中文

基于 **LangGraph** 的 Twitter 实时监控系统，自动抓取 For You 推荐 → AI 分析热点 → 推送到 Telegram。

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph StateGraph                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   START → [fetch] → [filter] ─┬─→ [analyse] → [push] → END  │
│                               │                             │
│                               └─→ END (无新推文时跳过)       │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Nodes:
├── fetch    → FetchAgent (agent-browser 抓取推文)
├── filter   → 过滤已处理推文 (SQLite 去重)
├── analyse  → AnalyseAgent (LLM 分析热点)
└── push     → PushAgent (Telegram 推送)
```

## 功能特性

- 🔄 **定时抓取**: 使用 agent-browser 通过 CDP 抓取 Twitter For You 推荐
- 🤖 **AI 分析**: 支持 7 种 LLM Provider 一键切换
- 📱 **实时推送**: 分析结果推送到 Telegram
- 🔐 **CDP 模式**: 连接 Chrome Debug，复用登录状态，无需重复登录
- 🔒 **登录验证**: 自动检测登录状态，提供明确错误提示
- 🏗️ **LangGraph**: 状态机工作流，易于扩展

## 快速开始

### 1. 安装依赖

```bash
# 克隆或下载项目
cd ~/scripts/twitter-monitor  # 替换为你的项目路径

# 创建虚拟环境
uv venv && source .venv/bin/activate
# 或使用 python3 -m venv .venv && source .venv/bin/activate

# 安装依赖
uv pip install -r requirements.txt
# 或使用 pip install -r requirements.txt
```

### 2. 配置

```bash
cp .env.example .env
vim .env
```

关键配置：
```bash
# 一键切换 LLM Provider
LLM_PROVIDER=local  # 可选: local/ark/one/anthropic/openai/ollama/gemini

# Telegram 推送
# 从 https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getUpdates 获取 chat_id
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Chrome 浏览器路径（根据你的操作系统调整）
# macOS: /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
# Linux: /usr/bin/google-chrome
# Windows: C:/Program Files/Google/Chrome/Application/chrome.exe
CHROME_PATH=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome

# Chrome 用户数据目录（用于保持登录状态）
CHROME_USER_DATA_DIR=~/.chrome-debug-profile

# CDP 端口（默认 9222）
CDP_PORT=9222

# 其他可选配置
SCROLL_COUNT=20              # 滚动次数，控制抓取推文数量
MAX_TWEETS_TO_ANALYZE=20     # 最多分析多少条推文
MAX_TWEETS_TO_DISPLAY=10     # Telegram 消息中最多显示多少条
DB_RETENTION_DAYS=7          # 已读推文保留天数
LOG_DIR=~/.twitter-monitor/logs  # 日志目录
```

### 3. 首次登录 Twitter

```bash
./login.sh
```

**工作流程**:
1. 脚本自动启动 Chrome Debug 模式 (CDP 端口 9222)
2. 在浏览器中访问 https://x.com/home 并登录
3. 登录完成后回到终端按 Enter
4. 自动保存登录态
5. **自动关闭浏览器**（节省资源）

**优势**:
- ✅ 使用你熟悉的 Chrome 配置
- ✅ 可以用 Google 账号快速登录
- ✅ 登录态持久保存
- ✅ 用完自动关闭，节省资源
- ✅ 下次运行自动启动并加载登录态

⚠️ **重要**：登录时请确保：
1. 完整输入用户名和密码
2. 完成所有验证步骤（邮箱/手机号）
3. **等待进入主页并看到推文流**
4. 页面完全加载后再按 Enter

验证登录状态：
```bash
./check_login.sh  # 检查登录态是否有效
```

### 4. 测试运行

```bash
source .venv/bin/activate
python3 test_login_detection.py  # 测试登录状态和抓取功能
```

### 5. 正式运行

```bash
source .venv/bin/activate
python3 graph.py
```

**注意**:
- ✅ 使用 CDP 模式连接到 Chrome Debug 浏览器
- ✅ Chrome 按需自动启动和关闭，节省资源
- ✅ 登录态持久保存，无需重复登录
- ✅ 系统会自动验证登录状态，如果未登录会给出明确提示

### 6. 设置定时任务

```bash
crontab -e
# 添加（每 10 分钟执行）：
*/10 * * * * /path/to/your/twitter-monitor/run.sh
# 例如: */10 * * * * /Users/yourname/scripts/twitter-monitor/run.sh
```

## 项目结构

```
twitter-monitor/
├── graph.py                     # LangGraph 工作流（主入口）
├── test_login_detection.py     # 登录状态测试脚本
├── agents/
│   ├── base.py                  # Agent 基类
│   ├── llm_factory.py           # LLM 工厂（多 Provider）
│   ├── fetch_agent/             # 抓取代理 (CDP + 登录验证)
│   ├── analyse_agent/           # 分析代理 (LLM)
│   └── push_agent/              # 推送代理 (Telegram)
├── .env                         # 配置文件
├── .env.example                 # 配置模板
├── run.sh                       # cron 启动脚本
├── login.sh                     # CDP 登录脚本
├── check_login.sh               # 登录状态检查
└── requirements.txt             # Python 依赖

~/.twitter-monitor/
├── twitter_auth.json            # Twitter 登录状态 (CDP 保存)
├── twitter_monitor.db           # SQLite 去重数据库
├── debug_login_failed.json      # 登录失败调试快照（自动生成）
└── logs/                        # 运行日志
```

## LLM Provider 配置

| Provider | 配置前缀 | 说明 |
|----------|----------|------|
| `local` | `LOCAL_*` | 本地代理（默认，OpenAI 兼容） |
| `ark` | `ARK_*` | 火山方舟 |
| `one` | `ONE_*` | LB One API |
| `anthropic` | `ANTHROPIC_*` | Anthropic 官方 |
| `openai` | `OPENAI_*` | OpenAI 官方 |
| `ollama` | `OLLAMA_*` | Ollama 本地 |
| `gemini` | `GEMINI_*` | Google Gemini |

切换 Provider 只需修改 `.env` 中的 `LLM_PROVIDER=xxx`。

## 配置说明

所有配置都通过环境变量设置，在 `.env` 文件中配置（参考 `.env.example`）：

### 必需配置

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `LLM_PROVIDER` | LLM 提供商 | `local`, `openai`, `anthropic` 等 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | `123456789:ABCdef...` |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | `123456789` |

### Chrome 配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `CHROME_PATH` | Chrome 可执行文件路径 | macOS: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` |
| `CHROME_USER_DATA_DIR` | Chrome 用户数据目录 | `~/.chrome-debug-profile` |
| `CDP_PORT` | Chrome DevTools Protocol 端口 | `9222` |

### 抓取配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `SCROLL_COUNT` | 滚动加载次数（控制抓取数量） | `3` |
| `MAX_TWEETS_PER_FETCH` | 每次最多抓取推文数 | `30` |
| `BROWSER_SESSION` | agent-browser 会话名称 | `twitter` |
| `DATA_DIR` | 数据存储目录 | `~/.twitter-monitor` |

### 分析与推送配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `MAX_TWEETS_TO_ANALYZE` | 最多分析多少条推文 | `20` |
| `MAX_TWEETS_TO_DISPLAY` | Telegram 消息中最多显示多少条 | `10` |
| `LLM_TEMPERATURE` | LLM 温度参数 | `0.3` |

### 系统配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `DB_RETENTION_DAYS` | 已读推文数据保留天数 | `7` |
| `LOG_DIR` | 日志存储目录 | `~/.twitter-monitor/logs` |

## 输出示例

```
[20:30:15] 开始执行 LangGraph 工作流

[Node: fetch] 抓取推文...
  → 获取到 25 条推文
[Node: filter] 过滤新推文...
  → 8 条新推文
[Node: analyse] AI 分析中...
  → 分析完成 (使用 local/claude-sonnet-4-5)
[Node: push] 推送到 Telegram...
  → 推送成功

[完成] 耗时 12.3s
✅ 成功分析 8 条推文
```

Telegram 推送效果：
```
📱 Twitter/X 热点速递
🕐 2026-01-28 20:30 | 📊 8 条新推文 | 🤖 local/claude-sonnet-4-5

🔥 热点话题
1. **AI Agent 框架之争** - LangGraph vs CrewAI 讨论激烈...
2. **OpenAI 新模型发布** - GPT-5 即将上线...

💡 值得关注的观点
- @elonmusk 暗示 X 将推出新功能...

📊 潜在机会信号
- AI 基础设施赛道持续火热...
```

## 故障排除

### 问题 1: 抓不到推文 / 未登录

**症状**:
```
❌ 未登录或登录已失效！
```

**解决方案**:
```bash
# 1. 检查登录状态
./check_login.sh

# 2. 重新登录（如果需要）
./login.sh
# ⚠️ 确保等待进入主页看到推文流后再按 Enter

# 3. 测试
python3 test_login_detection.py
```

**常见原因**:
- 登录态文件缺少 `auth_token`（未完成登录）
- 登录过期（Cookie 超时）
- Chrome CDP 浏览器未运行

### 问题 2: Chrome 自动启动失败

**症状**:
```
❌ Chrome 启动失败，请手动运行: ./login.sh
```

**解决方案**:
```bash
# 手动启动并登录
./login.sh
```

### 问题 3: 想手动保持 Chrome 运行

**解决方案**:
注释掉 graph.py 中的自动关闭逻辑：
```python
# 在 cleanup() 方法中注释掉 pkill 命令
def cleanup(self):
    if self.db_conn:
        self.db_conn.close()
    # print("\n🔒 关闭浏览器...")  # 注释掉
    # subprocess.run(...)            # 注释掉
```

手动启动 Chrome：
```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=~/.chrome-debug-profile &

# Linux
google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=~/.chrome-debug-profile &

# Windows (在 PowerShell 中)
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 `
  --user-data-dir=%USERPROFILE%\.chrome-debug-profile
```

### 问题 4: 页面加载超时

**症状**:
```
Failed to read: Resource temporarily unavailable
```

**解决方案**:
- 检查网络连接
- 增加等待时间（修改 `SCROLL_COUNT` 和 wait 时间）
- 检查是否有防火墙阻止

### 问题 5: 调试抓取问题

查看调试快照：
```bash
cat ~/.twitter-monitor/debug_login_failed.json | python3 -m json.tool | less
```

## 后续扩展

### 1. 添加新节点

LangGraph 架构便于扩展新功能：

```python
# 在 graph.py 中添加新节点
def _translate_node(self, state: MonitorState) -> dict:
    """翻译节点 - 将分析结果翻译成其他语言"""
    # 你的翻译逻辑
    return {"summary": translated_summary}

# 构建图时添加
builder.add_node("translate", self._translate_node)
builder.add_edge("analyse", "translate")
builder.add_edge("translate", "push")
```

### 2. 计划中的扩展

| 功能 | 说明 | 状态 |
|------|------|------|
| 🌐 **多语言翻译** | 将分析结果翻译成英文/日文 | 计划中 |
| 📝 **Obsidian 归档** | 自动保存到 Obsidian 笔记 | 计划中 |
| 🔍 **深度分析** | 对热门话题进行深入研究 | 计划中 |
| 📊 **趋势追踪** | 跟踪话题热度变化 | 计划中 |
| 🔔 **关键词告警** | 特定关键词触发即时推送 | 计划中 |
| 🤖 **多 Agent 协作** | 不同 Agent 处理不同类型内容 | 计划中 |

### 3. 并行执行多个分析

```python
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

# 并行执行多个分析任务
builder.add_node("analyse_tech", self._analyse_tech_node)
builder.add_node("analyse_finance", self._analyse_finance_node)
builder.add_edge("filter", "analyse_tech")
builder.add_edge("filter", "analyse_finance")
```

### 4. Human-in-the-loop

```python
# 添加人工审核节点
builder.add_node("review", self._human_review_node)
builder.add_conditional_edges(
    "analyse",
    self._needs_review,
    {"review": "review", "auto": "push"}
)
```

### 5. 持久化检查点

```python
from langgraph.checkpoint.sqlite import SqliteSaver

# 添加检查点，支持断点续传
memory = SqliteSaver.from_conn_string("twitter_monitor.db")
graph = builder.compile(checkpointer=memory)
```

## 故障排查

### 抓取失败

```bash
# 检查 agent-browser 状态
agent-browser --session twitter open https://x.com/home

# 重新登录
./login.sh
```

### 推送失败

```bash
# 测试 Telegram Bot
curl "https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=test"
```

### 查看日志

```bash
tail -f ~/.twitter-monitor/logs/monitor_$(date +%Y%m%d).log
```

## 技术栈

- **工作流引擎**: LangGraph StateGraph
- **浏览器自动化**: agent-browser (Playwright)
- **LLM**: LangChain + OpenAI SDK (多 Provider)
- **数据存储**: SQLite
- **推送**: Telegram Bot API
- **定时任务**: cron

## License

MIT
