# 智能问数 + 服务平台

一个基于 FastAPI + Vue 3 的数据表转接口服务系统，支持将数据库表快速转换为 RESTful API 接口，并提供基于大模型+RAG的智能问数功能。

## 🎯 核心目标

### 目标1：数据源表转接口服务
将多种数据源的表快速转换为RESTful API接口，支持专家模式和图形模式两种配置方式。

### 目标2：智能问数功能
基于大模型与RAG技术，将"业务人员的一句话"自动转换为"可执行SQL + 可视化图表"，让不懂SQL的人也能直接开口问数。

## ✨ 功能特性

### 数据表转接口服务
- 🔐 **用户认证**：JWT Token 认证机制
- 🗄️ **多数据源支持**：支持MySQL、PostgreSQL、SQLite、SQL Server、Oracle等多种数据库
- 📊 **表转接口**：专家模式和图形模式两种配置方式
- 🔍 **SQL解析**：自动解析SQL参数，生成接口文档
- 🛡️ **风险管控**：支持白名单、黑名单、限流、审计日志等
- 📝 **接口文档**：自动生成API文档和示例数据
- 🎨 **现代化UI**：基于 Element Plus 的美观界面
- 🔒 **安全防护**：SQL注入防护、输入验证、访问控制

### 智能问数功能 ✅ 已完成
- ✅ **自然语言提问**：无需SQL基础，可直接用自然语言提问
- ✅ **智能推荐**：【猜你想问】功能提供智能推荐，降低提问门槛
- ✅ **图表自动生成**：根据问题意图智能选择合适图表类型（柱状图、折线图、饼图、散点图、面积图、表格等）
- ✅ **图表管理**：支持图表类型切换、放大、导出为图片（PNG），或添加至仪表板
- ✅ **数据明细**：所有图表支持查看数据明细与导出（Excel、CSV、JSON、XML）
- ✅ **SQL可见**：每次问数均自动生成对应SQL查询语句，支持查看与复制
- ✅ **多轮对话**：支持连续提问，自动记忆上下文，实现更自然的分析过程
- ✅ **历史对话**：支持查看、重命名、搜索、删除过往对话，便于复用与追溯分析
- ✅ **知识库配置**：支持AI模型配置、术语配置、SQL示例配置、自定义提示词、业务知识库管理
- ✅ **仪表板**：支持将查询结果添加到仪表板，进行数据大屏展示
- ✅ **问数模式接口**：从问数结果一键生成服务接口，支持问数模式接口配置

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Node.js 16+
- MySQL 8.0+

### 快速安装

```bash
# 1. 克隆项目
git clone https://github.com/xiaoshi7915/table_to_service.git
cd table_to_service

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置数据库连接等信息

# 3. 安装后端依赖
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. 初始化数据库
python scripts/create_admin.py

# 5. 安装前端依赖
cd ../frontend
npm install

# 6. 启动服务
cd ..
./s start
```

详细安装说明请参考 [部署文档](docs/DEPLOYMENT.md)

## 📖 使用说明

### 1. 登录系统

访问 http://121.36.205.70:3003，使用默认管理员账号登录：
- 用户名：`admin`
- 密码：`admin123`

⚠️ **首次登录后请立即修改密码！**

### 2. 配置数据源

在"数据源配置"页面添加要连接的数据库连接信息。

**支持的数据库类型**：
- MySQL / MariaDB
- PostgreSQL
- SQLite
- SQL Server
- Oracle

选择数据库类型后，系统会自动调整连接参数和默认端口。

### 3. 创建接口

在"数据表转接口"页面创建接口配置：
- **专家模式**：直接编写SQL语句
- **图形模式**：通过可视化界面选择表和字段

### 4. 管理接口

在"接口清单"页面可以：
- 查看接口详情
- 执行接口测试
- 查看API文档
- 编辑或删除接口

### 5. 查看文档

在"API文档"页面查看自动生成的接口文档，包括：
- 接口URL
- 请求参数
- 响应示例
- cURL示例

## 🛠️ 服务管理

项目提供了便捷的服务管理脚本：

```bash
# 快捷命令（推荐）
./s start      # 启动所有服务
./s stop       # 停止所有服务
./s restart    # 重启所有服务
./s status     # 查看服务状态
```

详细说明请参考 [服务管理说明.md](服务管理说明.md)

## 🌐 访问地址

- **前端界面**: http://121.36.205.70:3003
- **后端API**: http://121.36.205.70:8300
- **API文档**: http://121.36.205.70:8300/docs
- **API代理**: http://121.36.205.70:50052（通过Nginx反向代理）

## 📁 项目结构

```
table_to_service/
├── backend/              # 后端代码（FastAPI）
│   ├── app/             # 应用主目录
│   │   ├── main.py      # FastAPI应用入口
│   │   ├── api/v1/      # API路由
│   │   ├── core/        # 核心模块
│   │   └── ...
│   ├── scripts/         # 脚本文件
│   └── requirements.txt # Python依赖
├── frontend/            # 前端代码（Vue 3）
│   ├── src/            # 源代码
│   └── package.json    # Node.js依赖
├── logs/               # 日志目录
├── .env                # 环境变量配置
├── service_manager.sh  # 服务管理脚本
└── README.md           # 本文件
```

## 🔧 技术栈

### 后端
- Python 3.11+
- FastAPI
- SQLAlchemy
- 多数据库支持：MySQL、PostgreSQL、SQLite、SQL Server、Oracle
- JWT认证
- 密码加密（Fernet）
- **智能问数**：OpenAI / 通义千问 / 本地LLM模型
- **RAG增强**：知识库检索、提示词优化

### 前端
- Vue 3
- Element Plus
- Vite（已配置代码分割和懒加载优化）
- Pinia
- **图表库**：ECharts（智能问数功能）
- **代码编辑器**：Monaco Editor（SQL编辑）
- **性能优化**：代码分割、懒加载、资源压缩

## 🔒 安全特性

- ✅ **SQL注入防护**：参数化查询、标识符转义、危险关键字检测
- ✅ **JWT Token认证**：安全的用户认证机制
- ✅ **密码加密**：bcrypt哈希存储，Fernet加密传输
- ✅ **访问控制**：IP白名单/黑名单、接口权限控制
- ✅ **接口限流**：防止API滥用
- ✅ **审计日志**：记录所有关键操作（SQL执行、接口调用等）
- ✅ **输入验证**：严格的参数验证和类型检查
- ✅ **CORS配置**：跨域请求安全控制
- ✅ **数据脱敏**：支持敏感数据脱敏功能


## 📚 文档

### 用户文档 
- [用户使用手册](docs/USER_MANUAL.md) - 用户操作指南
- [管理员配置手册](docs/ADMIN_MANUAL.md) - 系统配置和管理指南
- [API文档](http://121.36.205.70:8300/docs) - 在线API文档（Swagger UI）

### 技术文档
- [技术架构文档](docs/TECHNICAL_ARCHITECTURE.md) - 项目技术架构详解
- [SQL元数据检索流程](docs/SQL_METADATA_RETRIEVAL_FLOW.md) - SQL元数据检索实现详解



## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 👤 作者

mr stone

Copyright © 2025 mr stone的个人网站
