# 阿里云RDS PostgreSQL配置说明

## 获取RDS连接信息

### 1. 登录阿里云RDS控制台

1. 登录阿里云控制台
2. 进入 **云数据库RDS** 服务
3. 找到您的PostgreSQL实例（如：`gp-bp1789ydq5950he7p`）

### 2. 获取连接地址

在RDS实例详情页面，找到 **连接信息** 部分：

- **内网地址**：`gp-bp1789ydq5950he7p-master.gpdb.rds.aliyuncs.com`（仅同一VPC内可用）
- **外网地址**：`gp-bp1789ydq5950he7po-master.gpdb.rds.aliyuncs.com`（公网访问）
- **端口**：`5432`
- **数据库名称**：如 `local_service`

**重要选择：**
- 如果您的服务器**在同一个VPC内**，使用**内网地址**（更快、更安全）
- 如果您的服务器**不在同一个VPC内**，使用**外网地址**（需要先申请外网地址）
- 必须使用RDS提供的**连接地址（域名）**，不要使用IP地址！

### 3. 配置白名单

在RDS控制台的 **数据安全性** > **白名单设置** 中：

1. 点击 **添加白名单分组**
2. 添加您当前服务器的**公网IP地址**
   - 可以通过 `curl ifconfig.me` 或访问 `https://www.ipip.net` 查看
3. 保存配置

**注意：** 如果不配置白名单，外部服务器将无法连接到RDS实例。

### 4. 获取数据库账号信息

在RDS控制台的 **账号管理** 中：

- **用户名**：如 `cxs_vector`
- **密码**：您设置的密码（如 `4441326cxs!!`）

## 配置应用

在 `.env` 文件中配置：

```bash
# 本地数据库配置（阿里云RDS PostgreSQL）
LOCAL_DB_TYPE=postgresql
LOCAL_DB_HOST=gp-bp1789ydq5950he7p-master.gpdb.rds.aliyuncs.com
LOCAL_DB_PORT=5432
LOCAL_DB_USER=cxs_vector
LOCAL_DB_PASSWORD=4441326cxs!!
LOCAL_DB_NAME=local_service
```

## 测试连接

运行连接测试工具：

```bash
cd /opt/table_to_service/backend
python scripts/test_postgresql_connection.py
```

## 常见问题

### 1. 连接超时

**问题：** 连接超时或无法连接

**解决方案：**
- 确认使用的是RDS连接地址（域名），不是IP地址
- 检查白名单是否包含当前服务器的公网IP
- 检查RDS实例是否正常运行
- 检查网络是否正常（可以ping RDS连接地址）

### 2. 认证失败

**问题：** 用户名或密码错误

**解决方案：**
- 确认用户名和密码正确
- 检查账号是否有访问该数据库的权限
- 在RDS控制台重置密码（如果需要）

### 3. 数据库不存在

**问题：** 数据库名称不存在

**解决方案：**
- 在RDS控制台创建数据库
- 或使用已存在的数据库名称
- 确认数据库名称拼写正确

### 4. DNS解析失败

**问题：** 无法解析RDS连接地址

**解决方案：**
- 检查网络DNS配置
- 尝试使用 `nslookup` 或 `dig` 命令测试DNS解析
- 如果DNS有问题，可以尝试使用RDS的内网地址（如果服务器在同一VPC）

## 迁移数据到RDS

如果要从MySQL迁移数据到阿里云RDS PostgreSQL：

1. **配置源数据库（MySQL）**：
   ```bash
   export OLD_MYSQL_HOST=47.118.250.53
   export OLD_MYSQL_PORT=3306
   export OLD_MYSQL_USER=your_mysql_user
   export OLD_MYSQL_PASSWORD=your_mysql_password
   export OLD_MYSQL_DB=local_service_db
   ```

2. **配置目标数据库（RDS PostgreSQL）**：
   在 `.env` 文件中配置RDS连接信息（如上所示）

3. **运行迁移脚本**：
   ```bash
   cd /opt/table_to_service/backend
   python migrations/migrate_mysql_to_postgresql.py
   ```

## 安全建议

1. **使用强密码**：确保数据库密码足够复杂
2. **限制白名单**：只添加必要的IP地址到白名单
3. **定期备份**：在RDS控制台配置自动备份
4. **监控告警**：配置RDS监控告警，及时发现问题

