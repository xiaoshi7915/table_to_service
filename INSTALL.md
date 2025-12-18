# 表转接口服务 - 安装部署指南

## 项目简介

表转接口服务是一个基于 FastAPI + Vue 3 的数据表转接口服务系统，支持将数据库表快速转换为 RESTful API 接口。

## 功能特性

- 🔐 **用户认证**：JWT Token 认证机制
- 🗄️ **数据源管理**：支持配置多个数据库连接
- 📊 **表转接口**：专家模式和图形模式两种配置方式
- 🔍 **SQL解析**：自动解析SQL参数，生成接口文档
- 🛡️ **风险管控**：支持白名单、黑名单、限流、审计日志等
- 📝 **接口文档**：自动生成API文档和示例数据
- 🎨 **现代化UI**：基于 Element Plus 的美观界面
- 🔒 **安全防护**：SQL注入防护、输入验证、访问控制

## 系统要求

- **操作系统**：Linux (CentOS 7+, Ubuntu 18+, Debian 10+)
- **Python**：3.11 或更高版本
- **Node.js**：16+ 和 npm
- **MySQL**：8.0 或更高版本
- **内存**：建议至少 2GB
- **磁盘**：建议至少 10GB 可用空间

## 快速安装

### 1. 克隆项目

```bash
git clone https://github.com/xiaoshi7915/table_to_service.git
cd table_to_service
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp env.example .env

# 编辑环境变量文件
vi .env
```

**重要配置项**：

```env
# 数据库配置
LOCAL_DB_HOST=47.118.250.53
LOCAL_DB_PORT=3306
LOCAL_DB_USER=cxs_rds
LOCAL_DB_PASSWORD=4441326cxs!!
LOCAL_DB_NAME=local_service

# 安全配置（⚠️ 生产环境必须修改！）
SECRET_KEY=your-strong-random-secret-key-here-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 服务配置
API_HOST=0.0.0.0
API_PORT=8300
DEBUG=False

# CORS配置（前端地址）
ALLOWED_ORIGINS=http://localhost:3003,http://121.36.205.70:3003

# API服务地址配置（用于生成接口文档中的完整URL）
API_SERVER_HOST=121.36.205.70
API_SERVER_PORT=50052
API_SERVER_SCHEME=http
```

### 3. 安装后端依赖

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装Python依赖
pip install -r requirements.txt
```

### 4. 初始化数据库

```bash
# 创建管理员用户
python scripts/create_admin.py
```

**默认管理员账号**：
- 用户名：`admin`
- 密码：`admin123`

⚠️ **首次登录后请立即修改密码！**

### 5. 安装前端依赖

```bash
cd ../frontend

# 安装Node.js依赖
npm install
```

### 6. 启动服务

#### 方式一：使用服务管理脚本（推荐）

```bash
cd /opt/table_to_service

# 启动所有服务
./s start

# 查看服务状态
./s status

# 停止所有服务
./s stop

# 重启所有服务
./s restart
```

#### 方式二：手动启动

**启动后端**：
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8300 --reload
```

**启动前端**：
```bash
cd frontend
npm run dev
```

## 访问地址

### 本地访问
- **前端界面**: http://localhost:3003
- **后端API**: http://localhost:8300
- **API文档**: http://localhost:8300/docs

### 服务器访问（121.36.205.70）
- **前端界面**: http://121.36.205.70:3003
- **后端API**: http://121.36.205.70:8300
- **API文档**: http://121.36.205.70:8300/docs
- **API代理**: http://121.36.205.70:50052（通过Nginx反向代理）

## Nginx反向代理配置（可选）

如果需要通过50052端口访问后端服务，需要配置Nginx反向代理：

```bash
# 复制配置文件
sudo cp nginx_proxy.conf /etc/nginx/conf.d/table_to_service_proxy.conf

# 测试配置
sudo nginx -t

# 重载配置
sudo nginx -s reload
```

详细配置说明请参考 `配置nginx代理.md`

## 服务管理

### 使用服务管理脚本

项目提供了便捷的服务管理脚本 `service_manager.sh` 和快捷命令 `s`：

```bash
# 快捷命令（推荐）
./s start      # 启动所有服务
./s stop       # 停止所有服务
./s restart    # 重启所有服务
./s status     # 查看服务状态

# 完整命令
./service_manager.sh start-backend   # 仅启动后端
./service_manager.sh stop-backend    # 仅停止后端
./service_manager.sh start-frontend  # 仅启动前端
./service_manager.sh stop-frontend   # 仅停止前端
```

### 日志查看

```bash
# 查看后端日志
tail -f logs/backend.log

# 查看前端日志
tail -f logs/frontend.log
```

## 防火墙配置

确保防火墙开放必要端口：

```bash
# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8300/tcp
sudo firewall-cmd --permanent --add-port=3003/tcp
sudo firewall-cmd --permanent --add-port=50052/tcp
sudo firewall-cmd --reload

# Ubuntu/Debian
sudo ufw allow 8300/tcp
sudo ufw allow 3003/tcp
sudo ufw allow 50052/tcp
```

## 常见问题

### 1. 后端启动失败

**问题**：虚拟环境不存在
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**问题**：数据库连接失败
- 检查 `.env` 文件中的数据库配置
- 确认数据库服务器可访问
- 检查防火墙设置

**问题**：端口被占用
```bash
# 检查端口占用
netstat -tlnp | grep 8300
# 或修改 .env 中的 API_PORT
```

### 2. 前端启动失败

**问题**：依赖未安装
```bash
cd frontend
npm install
```

**问题**：端口被占用
- 修改 `frontend/vite.config.js` 中的端口配置

### 3. 服务无法访问

- 检查服务是否启动：`./s status`
- 检查防火墙设置
- 检查服务器安全组配置

## 安全建议

1. **修改SECRET_KEY**：生产环境必须修改为强随机字符串（至少32字符）
2. **修改默认密码**：首次登录后立即修改管理员密码
3. **限制CORS源**：不要使用 `*`，指定具体的前端域名
4. **使用HTTPS**：生产环境建议使用HTTPS
5. **数据库安全**：使用强密码，限制访问IP
6. **防火墙配置**：只开放必要的端口

详细安全说明请参考 `SECURITY.md`

## 项目结构

```
table_to_service/
├── backend/              # 后端代码（FastAPI）
│   ├── app/             # 应用主目录
│   │   ├── main.py      # FastAPI应用入口
│   │   ├── api/v1/      # API路由
│   │   ├── core/        # 核心模块
│   │   └── ...
│   ├── scripts/         # 脚本文件
│   ├── requirements.txt # Python依赖
│   └── venv/            # Python虚拟环境
├── frontend/            # 前端代码（Vue 3）
│   ├── src/            # 源代码
│   └── package.json    # Node.js依赖
├── logs/               # 日志目录
├── .env                # 环境变量配置
├── service_manager.sh  # 服务管理脚本
├── s                   # 快捷命令
├── nginx_proxy.conf    # Nginx配置示例
└── README.md           # 项目说明
```

## 技术支持

如有问题，请查看：
- 服务管理说明：`服务管理说明.md`
- Nginx配置说明：`配置nginx代理.md`
- 安全说明：`SECURITY.md`

## 更新日志

### v1.0.0 (2025-12-18)
- ✅ 前后端分离架构
- ✅ 服务管理脚本
- ✅ Nginx反向代理支持
- ✅ 安全加固

