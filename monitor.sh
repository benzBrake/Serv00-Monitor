#!/bin/bash

# 定义 pm2 的路径
PM2_PATH="/home/{username}/.npm-global/bin/pm2"
LOG_FILE="$(dirname "$0")/mon.log"

# 函数：记录日志
log_message() {
  local message="$1"
  echo "$(date +'%Y-%m-%d %H:%M:%S') - $message" >> "$LOG_FILE"

  # 检查日志文件大小，如果超过10K则滚动日志
  if [ $(wc -c < "$LOG_FILE") -ge 10240 ]; then
    mv "$LOG_FILE" "$LOG_FILE.bak"
    echo "$(date +'%Y-%m-%d %H:%M:%S') - Log rotated" > "$LOG_FILE"
  fi
}

# 检查是否有任何 pm2 进程处于 online 状态
if ! $PM2_PATH list | grep -q 'online'; then
  log_message "No online PM2 processes found. Executing pm2 resurrect."
  # 如果没有找到 online 状态的进程，则执行 pm2 resurrect 并记录输出
  $PM2_PATH resurrect >> "$LOG_FILE" 2>&1
  log_message "pm2 resurrect executed."
else
  log_message "Online PM2 processes found. No action needed."
fi

