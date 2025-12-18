# 表转接口服务

一个基于 FastAPI + Vue 3 的数据表转接口服务系统，支持将数据库表快速转换为 RESTful API 接口。

## ✨ 功能特性

- 🔐 **用户认证**：JWT Token 认证机制
- 🗄️ **数据源管理**：支持配置多个数据库连接
- 📊 **表转接口**：专家模式和图形模式两种配置方式
- 🔍 **SQL解析**：自动解析SQL参数，生成接口文档
- 🛡️ **风险管控**：支持白名单、黑名单、限流、审计日志等
- 📝 **接口文档**：自动生成API文档和示例数据
- 🎨 **现代化UI**：基于 Element Plus 的美观界面
- 🔒 **安全防护**：SQL注入防护、输入验证、访问控制

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

详细安装说明请参考 [INSTALL.md](INSTALL.md)

## 📖 使用说明

### 1. 登录系统

访问 http://121.36.205.70:3003，使用默认管理员账号登录：
- 用户名：`admin`
- 密码：`admin123`

⚠️ **首次登录后请立即修改密码！**

### 2. 配置数据源

在"数据源配置"页面添加要连接的数据库连接信息。

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
- MySQL 8.0
- JWT认证

### 前端
- Vue 3
- Element Plus
- Vite
- Pinia

## 🔒 安全特性

- ✅ SQL注入防护（参数转义、标识符转义）
- ✅ JWT Token认证
- ✅ 密码bcrypt哈希
- ✅ IP白名单/黑名单
- ✅ 接口限流
- ✅ 审计日志
- ✅ 输入验证
- ✅ CORS配置

详细安全说明请参考 [SECURITY.md](SECURITY.md)

## 📚 文档

- [安装部署指南](INSTALL.md)
- [服务管理说明](服务管理说明.md)
- [Nginx配置说明](配置nginx代理.md)
- [安全说明](SECURITY.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 👤 作者

mr stone

Copyright © 2025 mr stone的个人网站
