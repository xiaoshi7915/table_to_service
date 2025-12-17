# MySQL表转服务 - 前端项目

## 技术栈

- **Vue 3** - 渐进式JavaScript框架
- **Vue Router** - 官方路由管理器
- **Pinia** - 状态管理
- **Element Plus** - Vue 3组件库
- **Axios** - HTTP客户端
- **Vite** - 构建工具

## 快速开始

### 安装依赖

```bash
cd frontend
npm install
```

### 开发模式

```bash
npm run dev
```

访问 http://localhost:3000

### 构建生产版本

```bash
npm run build
```

构建产物在 `dist` 目录

## 项目结构

```
frontend/
├── src/
│   ├── api/           # API接口
│   ├── components/    # 组件
│   ├── layouts/       # 布局
│   ├── router/        # 路由配置
│   ├── stores/        # 状态管理
│   ├── views/         # 页面
│   ├── App.vue        # 根组件
│   └── main.js        # 入口文件
├── index.html
├── package.json
└── vite.config.js
```

## 功能模块

1. **用户登录** - 登录认证
2. **仪表盘** - 数据统计和概览
3. **数据库配置** - 管理数据库连接配置
4. **表配置** - 配置表的服务选项
5. **API文档** - 生成和查看API文档

## 开发说明

### API代理

开发模式下，Vite会自动代理 `/api` 请求到后端服务器 `http://localhost:8000`

### 状态管理

使用Pinia进行状态管理，主要store：
- `auth` - 用户认证状态

### 路由守卫

已实现路由守卫，未登录用户会自动跳转到登录页

## 部署

构建后的静态文件可以：
1. 部署到Nginx等Web服务器
2. 使用FastAPI的静态文件服务（已配置）


