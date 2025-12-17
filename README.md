# 表转服务系统

一个基于 FastAPI + Vue 3 的数据表转接口服务系统，支持将数据库表快速转换为 RESTful API 接口。

## 功能特性

- 🔐 **用户认证**：JWT Token 认证机制
- 🗄️ **数据源管理**：支持配置多个数据库连接
- 📊 **表转接口**：专家模式和图形模式两种配置方式
- 🔍 **SQL解析**：自动解析SQL参数，生成接口文档
- 🛡️ **风险管控**：支持白名单、黑名单、限流、审计日志等
- 📝 **接口文档**：自动生成API文档和示例数据
- 🎨 **现代化UI**：基于 Element Plus 的美观界面
- 🔒 **安全防护**：SQL注入防护、输入验证、访问控制

## 技术栈

### 后端
- Python 3.11+
- FastAPI
- SQLAlchemy
- MySQL 8.0
- JWT认证

### 前端
- Vue 3
- Element Plus
- Vite
- Pinia

## 项目结构

```
local_service/
├── backend/              # 后端代码（前后端分离）
│   ├── app/             # 应用主目录
│   │   ├── main.py      # FastAPI应用入口
│   │   ├── models.py    # 数据模型
│   │   ├── schemas.py   # Pydantic模式
│   │   ├── api/v1/      # API路由
│   │   ├── core/        # 核心模块（config, database, security）
│   │   └── utils/       # 工具函数
│   ├── migrations/      # 数据库迁移脚本
│   ├── scripts/         # 脚本文件
│   ├── requirements.txt # Python依赖
│   ├── start.sh         # Linux启动脚本
│   └── start.bat        # Windows启动脚本
├── frontend/            # 前端项目
│   ├── src/
│   │   ├── views/      # 页面组件
│   │   ├── router/     # 路由配置
│   │   └── api/        # API调用
│   └── package.json
├── deploy.sh           # 一键部署脚本
├── docker-compose.yml # Docker编排文件
├── Dockerfile         # Docker镜像文件
├── SECURITY.md        # 安全说明文档
└── README.md          # 本文件
```

## 快速开始

### 环境要求

- Python 3.11 或更高版本
- MySQL 8.0 或更高版本
- Node.js 16+ 和 npm（前端开发）

### 一键部署（Linux云服务器）

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd local_service

# 2. 配置环境变量
cp env.example.txt .env
# 编辑 .env 文件，配置数据库连接等信息
# ⚠️ 重要：修改SECRET_KEY为强随机字符串

# 3. 运行一键部署脚本
chmod +x deploy.sh
./deploy.sh

# 4. 运行数据库迁移（如果需要）
cd backend
python migrations/migrate_add_whitelist_blacklist_ips.py

# 5. 创建管理员用户
python scripts/create_admin.py

# 6. 启动服务
./start.sh
```

### 手动部署

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
# ⚠️ 重要：修改SECRET_KEY为强随机字符串

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

### 使用 systemd 管理服务（推荐）

```bash
# 创建服务文件
sudo nano /etc/systemd/system/table-service.service

# 内容参考 deploy.sh 脚本中的配置

# 启动服务
sudo systemctl start table-service

# 设置开机自启
sudo systemctl enable table-service

# 查看状态
sudo systemctl status table-service
```

## 配置说明

### 环境变量 (.env)

```env
# 数据库配置
LOCAL_DB_HOST=localhost
LOCAL_DB_PORT=3306
LOCAL_DB_USER=root
LOCAL_DB_PASSWORD=your_password
LOCAL_DB_NAME=local_service_db

# 目标数据库配置（可选）
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=target_db

# JWT密钥（⚠️ 生产环境必须修改！）
SECRET_KEY=your-strong-random-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 服务配置
API_HOST=0.0.0.0
API_PORT=8888
DEBUG=False

# CORS配置（生产环境应限制）
ALLOWED_ORIGINS=*
```

### 安全配置

⚠️ **重要安全提示**：

1. **SECRET_KEY**：生产环境必须修改为强随机字符串（至少32字符）
2. **数据库密码**：使用强密码，不要使用默认密码
3. **CORS配置**：生产环境应限制允许的源，不要使用 `*`
4. **HTTPS**：生产环境必须使用HTTPS

详细安全说明请参考 [SECURITY.md](SECURITY.md)

## API文档

启动服务后，访问以下地址查看API文档：

- Swagger UI: http://localhost:8888/docs
- ReDoc: http://localhost:8888/redoc

## 使用说明

1. **注册/登录**：首次使用需要注册管理员账号或使用 `create_admin.py` 创建
2. **配置数据源**：在"数据源配置"页面添加要连接的数据库
3. **创建接口**：在"接口配置"页面创建接口配置
   - 专家模式：直接编写SQL语句
   - 图形模式：通过可视化界面选择表和字段
4. **管理接口**：在"接口清单"页面查看、编辑、执行、删除接口
5. **查看文档**：在"API文档"页面查看自动生成的接口文档

## 安全特性

- ✅ SQL注入防护（参数转义、标识符转义）
- ✅ JWT Token认证
- ✅ 密码bcrypt哈希
- ✅ IP白名单/黑名单
- ✅ 接口限流
- ✅ 审计日志
- ✅ 输入验证
- ✅ CORS配置

详细安全说明请参考 [SECURITY.md](SECURITY.md)

## 常见问题

### 数据库连接失败

- 检查数据库配置是否正确
- 确认数据库服务是否启动
- 检查防火墙和IP白名单设置

### 前端无法连接后端

- 检查后端服务是否启动
- 确认前端API配置中的后端地址是否正确（默认：http://localhost:8888）
- 检查CORS配置

### 启动报错

- 检查Python版本（需要3.11+）
- 检查依赖是否安装完整：`pip install -r backend/requirements.txt`
- 检查.env文件配置是否正确

## 开发说明

### 后端开发

- 后端代码位于 `backend/` 目录
- 使用FastAPI框架
- API路径前缀：`/api/v1`
- 详细说明请参考 `backend/README.md`

### 前端开发

- 前端代码位于 `frontend/` 目录
- 使用Vue 3 + Vite
- API调用配置在 `frontend/src/api/index.js`

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v1.0.0 (2025-12-18)
- ✅ 前后端分离架构重构
- ✅ 后端代码迁移到 `backend/` 目录
- ✅ 安全加固（SQL注入防护、输入验证）
- ✅ 代码安全审查和优化
