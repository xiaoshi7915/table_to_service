# 部署说明文档

## 目录结构说明

项目已重构为前后端分离架构：

```
local_service/
├── backend/              # 后端代码（FastAPI）
│   ├── app/             # 应用主目录
│   │   ├── main.py     # FastAPI应用入口
│   │   ├── api/v1/     # API路由
│   │   ├── core/       # 核心模块
│   │   └── ...
│   ├── migrations/      # 数据库迁移脚本
│   ├── scripts/         # 脚本文件
│   ├── requirements.txt # Python依赖
│   ├── start.sh         # Linux启动脚本
│   └── start.bat        # Windows启动脚本
├── frontend/            # 前端代码（Vue 3）
├── Dockerfile          # Docker镜像文件
├── docker-compose.yml  # Docker编排文件
├── deploy.sh           # 一键部署脚本
└── .env                # 环境变量配置
```

## 部署方式

### 方式1：使用一键部署脚本（推荐）

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd local_service

# 2. 运行部署脚本
chmod +x deploy.sh
./deploy.sh

# 3. 配置环境变量
# 编辑 .env 文件，配置数据库连接等信息
# ⚠️ 重要：修改SECRET_KEY为强随机字符串！

# 4. 启动服务
cd backend
./start.sh
```

### 方式2：使用Docker Compose

```bash
# 1. 配置环境变量
cp env.example.txt .env
# 编辑 .env 文件

# 2. 构建并启动
docker-compose up -d

# 3. 查看日志
docker-compose logs -f api
```

### 方式3：手动部署

#### 后端部署

```bash
# 1. 进入backend目录
cd backend

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
# 在backend目录或项目根目录创建.env文件
cp ../env.example.txt .env
# 编辑 .env 文件

# 5. 运行数据库迁移
python migrations/migrate_add_whitelist_blacklist_ips.py

# 6. 创建管理员用户
python scripts/create_admin.py

# 7. 启动服务
# Linux/Mac
./start.sh

# Windows
start.bat

# 或直接使用uvicorn
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 前端部署

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 开发模式运行
npm run dev

# 4. 生产构建
npm run build
# 构建产物在 dist/ 目录
```

## 环境变量配置

### .env 文件位置

支持两种位置：
1. `backend/.env`（优先）
2. 项目根目录 `.env`

### 必需配置

```env
# 本地数据库配置（服务自身数据存储）
LOCAL_DB_HOST=localhost
LOCAL_DB_PORT=3306
LOCAL_DB_USER=root
LOCAL_DB_PASSWORD=your_password
LOCAL_DB_NAME=local_service_db

# JWT密钥（⚠️ 生产环境必须修改！）
SECRET_KEY=your-strong-random-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 服务配置
API_HOST=0.0.0.0
API_PORT=8888
DEBUG=False

# CORS配置（生产环境应限制）
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
```

## 使用systemd管理服务

```bash
# 创建服务文件
sudo nano /etc/systemd/system/table-service.service

# 内容：
[Unit]
Description=Table Service API
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/local_service/backend
Environment="PATH=/path/to/local_service/venv/bin"
ExecStart=/path/to/local_service/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8888
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# 启动服务
sudo systemctl daemon-reload
sudo systemctl start table-service
sudo systemctl enable table-service

# 查看状态
sudo systemctl status table-service
```

## Docker部署

### 构建镜像

```bash
docker build -t table-service:latest .
```

### 使用docker-compose

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f api

# 停止服务
docker-compose down

# 重启服务
docker-compose restart api
```

### Docker环境变量

可以通过环境变量或.env文件配置：

```bash
# 方式1：使用.env文件
docker-compose up -d

# 方式2：直接传递环境变量
docker-compose run -e LOCAL_DB_PASSWORD=your_password api
```

## 端口说明

- **后端API**：8888（可在.env中配置API_PORT）
- **MySQL数据库**：3306（docker-compose中）
- **前端开发服务器**：通常为5173（Vite默认）

## 常见问题

### 1. 启动报错：IndentationError

- 检查Python文件缩进是否正确
- 确保使用4个空格缩进，不要混用Tab和空格

### 2. 数据库连接失败

- 检查.env文件中的数据库配置
- 确认MySQL服务是否启动
- 检查防火墙和IP白名单

### 3. 模块导入错误

- 确保在backend目录下运行
- 检查虚拟环境是否激活
- 确认所有依赖已安装：`pip install -r backend/requirements.txt`

### 4. 端口被占用

- 检查8888端口是否被占用：`netstat -an | grep 8888`
- 修改.env中的API_PORT配置
- 或修改docker-compose.yml中的端口映射

## 安全建议

1. **修改SECRET_KEY**：生产环境必须修改为强随机字符串
2. **限制CORS源**：不要使用 `*`，指定具体的前端域名
3. **使用HTTPS**：生产环境必须使用HTTPS
4. **数据库安全**：使用强密码，限制访问IP
5. **防火墙配置**：只开放必要的端口

详细安全说明请参考 [SECURITY.md](SECURITY.md)

