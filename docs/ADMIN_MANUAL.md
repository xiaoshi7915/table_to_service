# 管理员配置手册

## 目录

1. [系统安装部署](#系统安装部署)
2. [系统配置](#系统配置)
3. [知识库配置](#知识库配置)
4. [安全配置](#安全配置)
5. [性能优化](#性能优化)
6. [监控和维护](#监控和维护)

---

## 系统安装部署

### 环境要求

- Python 3.11+
- Node.js 16+
- MySQL 8.0+
- Redis（可选，用于缓存）

### 安装步骤

详细安装说明请参考 [INSTALL.md](../INSTALL.md)

### 快速启动

```bash
# 使用服务管理脚本
./s start      # 启动所有服务
./s stop       # 停止所有服务
./s restart    # 重启所有服务
./s status     # 查看服务状态
```

---

## 系统配置

### 环境变量配置

编辑 `.env` 文件，配置以下参数：

```bash
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=test_db

# 本地数据库配置（服务自身数据存储）
LOCAL_DB_HOST=localhost
LOCAL_DB_PORT=3306
LOCAL_DB_USER=root
LOCAL_DB_PASSWORD=your_password
LOCAL_DB_NAME=local_service_db

# 安全配置
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 服务配置
API_HOST=127.0.0.1
API_PORT=5001
DEBUG=False

# Redis配置（可选）
REDIS_URL=redis://localhost:6379/0

# CORS配置
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
```

### 初始化数据库

```bash
cd backend
python scripts/create_admin.py
```

### 初始化AI模型

```bash
cd backend
python scripts/init_ai_models.py
```

---

## 知识库配置

### AI模型配置

1. 进入"AI模型配置"页面
2. 点击"添加模型"按钮
3. 配置模型信息：
   - **模型名称**：自定义名称（如：GPT-4、通义千问）
   - **提供商**：选择OpenAI、Alibaba（通义千问）、Kimi等
   - **API密钥**：提供商的API密钥（加密存储）
   - **API基础URL**：API服务地址（可选）
   - **模型名称**：具体模型名称（如：gpt-4、qwen-turbo）
   - **最大Token数**：单次请求最大token数
   - **温度参数**：控制生成随机性（0-1，默认0.7）
4. 点击"保存"
5. 可以设置默认模型（点击"设为默认"按钮）

**支持的提供商：**
- **OpenAI**：GPT-3.5、GPT-4等
- **Alibaba（通义千问）**：qwen-turbo、qwen-plus等
- **Kimi**：moonshot-v1-8k等

### 术语配置

术语库用于将业务术语映射到数据库字段，提升SQL生成准确性。

1. 进入"术语配置"页面
2. 点击"添加术语"按钮
3. 填写术语信息：
   - **业务术语**：用户常用的业务词汇（如：销售量、销售额）
   - **数据库字段**：对应的数据库字段名（如：sales_amount）
   - **表名**：所属表名（可选）
   - **描述**：术语说明（可选）
   - **分类**：术语分类（可选）
4. 点击"保存"

**批量导入：**
- 点击"批量导入"按钮
- 按格式输入术语（每行一个，格式：业务术语|数据库字段|表名|描述）
- 点击"导入"

### SQL示例配置

SQL示例库用于提供参考，帮助AI生成更准确的SQL。

1. 进入"SQL示例配置"页面
2. 点击"添加示例"按钮
3. 填写示例信息：
   - **标题**：示例标题
   - **问题**：对应的自然语言问题
   - **SQL语句**：SQL示例代码
   - **数据库类型**：MySQL、PostgreSQL等
   - **表名**：涉及的表名（可选）
   - **描述**：示例说明（可选）
   - **推荐图表类型**：柱状图、折线图等（可选）
4. 点击"保存"

### 自定义提示词配置

自定义提示词用于优化SQL生成效果。

1. 进入"自定义提示词"页面
2. 点击"添加提示词"按钮
3. 填写提示词信息：
   - **名称**：提示词名称
   - **类型**：sql_generation、data_analysis等
   - **内容**：提示词内容（支持Markdown）
   - **优先级**：数字越大优先级越高
   - **是否启用**：是否启用此提示词
4. 点击"保存"

### 业务知识库配置

业务知识库用于存储业务规则和知识，帮助AI理解业务场景。

1. 进入"业务知识库"页面
2. 点击"添加知识"按钮
3. 填写知识信息：
   - **标题**：知识标题
   - **内容**：知识内容（支持Markdown）
   - **分类**：知识分类（可选）
   - **标签**：知识标签，多个用逗号分隔（可选）
4. 点击"保存"

**搜索知识：**
- 使用关键词搜索
- 按分类筛选
- 按标签筛选

---

## 安全配置

### 密码安全

- 系统使用bcrypt哈希存储密码
- API密钥使用Fernet加密存储
- 生产环境请务必修改默认SECRET_KEY

### SQL注入防护

系统已实现多层SQL注入防护：
1. **参数化查询**：所有SQL使用参数化查询，防止SQL注入
2. **标识符转义**：表名、字段名自动转义
3. **危险关键字检测**：禁止生成DROP、DELETE等危险操作
4. **SQL注入模式检测**：检测常见的SQL注入攻击模式

### 访问控制

#### IP白名单/黑名单

在接口配置的"风险管控"步骤中：
- **IP白名单**：只允许白名单中的IP访问
- **IP黑名单**：禁止黑名单中的IP访问
- 支持CIDR格式（如：192.168.1.0/24）

#### 接口限流

在接口配置中设置：
- **启用限流**：是否启用接口限流
- **每分钟最大请求数**：限制每分钟的请求次数

#### 审计日志

在接口配置中启用审计日志，系统会记录：
- 接口调用记录
- SQL执行记录
- 用户操作记录
- 错误信息

查看审计日志：
- 日志文件：`backend/logs/app_YYYY-MM-DD.log`
- 数据库表：`audit_logs`（如果启用）

### CORS配置

在 `.env` 文件中配置允许的源：

```bash
ALLOWED_ORIGINS=http://localhost:3000,http://your-domain.com
```

---

## 性能优化

### SQL生成缓存

系统支持SQL生成结果缓存，提升性能：

1. **Redis缓存**（推荐）：
   - 安装Redis
   - 在 `.env` 中配置 `REDIS_URL=redis://localhost:6379/0`
   - 系统自动使用Redis作为缓存后端

2. **内存缓存**（默认）：
   - 如果未配置Redis，系统使用内存缓存
   - 缓存最多保留1000个键
   - 缓存过期时间：1小时（可配置）

### 数据库连接池

系统已配置数据库连接池：
- **连接池大小**：10
- **最大溢出连接**：20
- **连接回收时间**：1小时
- **连接前检查**：启用（pool_pre_ping）

### 前端优化

- **代码分割**：使用Vite自动代码分割
- **懒加载**：路由懒加载
- **资源压缩**：生产环境自动压缩

### 查询优化建议

1. **使用索引**：确保查询字段有索引
2. **限制返回行数**：设置合理的max_query_count
3. **启用分页**：对于大数据量查询，启用分页
4. **设置超时**：设置合理的查询超时时间

---

## 监控和维护

### 日志管理

系统日志位置：
- **应用日志**：`backend/logs/app_YYYY-MM-DD.log`
- **日志保留**：30天
- **日志级别**：DEBUG（开发环境）或INFO（生产环境）

### 数据库维护

#### 备份数据库

```bash
# 备份目标数据库
mysqldump -u root -p test_db > backup_test_db.sql

# 备份本地数据库
mysqldump -u root -p local_service_db > backup_local_db.sql
```

#### 清理审计日志

定期清理旧的审计日志：

```sql
-- 删除90天前的审计日志
DELETE FROM audit_logs WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);
```

### 性能监控

监控指标：
- API响应时间
- SQL执行时间
- 缓存命中率
- 错误率

### 故障排查

#### 常见问题

1. **服务无法启动**
   - 检查端口是否被占用
   - 检查数据库连接是否正常
   - 查看日志文件

2. **SQL生成失败**
   - 检查AI模型配置是否正确
   - 检查API密钥是否有效
   - 查看日志文件

3. **接口执行失败**
   - 检查数据源连接
   - 检查SQL语句是否正确
   - 查看错误日志

#### 日志查看

```bash
# 查看最新日志
tail -f backend/logs/app_$(date +%Y-%m-%d).log

# 搜索错误日志
grep ERROR backend/logs/app_*.log
```

---

## 更新和升级

### 更新代码

```bash
git pull origin main
cd backend
pip install -r requirements.txt
cd ../frontend
npm install
./s restart
```

### 数据库迁移

如果有数据库结构变更，运行迁移脚本：

```bash
cd backend
python migrations/add_db_type_support.py
python migrations/encrypt_database_passwords.py
```

---

## 技术支持

如遇到问题，请：
1. 查看日志文件
2. 查看系统文档
3. 联系技术支持团队
