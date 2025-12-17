#!/bin/bash

echo "========================================"
echo "表转服务系统"
echo "========================================"
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到Python3，请先安装Python 3.11+"
    exit 1
fi

# 激活虚拟环境（如果存在）
if [ -d "venv" ]; then
    echo "[信息] 激活虚拟环境..."
    source venv/bin/activate
fi

# 检查依赖是否安装
echo "[信息] 检查依赖..."
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "[信息] 正在安装依赖..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[错误] 依赖安装失败"
        exit 1
    fi
fi

# 检查.env文件（从backend目录或项目根目录）
if [ ! -f .env ] && [ ! -f ../.env ]; then
    echo "[警告] 未找到.env文件"
    if [ -f ".env.example" ] || [ -f "../.env.example" ]; then
        echo "[信息] 从.env.example创建.env文件..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
        else
            cp ../.env.example .env
        fi
        echo "[提示] 请编辑.env文件配置数据库连接信息"
    else
        echo "[错误] 未找到.env.example文件"
        exit 1
    fi
fi

# 创建logs目录
mkdir -p logs

# 启动服务
echo "[信息] 启动服务..."
echo "访问地址: http://localhost:5001"
echo "API文档: http://localhost:5001/docs"
echo ""
cd "$(dirname "$0")"
uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload

