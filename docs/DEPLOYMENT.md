# 部署文档

## 概述

本文档详细说明如何部署和配置"表转接口服务 + 智能问数系统"。

## 系统架构

```
┌─────────────┐
│   Nginx     │  (反向代理，可选)
└──────┬──────┘
       │
       ├──────────────┬──────────────┐
       │              │              │
┌──────▼──────┐ ┌────▼─────┐ ┌─────▼─────┐
│  前端服务    │ │ 后端服务   │ │  MySQL    │
│  (Vite)     │ │ (FastAPI) │ │ 数据库     │
│  Port:3003  │ │ Port:8300 │ │ Port:3306 │
└─────────────┘ └───────────┘ └───────────┘
                       │
                       ├──────────────┐
                       │              │
                  ┌────▼─────┐  ┌────▼─────┐
                  │  Redis   │  │  目标    │
                  │ 缓存服务  │  │ 数据库    │
                  │ Port:6379│  │ (多种)   │
                  └──────────┘  └──────────┘
```

## 环境要求

### 服务器要求

- **操作系统**: Linux (推荐 Ubuntu 20.04+ / CentOS 7+)
- **CPU**: 2核心以上
- **内存**: 4GB以上（推荐8GB）
- **磁盘**: 20GB以上可用空间
- **网络**: 可访问目标数据库和AI模型API

### 软件要求

- **Python**: 3.11+
- **Node.js**: 16+ (推荐18+)
- **MySQL**: 8.0+ (用于系统自身数据存储)
- **Redis**: 5.0+ (可选，用于缓存)
- **Nginx**: 1.18+ (可选，用于反向代理)

## 部署步骤

### 1. 准备服务器环境

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
# 或
sudo yum update -y  # CentOS/RHEL

# 安装基础工具
sudo apt install -y git curl wget vim  # Ubuntu/Debian
# 或
sudo yum install -y git curl wget vim  # CentOS/RHEL
```

### 2. 安装Python 3.11+

```bash
# Ubuntu/Debian
sudo apt install -y python3.11 python3.11-venv python3-pip

# CentOS/RHEL
sudo yum install -y python311 python311-pip
```

### 3. 安装Node.js

```bash
# 使用NodeSource仓库安装Node.js 18
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -  # CentOS
# 或
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo bash -  # Ubuntu
sudo apt install -y nodejs  # Ubuntu
sudo yum install -y nodejs  # CentOS
```

### 4. 安装MySQL

```bash
# Ubuntu/Debian
sudo apt install -y mysql-server
sudo systemctl start mysql
sudo systemctl enable mysql

# CentOS/RHEL
sudo yum install -y mysql-server
sudo systemctl start mysqld
sudo systemctl enable mysqld
```

### 5. 安装Redis (可选，推荐)

```bash
# Ubuntu/Debian
sudo apt install -y redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server

# CentOS/RHEL
sudo yum install -y redis
sudo systemctl start redis
sudo systemctl enable redis
```

### 6. 部署应用

```bash
# 1. 克隆项目
cd /opt
sudo git clone https://github.com/your-repo/table_to_service.git
sudo chown -R $USER:$USER table_to_service
cd table_to_service

# 2. 配置环境变量
cp env.example .env
vim .env  # 编辑配置文件

# 3. 安装后端依赖
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. 初始化数据库
python scripts/create_admin.py

# 5. 安装前端依赖
cd ../frontend
npm install

# 6. 构建前端
npm run build
```

### 7. 配置环境变量

编辑 `.env` 文件：

```bash
# 本地数据库配置（用于服务自身数据存储）
LOCAL_DB_HOST=localhost
LOCAL_DB_PORT=3306
LOCAL_DB_USER=your_user
LOCAL_DB_PASSWORD=your_password
LOCAL_DB_NAME=local_service

# 安全配置
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Redis配置（可选）
REDIS_URL=redis://127.0.0.1:6379/0
# REDIS_PASSWORD=your_redis_password
# REDIS_DB=0
# CACHE_TTL=3600

# API服务器配置
API_SERVER_SCHEME=http
API_SERVER_HOST=0.0.0.0
API_SERVER_PORT=8300

# CORS配置
ALLOWED_ORIGINS=http://localhost:3003,http://your-domain.com

# AI模型配置（根据使用的模型填写）
# DEEPSEEK_API_KEY=your_deepseek_api_key
# KIMI_API_KEY=your_kimi_api_key
# QWEN_API_KEY=your_qwen_api_key
```

### 8. 启动服务

#### 方式1：使用服务管理脚本（推荐）

```bash
cd /opt/table_to_service
chmod +x s
./s start    # 启动服务
./s stop     # 停止服务
./s restart  # 重启服务
./s status   # 查看状态
```

#### 方式2：手动启动

```bash
# 启动后端
cd /opt/table_to_service/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8300 &

# 启动前端（开发模式）
cd /opt/table_to_service/frontend
npm run dev &

# 或使用生产模式（需要先构建）
npm run build
npm run preview &
```

### 9. 配置Nginx反向代理（可选）

创建Nginx配置文件 `/etc/nginx/sites-available/table_to_service`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /opt/table_to_service/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端API代理
    location /api {
        proxy_pass http://127.0.0.1:8300;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket支持（如需要）
    location /ws {
        proxy_pass http://127.0.0.1:8300;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/table_to_service /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 10. 配置防火墙

```bash
# 开放端口
sudo ufw allow 3003/tcp  # 前端（如果直接访问）
sudo ufw allow 8300/tcp  # 后端API
sudo ufw allow 80/tcp    # HTTP（如果使用Nginx）
sudo ufw allow 443/tcp   # HTTPS（如果使用SSL）
```

## 系统服务配置（Systemd）

### 创建后端服务

创建文件 `/etc/systemd/system/table-to-service-backend.service`:

```ini
[Unit]
Description=Table to Service Backend API
After=network.target mysql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/table_to_service/backend
Environment="PATH=/opt/table_to_service/backend/venv/bin"
ExecStart=/opt/table_to_service/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8300
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 创建前端服务（如果需要）

创建文件 `/etc/systemd/system/table-to-service-frontend.service`:

```ini
[Unit]
Description=Table to Service Frontend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/table_to_service/frontend
ExecStart=/usr/bin/npm run preview
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable table-to-service-backend
sudo systemctl start table-to-service-backend
sudo systemctl status table-to-service-backend
```

## Docker部署（可选）

### 使用Docker Compose

项目包含 `docker-compose.yml` 文件，可以使用Docker部署：

```bash
# 构建和启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 性能优化

### 1. 启用Redis缓存（推荐）

#### 安装Redis

```bash
# Ubuntu/Debian
sudo apt install -y redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server

# CentOS/RHEL
sudo yum install -y redis
sudo systemctl start redis
sudo systemctl enable redis
```

#### 配置Redis（生产环境）

编辑 `/etc/redis/redis.conf`:

```bash
# 设置密码（生产环境必须）
requirepass your_strong_password_here

# 设置最大内存（根据服务器内存调整）
maxmemory 2gb
maxmemory-policy allkeys-lru

# 重启Redis
sudo systemctl restart redis
```

#### 在 `.env` 中配置Redis

```bash
REDIS_URL=redis://:your_strong_password@127.0.0.1:6379/0
REDIS_PASSWORD=your_strong_password
REDIS_DB=0
CACHE_TTL=3600  # 缓存过期时间（秒，默认1小时）
```

#### 验证Redis连接

```bash
# 测试连接
redis-cli -a your_strong_password ping
# 应该返回: PONG

