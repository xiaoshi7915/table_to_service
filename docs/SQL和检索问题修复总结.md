# SQL和检索问题修复总结

## 修复的问题

### 1. WITH子句SQL被误判为非SELECT语句 ✅

**问题描述：**
- 生成的SQL包含WITH子句（CTE），但被误判为"只允许执行SELECT查询语句"
- 例如：`WITH enterprise_fair_counts AS (...) SELECT ...`

**根本原因：**
- SQL安全验证只检查 `sql_upper.startswith("SELECT")`
- WITH子句的SQL以 `WITH` 开头，不是 `SELECT`

**修复方案：**
- 修改 `_validate_sql_safety` 方法，允许 `WITH` 开头的SQL
- 确保WITH子句包含SELECT语句

**修复代码位置：**
- `backend/app/core/rag_langchain/sql_executor.py` 第 231-233 行

**修复后：**
```python
# 只允许SELECT语句或WITH子句（CTE）开头的SELECT语句
if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
    raise ValueError("只允许执行SELECT查询语句")

# 如果以WITH开头，必须包含SELECT
if sql_upper.startswith("WITH") and "SELECT" not in sql_upper:
    raise ValueError("WITH子句必须包含SELECT语句")
```

### 2. SQL参数绑定错误 ✅

**问题描述：**
- 生成的SQL包含命名参数占位符（如 `:company_name`），但没有提供参数值
- 错误：`A value is required for bind parameter 'company_name'`
- 后续错误：`Replacement index 0 out of range for positional args tuple`

**根本原因：**
- LLM生成的SQL包含参数占位符，但调用时没有提供参数值
- `_parameterize_sql` 方法没有处理未绑定的参数

**修复方案：**
- 检测SQL中未绑定的参数占位符
- 自动移除未绑定的参数条件（如 `WHERE column != :param_name`）
- 如果无法移除，替换为NULL

**修复代码位置：**
- `backend/app/core/rag_langchain/sql_executor.py` 第 284-306 行

**修复后：**
- 自动检测未绑定的参数
- 移除包含未绑定参数的条件（如 `WHERE column != :param_name`）
- 如果WHERE子句变为空，移除WHERE关键字
- 添加警告日志

### 3. 检索到0个文档 ⚠️

**问题描述：**
- 日志显示：`检索到 0 个术语，0 个SQL示例，0 个知识条目`
- 合并后得到 0 个唯一文档

**可能原因：**
1. **向量存储中没有数据**（最可能）
   - 需要运行 `python scripts/init_vector_store.py` 初始化向量存储
   - 向量存储可能为空

2. **检索器未初始化**
   - 如果向量存储不可用，检索器可能为None
   - 已添加调试日志来诊断

3. **查询没有匹配的文档**
   - 向量检索可能没有找到相似文档
   - 这是正常的，如果问题与现有知识库不相关

**已添加的调试日志：**
- 在 `rag_workflow.py` 中添加了详细的调试日志
- 记录检索器是否初始化
- 记录检索返回的文档数量

**排查步骤：**
1. 检查向量存储是否有数据：
   ```bash
   cd /opt/table_to_service/backend
   python scripts/init_vector_store.py
   ```

2. 检查日志中的调试信息：
   - 查看是否有 "术语检索器未初始化" 的日志
   - 查看是否有 "术语检索返回 X 个文档" 的日志

3. 如果向量存储为空，需要先导入数据：
   - 确保数据库中有术语、SQL示例、知识条目
   - 运行初始化脚本导入到向量存储

### 4. 前端表字段悬停显示功能 ✅

**问题描述：**
- 用户希望在已选表上，鼠标悬停时显示表字段和字段描述

**实现方案：**
- 使用 `el-tooltip` 组件显示表字段信息
- 懒加载：鼠标悬停时才加载字段信息
- 缓存机制：已加载的字段信息会被缓存

**实现功能：**
1. **悬停触发加载**
   - 鼠标悬停在表标签上时，自动加载表字段信息
   - 使用 `@mouseenter="loadTableFields(table)"` 触发

2. **字段信息显示**
   - 显示表名和表描述
   - 显示字段列表（最多20个）
   - 每个字段显示：字段名、类型、注释

3. **缓存机制**
   - 已加载的字段信息会被缓存
   - 避免重复请求

**实现代码位置：**
- `frontend/src/views/Chat.vue` 第 67-87 行（模板）
- `frontend/src/views/Chat.vue` 第 608 行（变量定义）
- `frontend/src/views/Chat.vue` 第 834-904 行（方法实现）
- `frontend/src/views/Chat.vue` 第 2590-2600 行（样式）

**API调用：**
- 使用 `/api/v1/database-configs/{config_id}/tables/{table_name}/info` 获取表字段信息

## 测试建议

### 1. 测试WITH子句SQL
- 发送一个需要CTE的复杂查询
- 确认SQL能够正常执行

### 2. 测试参数绑定
- 发送一个包含参数占位符的查询
- 确认未绑定的参数会被自动处理

### 3. 测试文档检索
- 检查日志中的调试信息
- 如果检索到0个文档，运行初始化脚本：
  ```bash
  cd /opt/table_to_service/backend
  python scripts/init_vector_store.py
  ```

### 4. 测试表字段悬停
- 在聊天页面，鼠标悬停在已选表标签上
- 确认显示表字段和字段描述
- 确认字段信息被正确缓存

## 预期效果

- **WITH子句SQL**：应该能够正常执行，不再被误判
- **参数绑定**：未绑定的参数会被自动处理，SQL能够正常执行
- **文档检索**：如果向量存储有数据，应该能够检索到相关文档
- **表字段悬停**：鼠标悬停时显示表字段和字段描述

