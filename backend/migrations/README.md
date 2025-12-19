# 数据库迁移说明

## 多数据源支持迁移

### 执行迁移

运行以下命令执行数据库迁移，添加多数据源支持：

```bash
cd backend
python migrations/add_db_type_support.py
```

### 迁移内容

迁移脚本会执行以下操作：

1. 添加 `db_type` 字段（数据库类型）
   - 类型：VARCHAR(50)
   - 默认值：'mysql'（保持向后兼容）
   - 位置：在 `name` 字段之后

2. 添加 `extra_params` 字段（额外连接参数）
   - 类型：JSON
   - 允许为空
   - 用于存储数据库特定的连接参数（如SSL配置、连接池参数等）

3. 为现有数据设置默认值
   - 所有现有配置的 `db_type` 将被设置为 'mysql'

### 回滚迁移

如果需要回滚迁移，运行：

```bash
python migrations/add_db_type_support.py downgrade
```

**注意**：回滚会删除 `db_type` 和 `extra_params` 字段，请谨慎操作。

### 支持的数据库类型

- `mysql` - MySQL / MariaDB
- `postgresql` - PostgreSQL
- `sqlite` - SQLite
- `sqlserver` - Microsoft SQL Server
- `oracle` - Oracle Database

