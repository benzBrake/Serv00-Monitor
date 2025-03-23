#!/bin/bash

# 脚本的用途
echo "这个脚本将自动检测并创建venv虚拟环境，自动安装依赖项，并添加一个crontab任务，每小时运行一次指定的Python脚本。"

# 获取脚本所在的目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 定义venv路径
VENV_PATH="$SCRIPT_DIR/venv"

# 定义Python脚本路径
PYTHON_SCRIPT_PATH="$SCRIPT_DIR/task.py"

# 定义requirements.txt路径
REQUIREMENTS_PATH="$SCRIPT_DIR/requirements.txt"

# 检查venv是否存在
if [ ! -d "$VENV_PATH" ]; then
    echo "未检测到venv虚拟环境，正在创建..."
    python3 -m venv "$VENV_PATH"
    if [ $? -ne 0 ]; then
        echo "创建venv虚拟环境失败。"
        exit 1
    fi
    echo "venv虚拟环境已创建。"
else
    echo "venv虚拟环境已存在。"
fi

# 激活venv
source "$VENV_PATH/bin/activate"

# 安装依赖项
if [ -f "$REQUIREMENTS_PATH" ]; then
    echo "正在安装依赖项..."
    pip install -r "$REQUIREMENTS_PATH"
    if [ $? -ne 0 ]; then
        echo "安装依赖项失败。"
        exit 1
    fi
    echo "依赖项已安装。"
else
    echo "未找到requirements.txt文件，跳过安装依赖项。"
fi

# 定义crontab条目
CRON_ENTRY="0 * * * * $VENV_PATH/bin/python3 $PYTHON_SCRIPT_PATH"

# 检查crontab条目是否已存在
if ! crontab -l | grep -qF "$CRON_ENTRY"; then
    echo "未检测到crontab任务，正在添加..."
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    if [ $? -eq 0 ]; then
        echo "成功添加crontab任务："
        echo "$CRON_ENTRY"
    else
        echo "添加crontab任务失败。"
        exit 1
    fi
else
    echo "crontab任务已存在。"
fi

echo "完成。"

