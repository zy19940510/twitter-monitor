#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 从 .env 文件加载配置
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

# 使用环境变量，如果未设置则使用默认值
LOG_DIR="${LOG_DIR:-$HOME/.twitter-monitor/logs}"
LOG_DIR=$(eval echo "$LOG_DIR")  # 展开路径中的 ~ 符号
LOG_FILE="$LOG_DIR/monitor_$(date +%Y%m%d).log"

mkdir -p "$LOG_DIR"

echo "=== $(date) ===" >> "$LOG_FILE"
cd "$SCRIPT_DIR"
source .venv/bin/activate
python3 graph.py >> "$LOG_FILE" 2>&1

find "$LOG_DIR" -name "monitor_*.log" -mtime +7 -delete 2>/dev/null || true
