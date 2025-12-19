# 测试套件说明

## 📋 测试内容

本测试套件包含以下4个测试模块：

### 1. SQL生成准确性测试 (`test_sql_generation.py`)
- **目的**：测试SQL生成的准确性和质量
- **测试用例**：5个典型SQL查询场景
- **评估指标**：
  - SQL语法正确性
  - 关键词匹配度
  - 安全性检查（无危险操作）
  - 表引用正确性
- **通过标准**：平均准确率≥80%

### 2. 不同模型对比测试 (`test_model_comparison.py`)
- **目的**：对比不同AI模型的SQL生成效果
- **测试内容**：
  - 质量分数对比
  - 响应时间对比
  - 成功率对比
- **输出**：最佳模型、最快模型、详细对比报告

### 3. 性能测试和优化 (`test_performance.py`)
- **目的**：测试SQL生成的性能指标
- **测试内容**：
  - 响应时间测试（平均、P95、中位数）
  - 并发性能测试（吞吐量、并发成功率）
- **通过标准**：平均响应时间≤3秒

### 4. 错误场景测试 (`test_error_scenarios.py`)
- **目的**：测试各种错误情况下的系统行为
- **测试场景**：
  - 空问题
  - 不存在的表/字段
  - SQL语法错误
  - 数据库连接失败
  - 超长问题
  - SQL注入攻击
  - 模糊问题
- **通过标准**：通过率≥80%，安全检查100%通过

## 🚀 运行测试

### 方式1：使用pytest（推荐）

```bash
cd /opt/table_to_service/backend
source venv/bin/activate

# 安装测试依赖
pip install pytest pytest-asyncio

# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_sql_generation.py -v
pytest tests/test_model_comparison.py -v
pytest tests/test_performance.py -v
pytest tests/test_error_scenarios.py -v

# 生成测试报告
pytest tests/ --html=report.html --self-contained-html
```

### 方式2：使用自定义脚本

```bash
cd /opt/table_to_service/backend
source venv/bin/activate

# 运行所有测试
python tests/run_tests.py
```

## 📊 测试报告

测试完成后会输出详细的测试报告，包括：

- **SQL生成准确性**：平均准确率、通过率、各测试用例详情
- **模型对比**：各模型的质量分数、响应时间、成功率对比
- **性能指标**：平均响应时间、P95响应时间、吞吐量
- **错误处理**：各错误场景的处理结果、安全检查结果

## ⚙️ 前置条件

1. **数据库配置**：至少配置一个激活的数据库连接
2. **AI模型配置**：至少配置一个激活的AI模型（默认模型）
3. **测试数据**：建议在测试数据库中准备一些测试表和数据

## 📝 测试用例说明

### SQL生成准确性测试用例

1. **简单查询**：查询所有用户的姓名和邮箱
2. **聚合查询**：统计每个部门的员工数量
3. **排序和限制**：查询销售额最高的前10个产品
4. **日期过滤**：查询2024年1月的订单总金额
5. **多表关联**：查询每个客户的订单数量和总金额

### 错误场景测试用例

1. **空问题**：验证输入验证
2. **不存在的表**：验证错误重试机制
3. **不存在的字段**：验证SQL修正能力
4. **SQL语法错误**：验证错误处理
5. **数据库连接失败**：验证连接错误处理
6. **超长问题**：验证输入长度限制
7. **SQL注入攻击**：验证安全性
8. **模糊问题**：验证默认处理

## 🔧 自定义测试

可以修改测试文件中的测试用例和评估标准：

- `test_sql_generation.py`：修改`_load_test_cases()`方法添加新的测试用例
- `test_model_comparison.py`：修改`test_questions`列表添加新的测试问题
- `test_performance.py`：修改`iterations`和`concurrent_count`调整测试强度
- `test_error_scenarios.py`：修改`_load_error_scenarios()`方法添加新的错误场景

## 📈 性能基准

根据验收标准，系统应满足：

- ✅ SQL生成准确率≥80%
- ✅ 平均响应时间≤3秒
- ✅ 错误场景通过率≥80%
- ✅ 安全检查100%通过

## 🐛 问题排查

如果测试失败，请检查：

1. **数据库连接**：确保数据库配置正确且可访问
2. **AI模型配置**：确保AI模型API密钥有效
3. **测试数据**：确保测试数据库中有相应的表和数据
4. **依赖安装**：确保所有依赖已正确安装

## 📚 相关文档

- [实现路线图](../../implementation_roadmap.md)
- [开发进度](../../DEVELOPMENT_PROGRESS.md)
- [设计文档](../../design.md)

