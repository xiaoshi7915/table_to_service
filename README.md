# 表转服务系统

一个基于 FastAPI + Vue 3 的数据表转接口服务系统，支持将数据库表快速转换为 RESTful API 接口。

## 功能特性

- 🔐 **用户认证**：JWT Token 认证机制
- 🗄️ **数据库管理**：支持配置多个数据库连接
- 📊 **表转接口**：专家模式和图形模式两种配置方式
- 🔍 **SQL解析**：自动解析SQL参数，生成接口文档
- 🛡️ **风险管控**：支持白名单、黑名单、限流、审计日志等
- 📝 **接口文档**：自动生成API文档和示例数据
- 🎨 **现代化UI**：基于 Element Plus 的美观界面

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

# 2. 运行一键部署脚本
chmod +x deploy.sh
./deploy.sh

# 3. 配置环境变量
cp env.example.txt .env
# 编辑 .env 文件，配置数据库连接等信息

# 4. 运行数据库迁移（如果需要）
python migrate_add_whitelist_blacklist_ips.py

# 5. 启动服务
./start.sh
```

### 手动部署

#### 后端部署

```bash
# 1. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp env.example.txt .env
# 编辑 .env 文件

# 4. 运行数据库迁移
python migrate_add_whitelist_blacklist_ips.py

# 5. 启动服务
uvicorn main:app --host 0.0.0.0 --port 5001 --reload
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
LOCAL_DB_NAME=table_service

# JWT密钥
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256

# 服务配置
API_HOST=0.0.0.0
API_PORT=5001
DEBUG=False
```

## 项目结构

```
local_service/
├── routers/              # API路由
│   ├── auth.py          # 认证相关
│   ├── database_configs.py  # 数据库配置管理
│   ├── interface_configs.py  # 接口配置管理
│   └── interface_executor.py # 接口执行
├── frontend/            # 前端项目
│   ├── src/
│   │   ├── views/      # 页面组件
│   │   ├── router/     # 路由配置
│   │   └── api/        # API调用
│   └── package.json
├── models.py           # 数据模型
├── database.py         # 数据库连接
├── config.py           # 配置管理
├── main.py             # 应用入口
├── requirements.txt    # Python依赖
├── deploy.sh           # 一键部署脚本
└── README.md           # 项目说明
```

## API文档

启动服务后，访问以下地址查看API文档：

- Swagger UI: http://localhost:5001/docs
- ReDoc: http://localhost:5001/redoc

## 使用说明

1. **注册/登录**：首次使用需要注册管理员账号
2. **配置数据库**：在"数据库配置"页面添加要连接的数据库
3. **创建接口**：在"数据表转接口"页面创建接口配置
   - 专家模式：直接编写SQL语句
   - 图形模式：通过可视化界面选择表和字段
4. **管理接口**：在"接口清单"页面查看、编辑、执行、删除接口
5. **查看文档**：在"API文档"页面查看自动生成的接口文档

## 常见问题

### 数据库连接失败

- 检查数据库配置是否正确
- 确认数据库服务是否启动
- 检查防火墙和IP白名单设置

### 前端无法连接后端

- 检查后端服务是否启动
- 确认前端API配置中的后端地址是否正确
- 检查CORS配置

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