# 或在Python中测试
python -c "import redis; r=redis.from_url('redis://:your_strong_password@127.0.0.1:6379/0'); print(r.ping())"
```

**注意**: 如果Redis不可用，系统会自动降级到内存缓存（单进程场景可用）。

### 2. 数据库连接池优化

#### 环境变量配置

在 `.env` 文件中配置连接池参数：

```bash
# 目标数据库连接池配置（用于表转服务）
DB_POOL_SIZE=10          # 连接池大小（默认10）
DB_MAX_OVERFLOW=20       # 最大溢出连接数（默认20）
DB_POOL_RECYCLE=3600     # 连接回收时间（秒，默认1小时）

# 本地数据库连接池配置（用于系统自身数据存储）
LOCAL_DB_POOL_SIZE=5     # 本地数据库连接池大小（默认5）
LOCAL_DB_MAX_OVERFLOW=10 # 本地数据库最大溢出连接数（默认10）
```

#### 推荐配置

**高并发场景**:
```bash
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
LOCAL_DB_POOL_SIZE=10
LOCAL_DB_MAX_OVERFLOW=20
```

**低并发场景**:
```bash
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
LOCAL_DB_POOL_SIZE=3
LOCAL_DB_MAX_OVERFLOW=5
```

### 3. 前端代码分割

已配置Vite的代码分割，生产构建会自动优化：

```bash
cd frontend
npm run build
```

### 4. 日志配置优化

日志配置已在 `backend/app/main.py` 中自动配置：

- **应用日志**: `backend/logs/app_YYYY-MM-DD.log`
  - 轮转: 每天午夜
  - 保留: 30天
  - 压缩: 自动压缩为zip

- **错误日志**: `backend/logs/error_YYYY-MM-DD.log`
  - 轮转: 每天午夜
  - 保留: 90天
  - 压缩: 自动压缩为zip

无需额外配置，系统会自动管理日志文件。

## 监控和日志

### 日志位置

- **应用日志**: `/opt/table_to_service/backend/logs/app_YYYY-MM-DD.log`
- **错误日志**: `/opt/table_to_service/backend/logs/error_YYYY-MM-DD.log`
- **系统日志**: `journalctl -u table-to-service-backend`

### 查看日志

```bash
# 应用日志（实时）
tail -f /opt/table_to_service/backend/logs/app_$(date +%Y-%m-%d).log

# 错误日志（实时）
tail -f /opt/table_to_service/backend/logs/error_$(date +%Y-%m-%d).log

# 系统服务日志
sudo journalctl -u table-to-service-backend -f

# 查看今日错误数量
grep -c "ERROR" /opt/table_to_service/backend/logs/error_$(date +%Y-%m-%d).log
```

### 错误日志监控（推荐配置）

#### 方案1: 简单监控脚本

创建监控脚本 `/opt/table_to_service/backend/scripts/monitor_errors.sh`:

```bash
#!/bin/bash
ERROR_LOG="/opt/table_to_service/backend/logs/error_$(date +%Y-%m-%d).log"
THRESHOLD=10  # 错误阈值

if [ -f "$ERROR_LOG" ]; then
    ERROR_COUNT=$(grep -c "ERROR" "$ERROR_LOG" 2>/dev/null || echo "0")
    if [ "$ERROR_COUNT" -gt "$THRESHOLD" ]; then
        echo "警告: 今日错误日志超过阈值 ($ERROR_COUNT > $THRESHOLD)"
        # 可以在这里添加告警逻辑（邮件、Slack、企业微信等）
    fi
fi
```

添加到crontab（每小时检查一次）:

```bash
chmod +x /opt/table_to_service/backend/scripts/monitor_errors.sh
crontab -e
# 添加: 0 * * * * /opt/table_to_service/backend/scripts/monitor_errors.sh
```

#### 方案2: 集成监控系统（推荐生产环境）

- **Prometheus + Grafana**: 收集日志指标，可视化监控
- **ELK Stack**: Elasticsearch + Logstash + Kibana
- **Sentry**: 错误追踪和告警

### 审计日志

系统支持审计日志功能，记录所有接口执行情况：

1. **启用审计日志**: 在接口配置中勾选"启用审计日志"
2. **查看审计日志**: 审计日志保存在 `audit_logs` 表中
3. **日志内容**: 包括请求参数、响应数据、执行时间、用户ID、客户端IP等

**建议**:
- 定期清理旧审计日志（保留90天）
- 配置审计日志备份策略
- 监控异常访问模式

## 备份和恢复

### 数据库备份

```bash
# 备份系统数据库
mysqldump -u your_user -p local_service > backup_$(date +%Y%m%d).sql

