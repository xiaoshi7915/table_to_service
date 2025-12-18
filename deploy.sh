#!/bin/bash
# 一键部署脚本 - 适用于Linux云服务器

set -e  # 遇到错误立即退出

echo "=========================================="
echo "开始部署表转服务系统"
echo "=========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查是否为root用户
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}请不要使用root用户运行此脚本${NC}"
   exit 1
fi

# 1. 检查Python版本
echo -e "${YELLOW}[1/8] 检查Python版本...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 未安装，请先安装Python 3.11或更高版本${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}Python版本: $(python3 --version)${NC}"

# 2. 检查并安装系统依赖
echo -e "${YELLOW}[2/8] 检查系统依赖...${NC}"
if command -v apt-get &> /dev/null; then
    echo "检测到Debian/Ubuntu系统，安装依赖..."
    sudo apt-get update
    sudo apt-get install -y python3-pip python3-venv mysql-client
elif command -v yum &> /dev/null; then
    echo "检测到CentOS/RHEL系统，安装依赖..."
    sudo yum install -y python3 python3-pip mysql
elif command -v dnf &> /dev/null; then
    echo "检测到Fedora系统，安装依赖..."
    sudo dnf install -y python3 python3-pip mysql
else
    echo -e "${YELLOW}无法自动检测包管理器，请手动安装: python3, pip, mysql-client${NC}"
fi

# 3. 创建虚拟环境
echo -e "${YELLOW}[3/8] 创建Python虚拟环境...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}虚拟环境创建成功${NC}"
else
    echo -e "${GREEN}虚拟环境已存在${NC}"
fi

# 4. 激活虚拟环境并安装依赖
echo -e "${YELLOW}[4/8] 安装Python依赖...${NC}"
source venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

# 5. 配置环境变量
echo -e "${YELLOW}[5/8] 配置环境变量...${NC}"
if [ ! -f ".env" ]; then
    if [ -f "env.example.txt" ]; then
        cp env.example.txt .env
        echo -e "${GREEN}已从示例文件创建.env，请编辑.env文件配置数据库等信息${NC}"
        echo -e "${YELLOW}⚠️  重要：请修改SECRET_KEY为强随机字符串！${NC}"
    else
        echo -e "${YELLOW}警告: 未找到env.example.txt，请手动创建.env文件${NC}"
    fi
else
    echo -e "${GREEN}.env文件已存在${NC}"
fi

# 6. 运行数据库迁移（如果需要）
echo -e "${YELLOW}[6/8] 运行数据库迁移...${NC}"
cd backend
if [ -f "migrations/migrate_add_whitelist_blacklist_ips.py" ]; then
    python migrations/migrate_add_whitelist_blacklist_ips.py || echo -e "${YELLOW}迁移脚本执行失败或已执行过${NC}"
fi
cd ..

# 7. 创建管理员用户（可选）
echo -e "${YELLOW}[7/8] 创建管理员用户...${NC}"
read -p "是否创建管理员用户？(y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd backend
    python scripts/create_admin.py || echo -e "${YELLOW}创建管理员用户失败或用户已存在${NC}"
    cd ..
fi

# 8. 创建systemd服务文件（可选）
echo -e "${YELLOW}[8/8] 创建systemd服务...${NC}"
read -p "是否创建systemd服务？(y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    SERVICE_NAME="table-service"
    WORK_DIR=$(pwd)
    USER_NAME=$(whoami)
    
    sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=Table Service API
After=network.target

[Service]
Type=simple
User=${USER_NAME}
WorkingDirectory=${WORK_DIR}/backend
Environment="PATH=${WORK_DIR}/venv/bin"
ExecStart=${WORK_DIR}/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8888
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    echo -e "${GREEN}systemd服务已创建${NC}"
    echo -e "${YELLOW}使用以下命令管理服务:${NC}"
    echo "  启动: sudo systemctl start ${SERVICE_NAME}"
    echo "  停止: sudo systemctl stop ${SERVICE_NAME}"
    echo "  状态: sudo systemctl status ${SERVICE_NAME}"
    echo "  开机自启: sudo systemctl enable ${SERVICE_NAME}"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "部署完成！"
echo "==========================================${NC}"
echo ""
echo "下一步："
echo "1. 编辑 .env 文件配置数据库连接信息"
echo "   ⚠️  重要：修改SECRET_KEY为强随机字符串！"
echo "2. 运行数据库迁移脚本（如果需要）"
echo "3. 启动服务:"
echo "   cd backend"
echo "   ./start.sh"
echo "   或使用systemd: sudo systemctl start table-service"
echo ""
echo "前端部署："
echo "1. cd frontend"
echo "2. npm install"
echo "3. npm run build"
echo "4. 将dist目录部署到nginx或其他Web服务器"
echo ""
echo "API访问地址: http://your-server-ip:8888"
echo "API文档: http://your-server-ip:8888/docs"
echo ""
