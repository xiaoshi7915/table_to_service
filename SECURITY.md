# 安全说明文档

## 安全措施

### 1. SQL注入防护

#### 专家模式SQL执行
- **位置**：`backend/app/api/v1/interface_executor.py`
- **措施**：
  - 使用 `escape_identifier()` 转义表名和字段名
  - 使用 `escape_sql_value()` 转义字符串参数值（转义单引号和反斜杠）
  - 限制SQL语句只能执行SELECT查询（通过接口配置控制）

#### 图形模式SQL构建
- **位置**：`backend/app/api/v1/interface_executor.py` - `build_sql_from_graphical_config()`
- **措施**：
  - 所有表名和字段名使用反引号转义
  - 所有用户输入的值都经过 `escape_sql_value()` 转义
  - 参数值从请求参数中获取，经过转义后拼接

### 2. 认证与授权

#### JWT Token认证
- **位置**：`backend/app/core/security.py`
- **措施**：
  - 使用JWT (JSON Web Token) 进行用户认证
  - Token包含用户信息，使用HS256算法签名
  - Token有过期时间（默认30分钟）
  - 所有需要认证的接口都使用 `get_current_active_user` 依赖

#### 密码安全
- **位置**：`backend/app/core/security.py`
- **措施**：
  - 使用bcrypt进行密码哈希（如果失败则使用sha256_crypt）
  - 密码不存储明文，只存储哈希值
  - 密码验证失败不会泄露用户是否存在的信息

### 3. 敏感信息保护

#### 数据库密码
- **存储**：数据库密码存储在数据库中（已加密）
- **传输**：使用URL编码（`quote_plus`）处理密码中的特殊字符
- **日志**：密码不会记录到日志中

#### 配置信息
- **环境变量**：敏感配置（如数据库密码、JWT密钥）通过环境变量配置
- **默认值警告**：如果使用默认的SECRET_KEY，系统会发出警告

### 4. 输入验证

#### 参数验证
- **位置**：所有API路由
- **措施**：
  - 使用Pydantic进行请求参数验证
  - 验证参数类型、长度、格式等
  - 拒绝不符合要求的请求

#### SQL参数验证
- **位置**：`backend/app/api/v1/interface_executor.py`
- **措施**：
  - 验证参数类型
  - 转义特殊字符
  - 限制参数值长度（通过max_query_count）

### 5. 访问控制

#### IP白名单/黑名单
- **位置**：`backend/app/api/v1/interface_executor.py`
- **措施**：
  - 支持配置IP白名单和黑名单
  - 支持CIDR格式的IP范围
  - 在接口执行前进行IP检查

#### 限流
- **位置**：`backend/app/api/v1/interface_executor.py`
- **措施**：
  - 支持接口级别的限流配置
  - 防止接口被恶意调用

### 6. 审计日志

#### 操作日志
- **位置**：`backend/app/api/v1/interface_executor.py` - `audit_log()`
- **措施**：
  - 记录接口执行操作
  - 记录客户端IP、用户ID、操作类型等
  - 不记录敏感信息（如密码）

### 7. CORS配置

#### 跨域请求
- **位置**：`backend/app/main.py`
- **措施**：
  - 支持配置允许的源（origins）
  - 支持配置允许的方法和请求头
  - 默认允许所有源（开发环境），生产环境应限制

## 安全建议

### 生产环境配置

1. **修改SECRET_KEY**
   ```env
   SECRET_KEY=your-strong-random-secret-key-here
   ```
   使用强随机字符串，长度至少32字符

2. **限制CORS源**
   ```python
   # 在 .env 中配置
   ALLOWED_ORIGINS=http://your-frontend-domain.com,https://your-frontend-domain.com
   ```

3. **使用HTTPS**
   - 生产环境必须使用HTTPS
   - 配置SSL证书

4. **数据库安全**
   - 使用强密码
   - 限制数据库访问IP
   - 定期备份数据库

5. **日志管理**
   - 定期清理日志文件
   - 不要将日志文件暴露在公网
   - 监控异常日志

6. **接口安全**
   - 为重要接口配置IP白名单
   - 启用限流和审计日志
   - 设置合理的超时时间

## 已知安全限制

1. **SQL注入风险**：
   - 专家模式下，如果用户编写的SQL语句本身不安全，仍可能存在风险
   - 建议：只允许可信用户使用专家模式，或对SQL语句进行更严格的验证

2. **默认密钥**：
   - 如果使用默认的SECRET_KEY，系统会发出警告
   - 建议：生产环境必须修改SECRET_KEY

3. **CORS配置**：
   - 默认允许所有源（开发环境）
   - 建议：生产环境限制允许的源

## 安全更新

如发现安全问题，请及时更新代码并通知用户。