# 恢复
mysql -u your_user -p local_service < backup_20250101.sql
```

### 配置文件备份

```bash
# 备份配置文件
tar -czf config_backup_$(date +%Y%m%d).tar.gz .env backend/app/core/config.py
```

## 故障排查

### 常见问题

1. **端口被占用**
   ```bash
   # 检查端口占用
   sudo netstat -tlnp | grep 8300
   sudo lsof -i :8300
   ```

2. **数据库连接失败**
   - 检查数据库服务是否运行
   - 检查 `.env` 中的数据库配置
   - 检查防火墙设置

3. **前端无法访问后端**
   - 检查CORS配置
   - 检查Nginx代理配置
   - 检查后端服务是否运行

4. **Redis连接失败**
   - 检查Redis服务是否运行
   - 检查Redis配置
   - 系统会自动降级到内存缓存

## 安全建议

1. **修改默认密码**: 首次登录后立即修改管理员密码
2. **使用HTTPS**: 生产环境建议配置SSL证书
3. **限制访问**: 使用防火墙限制数据库端口访问
4. **定期更新**: 定期更新系统和依赖包
5. **备份数据**: 定期备份数据库和配置文件

## 测试验证

### 运行单元测试

```bash
cd /opt/table_to_service/backend
source venv/bin/activate

# 运行所有测试
pytest tests/ -v

# 运行SQL注入防护测试
pytest tests/test_sql_injection_protection.py -v

# 运行资源管理测试
pytest tests/test_resource_management.py -v

# 生成测试报告
pytest tests/ --html=report.html --self-contained-html
```

### 压力测试（可选）

#### 使用Apache Bench

```bash
# 安装
sudo yum install httpd-tools -y  # CentOS
sudo apt install apache2-utils -y  # Ubuntu

# 获取Token（先登录）
TOKEN=$(curl -X POST http://localhost:8300/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq -r '.access_token')

# 压力测试（1000请求，10并发）
ab -n 1000 -c 10 -H "Authorization: Bearer $TOKEN" \
   http://localhost:8300/api/v1/interfaces/1/execute
```

#### 使用wrk

```bash
# 安装
sudo yum install wrk -y  # CentOS
sudo apt install wrk -y  # Ubuntu

# 压力测试（4线程，100连接，持续30秒）
wrk -t4 -c100 -d30s -H "Authorization: Bearer $TOKEN" \
    http://localhost:8300/api/v1/interfaces/1/execute
```

### SQL注入防护验证

系统已实现SQL注入防护机制，所有测试用例已通过：

```bash
# 运行SQL注入防护测试
pytest tests/test_sql_injection_protection.py -v

# 预期结果: 5个测试全部通过
```

## 更新部署

```bash
# 1. 备份当前版本
cp -r /opt/table_to_service /opt/table_to_service_backup

# 2. 拉取最新代码
cd /opt/table_to_service
git pull

# 3. 更新依赖
cd backend
source venv/bin/activate
pip install -r requirements.txt

cd ../frontend
npm install
npm run build

# 4. 运行测试（推荐）
cd ../backend
pytest tests/ -v

# 5. 重启服务
cd ..
./s restart
```

## 联系支持

如遇到问题，请查看：
- [用户手册](USER_MANUAL.md)
- [管理员手册](ADMIN_MANUAL.md)
- [SQL注入防护文档](SQL_INJECTION_PROTECTION.md)
