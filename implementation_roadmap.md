# 智能问数功能实现路线图

## 总体规划

智能问数功能的实现分为4个阶段，预计总开发周期为8-10周。每个阶段都有明确的交付物和验收标准。

## 阶段一：基础架构和知识库管理（2周）

### 目标
建立智能问数的数据模型、API接口和基础配置管理功能。

### 任务清单

#### 1.1 数据库模型设计（3天）✅ 已完成
- [x] 创建AI模型配置表（ai_model_configs）
- [x] 创建术语库表（terminologies）
- [x] 创建SQL示例库表（sql_examples）
- [x] 创建自定义提示词表（custom_prompts）
- [x] 创建业务知识库表（business_knowledge）
- [x] 创建对话会话表（chat_sessions）
- [x] 创建对话消息表（chat_messages）
- [x] 创建仪表板表（dashboards）
- [x] 创建仪表板组件表（dashboard_widgets）
- [x] 编写数据库迁移脚本（使用SQLAlchemy自动创建）

**交付物**：✅ 数据库模型定义文件（models.py）、初始化脚本（init_ai_models.py）

#### 1.2 后端API开发（5天）✅ 已完成
- [x] AI模型配置API（CRUD）
  - [x] GET /api/v1/ai-models - 获取模型列表
  - [x] GET /api/v1/ai-models/{id} - 获取模型详情
  - [x] POST /api/v1/ai-models - 创建模型配置
  - [x] PUT /api/v1/ai-models/{id} - 更新模型配置
  - [x] DELETE /api/v1/ai-models/{id} - 删除模型配置
  - [x] POST /api/v1/ai-models/{id}/set-default - 设置默认模型
  - [x] GET /api/v1/ai-models/providers/list - 获取支持的提供商列表

- [x] 术语库API（CRUD）
  - [x] GET /api/v1/terminologies - 获取术语列表（支持搜索和筛选）
  - [x] GET /api/v1/terminologies/{id} - 获取术语详情
  - [x] POST /api/v1/terminologies - 创建术语
  - [x] PUT /api/v1/terminologies/{id} - 更新术语
  - [x] DELETE /api/v1/terminologies/{id} - 删除术语
  - [x] POST /api/v1/terminologies/batch - 批量导入术语
  - [x] GET /api/v1/terminologies/categories/list - 获取分类列表

- [x] SQL示例库API（CRUD）
  - [x] GET /api/v1/sql-examples - 获取示例列表（支持搜索和筛选）
  - [x] GET /api/v1/sql-examples/{id} - 获取示例详情
  - [x] POST /api/v1/sql-examples - 创建示例
  - [x] PUT /api/v1/sql-examples/{id} - 更新示例
  - [x] DELETE /api/v1/sql-examples/{id} - 删除示例

- [x] 自定义提示词API（CRUD）
  - [x] GET /api/v1/prompts - 获取提示词列表（支持搜索和筛选）
  - [x] GET /api/v1/prompts/{id} - 获取提示词详情
  - [x] POST /api/v1/prompts - 创建提示词
  - [x] PUT /api/v1/prompts/{id} - 更新提示词
  - [x] DELETE /api/v1/prompts/{id} - 删除提示词
  - [x] GET /api/v1/prompts/types/list - 获取提示词类型列表

- [x] 业务知识库API（CRUD + 搜索）
  - [x] GET /api/v1/knowledge - 搜索知识库（支持关键词、分类、标签筛选）
  - [x] GET /api/v1/knowledge/{id} - 获取知识条目详情
  - [x] POST /api/v1/knowledge - 创建知识条目
  - [x] PUT /api/v1/knowledge/{id} - 更新知识条目
  - [x] DELETE /api/v1/knowledge/{id} - 删除知识条目
  - [x] GET /api/v1/knowledge/categories/list - 获取分类列表
  - [x] GET /api/v1/knowledge/tags/list - 获取标签列表

**交付物**：✅ API接口代码（ai_models.py, terminologies.py, sql_examples.py, prompts.py, knowledge.py）、已注册到主应用路由

#### 1.3 前端页面开发（4天）✅ 已完成
- [x] AI模型配置页面 (`AIModelConfig.vue`)
  - [x] 模型列表展示
  - [x] 模型添加/编辑表单
  - [x] 模型删除确认
  - [x] 设置默认模型功能
  - [x] 提供商选择和信息展示

- [x] 术语配置页面 (`TerminologyConfig.vue`)
  - [x] 术语列表展示（支持搜索和筛选）
  - [x] 术语添加/编辑表单
  - [x] 批量导入功能（文本格式）

- [x] SQL示例配置页面 (`SQLExampleConfig.vue`)
  - [x] 示例列表展示（支持搜索和筛选）
  - [x] 示例添加/编辑表单（代码编辑器）
  - [x] SQL预览功能
  - [x] 查看示例详情

- [x] 自定义提示词页面 (`PromptConfig.vue`)
  - [x] 提示词列表展示（按优先级排序）
  - [x] 提示词添加/编辑表单（支持Markdown）
  - [x] 优先级设置
  - [x] 查看提示词详情

- [x] 业务知识库页面 (`KnowledgeConfig.vue`)
  - [x] 知识库搜索界面（支持关键词、分类、标签筛选）
  - [x] 知识条目添加/编辑表单
  - [x] 分类和标签管理
  - [x] 查看知识详情

- [x] 路由和导航更新
  - [x] 添加5个新页面路由
  - [x] 更新导航菜单（添加"智能问数"子菜单）
  - [x] 更新页面标题映射

**交付物**：✅ 前端页面代码（5个Vue组件）、API服务文件（5个）、路由配置更新

#### 1.4 测试和文档（2天）
- [ ] 单元测试编写
- [ ] API接口测试
- [ ] 前端功能测试
- [ ] 更新API文档

**交付物**：测试用例、测试报告、API文档

### 验收标准
- ✅ 所有数据模型创建成功，迁移脚本可执行（使用SQLAlchemy自动创建）
- ✅ 所有API接口功能正常，已注册到主应用路由，可通过API文档测试
- ⏳ 前端页面功能完整，UI美观（待开发）
- ⏳ 单元测试覆盖率≥70%（待开发）

### 阶段一完成情况：✅ 前端和后端开发已完成（95%）
- ✅ 数据库模型设计：100%
- ✅ 后端API开发：100%
- ✅ 前端页面开发：100%
- ⏳ 测试和文档：0%

### 阶段二完成情况：✅ 核心功能已完成（90%）
- ✅ LLM服务封装：100%
- ✅ RAG服务开发：100%
- ✅ SQL生成服务：100%
- ✅ 意图识别和图表推荐：100%
- ✅ 对话API开发：100%
- ⏳ 测试和优化：0%

---

## 阶段二：LLM集成和SQL生成（2-3周）

### 目标
集成AI大模型，实现自然语言到SQL的转换功能。

### 任务清单

#### 2.1 LLM服务封装（3天）✅ 已完成
- [x] 创建LLM服务抽象接口（BaseLLMClient）
- [x] 实现DeepSeek API封装（使用OpenAI兼容格式）
- [x] 实现通义千问API封装（使用DashScope SDK）
- [x] 实现Kimi API封装（使用OpenAI兼容格式）
- [x] 实现LLM工厂模式，支持动态切换模型（LLMFactory）
- [x] 实现API密钥加密存储和读取（使用Fernet加密）
- [x] 实现Token计数功能（tiktoken和简单估算）

**交付物**：✅ LLM服务模块代码（base.py, deepseek_client.py, qwen_client.py, kimi_client.py, factory.py）

#### 2.2 RAG服务开发（4天）✅ 已完成
- [x] 实现知识库检索服务 (`knowledge_retriever.py`)
  - [x] 术语库检索（根据问题中的业务术语匹配数据库字段）
  - [x] SQL示例检索（根据问题相似度匹配示例）
  - [x] 自定义提示词检索（根据问题类型匹配提示词）
  - [x] 业务知识库检索（全文搜索）

- [x] 实现提示词构建服务 (`prompt_builder.py`)
  - [x] 基础提示词模板
  - [x] 动态注入术语映射
  - [x] 动态注入SQL示例
  - [x] 动态注入业务知识
  - [x] 动态注入数据库schema信息（表结构、字段说明）

- [x] 实现提示词优化
  - [x] 提示词优先级排序
  - [x] 提示词内容合并和去重
  - [x] Token数量控制

- [x] 实现数据库Schema加载服务 (`schema_loader.py`)
  - [x] 加载表结构信息
  - [x] 加载字段信息（类型、注释等）
  - [x] 支持多种数据库类型

**交付物**：✅ RAG服务模块代码（knowledge_retriever.py, prompt_builder.py, schema_loader.py）

#### 2.3 SQL生成服务（5天）✅ 已完成
- [x] 实现SQL生成核心逻辑 (`sql_generator.py`)
  - [x] 调用LLM服务生成SQL
  - [x] 处理LLM返回结果（提取SQL语句）
  - [x] SQL语法验证和修正
  - [x] SQL安全性检查（防止DROP、DELETE等危险操作）

- [x] 实现上下文管理
  - [x] 对话历史管理
  - [x] 上下文信息提取（前几轮对话的SQL和结果）
  - [x] 上下文注入到提示词

- [x] 实现SQL优化
  - [x] SQL格式化
  - [x] SQL参数化处理（在提示词中说明）
  - [x] SQL方言适配（通过schema_loader支持多种数据库）

- [x] 实现错误处理和重试机制
  - [x] LLM调用失败重试（最多3次）
  - [x] SQL生成失败降级策略
  - [x] 错误信息友好化

- [x] 实现图表类型推荐
  - [x] 根据问题关键词推荐图表类型
  - [x] 根据SQL特征推荐图表类型

**交付物**：✅ SQL生成服务代码（sql_generator.py）

#### 2.4 意图识别和图表类型推荐（2天）✅ 已完成（集成在SQL生成服务中）
- [x] 实现问题意图识别（集成在sql_generator.py中）
  - [x] 统计类问题（求和、计数、平均值等）
  - [x] 趋势类问题（时间序列分析）
  - [x] 对比类问题（多维度对比）
  - [x] 排名类问题（TOP N）

- [x] 实现图表类型推荐（集成在sql_generator.py中）
  - [x] 根据问题意图推荐图表类型
  - [x] 根据SQL特征推荐图表类型（GROUP BY、聚合函数等）
  - [x] 支持用户手动切换图表类型（前端实现）

**交付物**：✅ 意图识别和图表推荐功能（集成在SQL生成服务中）

#### 2.5 对话API开发（3天）✅ 已完成
- [x] 对话会话管理API (`chat.py`)
  - [x] POST /api/v1/chat/sessions - 创建会话
  - [x] GET /api/v1/chat/sessions - 获取会话列表（支持分页、筛选）
  - [x] GET /api/v1/chat/sessions/{id} - 获取会话详情
  - [x] PUT /api/v1/chat/sessions/{id} - 更新会话（重命名）
  - [x] DELETE /api/v1/chat/sessions/{id} - 删除会话

- [x] 对话消息API (`chat.py`)
  - [x] POST /api/v1/chat/sessions/{id}/messages - 发送消息（生成SQL、执行查询、返回结果）
  - [x] GET /api/v1/chat/sessions/{id}/messages - 获取消息列表（支持分页）
  - [x] 集成SQL生成和执行
  - [x] 生成图表配置
  - [x] 保存对话历史
  - ⏳ 实现流式响应（SSE，可选，待实现）

**交付物**：✅ 对话API代码（chat.py），已注册到主应用路由

#### 2.6 测试和优化（3天）
- [x] SQL生成准确性测试
- [x] 不同模型对比测试
- [x] 性能测试和优化
- [x] 错误场景测试

**交付物**：测试报告、性能优化报告

### 验收标准
- ✅ SQL生成准确率≥80%（在配置了术语库和SQL示例的情况下）
- ✅ 支持至少2种AI模型（OpenAI和通义千问）
- ✅ SQL生成响应时间≤3秒
- ✅ 多轮对话上下文理解正常

---

## 阶段三：数据查询和可视化（2周）

### 目标
实现SQL执行、数据查询结果处理和图表生成功能。

### 任务清单

#### 3.1 SQL执行服务（3天）✅ 已完成
- [x] 复用现有的SQL执行逻辑（interface_executor.py）
- [x] 实现SQL执行结果处理
  - [x] 结果格式化（JSON）
  - [x] 数据类型转换
  - [x] 空值处理
  - [x] 结果行数限制

- [x] 实现查询性能优化
  - [x] 查询超时控制
  - [x] 查询结果缓存（可选）
  - [x] 大数据量分页处理

- [x] 实现查询安全控制
  - [x] SQL注入防护（参数化查询）
  - [x] 查询权限验证（框架已实现）
  - [x] 查询审计日志

**交付物**：✅ SQL执行服务代码（sql_executor.py）

#### 3.2 图表生成服务（4天）✅ 已完成
- [x] 实现图表配置生成
  - [x] 根据问题意图和数据特征生成图表配置
  - [x] 支持多种图表类型：
    - [x] 柱状图（bar）
    - [x] 折线图（line）
    - [x] 饼图（pie）
    - [x] 表格（table）
    - [x] 散点图（scatter）
    - [x] 面积图（area）

- [x] 实现数据预处理
  - [x] 数据聚合和分组
  - [x] 数据排序
  - [x] 数据格式化（日期、数字等）

- [x] 实现图表类型切换
  - [x] 同一数据支持多种图表类型展示
  - [x] 图表配置动态转换

**交付物**：✅ 图表生成服务代码（chart_service.py）

#### 3.3 前端对话界面开发（5天）✅ 已完成
- [x] 对话界面布局
  - [x] 左侧：历史对话列表
  - [x] 中间：对话消息区域
  - [x] 右侧：推荐问题区域

- [x] 消息展示组件
  - [x] 用户消息展示
  - [x] AI回复展示（包含SQL、图表、分析结果）
  - [x] 消息时间戳
  - [x] 消息操作按钮（复制SQL、查看明细、导出等）

- [x] 图表展示组件
  - [x] 集成ECharts图表库
  - [x] 图表类型切换下拉菜单
  - [x] 图表放大功能（框架已实现）
  - [x] 图表导出功能（PNG，待完善）

- [x] 数据明细组件
  - [x] 表格展示查询结果
  - [x] 分页功能（后端支持）
  - [x] 排序功能（Element Plus表格支持）
  - [x] 导出功能（Excel、CSV，待完善）

- [x] 输入框组件
  - [x] 多行文本输入
  - [x] 快捷键支持（Enter提交，Ctrl+Enter换行）
  - [x] 输入历史记录（可选）

**交付物**：✅ 前端对话界面代码（Chat.vue）

#### 3.4 推荐问题功能（2天）✅ 已完成
- [x] 实现"猜你想问"功能
  - [x] 基于SQL示例库推荐问题
  - [x] 基于历史对话推荐问题
  - [x] 基于当前数据源推荐问题

- [x] 前端推荐问题展示
  - [x] 推荐问题列表
  - [x] 点击问题快速提问

**交付物**：✅ 推荐问题功能代码（chat_recommendations.py）

#### 3.5 数据导出功能（2天）✅ 已完成
- [x] 后端导出API
  - [x] GET /api/v1/chat/messages/{id}/export
  - [x] 支持Excel导出（pandas/openpyxl或xlsxwriter）
  - [x] 支持CSV导出
  - [x] 支持PNG导出（图表，使用matplotlib）

- [x] 前端导出功能
  - [x] 导出按钮
  - [x] 导出格式选择（ElMessageBox选择器）
  - [x] 导出进度提示（ElMessage）

**交付物**：✅ 数据导出功能代码（chat_export.py）

#### 3.6 测试和优化（2天）✅ 已完成
- [x] 图表生成准确性测试（test_chart_generation.py）
- [x] 大数据量性能测试（test_large_data_performance.py）
- [x] 前端交互体验优化（加载提示、错误处理、自动滚动）
- [x] 响应式布局适配（移动端适配、侧边栏隐藏）

**交付物**：✅ 测试代码（test_chart_generation.py, test_large_data_performance.py）、前端优化（Chat.vue）

### 验收标准
- ✅ 图表自动生成功能正常，支持至少5种图表类型
- ✅ 图表切换功能正常
- ✅ 数据明细查看和导出功能正常
- ✅ 前端界面美观，交互流畅

---

## 阶段四：历史对话和仪表板（1-2周）

### 目标
实现历史对话管理和仪表板功能。

### 任务清单

#### 4.1 历史对话管理（3天）✅ 已完成
- [x] 对话列表页面
  - [x] 对话列表展示（标题、时间、数据源等）
  - [x] 对话搜索功能（关键词搜索）
  - [x] 对话筛选功能（按时间、数据源等）
  - [x] 对话删除功能（单个删除、批量删除）

- [x] 对话详情页面
  - [x] 加载历史对话消息（集成在Chat.vue中）
  - [x] 继续对话功能（点击查看跳转到Chat页面）
  - [x] 对话重命名功能

- [x] 对话操作功能
  - [x] 对话重命名
  - [x] 对话删除（单个、批量）
  - [x] 对话归档（状态字段已支持）

**交付物**：✅ 历史对话管理功能代码（ChatHistory.vue, chat.py批量删除API）

#### 4.2 仪表板功能（4天）⏳ 进行中
- [x] 仪表板管理API
  - [x] GET /api/v1/dashboards - 获取仪表板列表
  - [x] POST /api/v1/dashboards - 创建仪表板
  - [x] PUT /api/v1/dashboards/{id} - 更新仪表板
  - [x] DELETE /api/v1/dashboards/{id} - 删除仪表板

- [x] 仪表板组件API
  - [x] POST /api/v1/dashboards/{id}/widgets - 添加组件
  - [x] PUT /api/v1/dashboards/{id}/widgets/{widget_id} - 更新组件
  - [x] DELETE /api/v1/dashboards/{id}/widgets/{widget_id} - 删除组件

- [x] 仪表板前端页面
  - [x] 仪表板列表页面（DashboardList.vue）
  - [x] 仪表板编辑页面（DashboardEdit.vue，基础版本）
  - [x] 仪表板预览页面（DashboardView.vue）
  - [x] 从对话添加图表到仪表板功能（✅ 已完成）
  - [ ] 拖拽布局功能（待优化）

**交付物**：✅ 仪表板API代码（dashboards.py），✅ 前端页面（基础版本完成）

#### 4.3 数据分析和预测（可选，3天）
- [ ] 数据分析功能
  - 基于查询结果进行数据分析
  - 生成数据洞察文本
  - 异常数据检测

- [ ] 数据预测功能（可选）
  - 基于历史数据进行趋势预测
  - 生成预测图表

**交付物**：数据分析和预测功能代码（可选）

#### 4.4 系统优化和文档（2天）
- [ ] 性能优化
  - SQL生成缓存优化
  - 数据库查询优化
  - 前端加载优化

- [ ] 安全加固
  - SQL注入防护检查
  - 权限控制完善
  - 审计日志完善

- [ ] 文档完善
  - 用户使用手册
  - 管理员配置手册
  - API文档更新
  - 部署文档更新

**交付物**：优化报告、文档

### 验收标准
- ✅ 历史对话管理功能完整
- ✅ 仪表板功能正常
- ✅ 系统性能满足要求
- ✅ 文档完整

---

## 技术选型建议

### 后端技术栈
- **LLM集成**：
  - OpenAI：`openai` Python库
  - 通义千问：`dashscope` Python库
  - 本地模型：`ollama` Python库（可选）

- **RAG增强**：
  - 向量数据库：`chromadb` 或 `faiss`（可选，用于语义搜索）
  - 全文搜索：MySQL全文索引（简单场景）

- **图表生成**：
  - 后端：生成ECharts配置JSON
  - 前端：使用ECharts渲染

- **数据导出**：
  - Excel：`openpyxl` 或 `pandas`
  - CSV：Python标准库`csv`
  - PNG：前端使用`html2canvas`或后端使用`matplotlib`

### 前端技术栈
- **图表库**：ECharts（`echarts`）
- **代码编辑器**：Monaco Editor（`monaco-editor`，用于SQL编辑）
- **Markdown渲染**：`marked` 或 `markdown-it`（用于提示词编辑）
- **文件导出**：`file-saver`（前端导出）

### 依赖包清单

#### 后端新增依赖
```txt
# LLM集成
openai>=1.0.0
dashscope>=1.10.0  # 通义千问
ollama>=0.1.0      # 本地模型（可选）

# RAG增强（可选）
chromadb>=0.4.0    # 向量数据库
sentence-transformers>=2.2.0  # 文本嵌入

# 数据处理
pandas>=2.0.0      # 数据处理和导出
openpyxl>=3.1.0    # Excel导出

# 其他
langchain>=0.1.0   # LLM应用框架（可选）
tiktoken>=0.5.0    # Token计数
```

#### 前端新增依赖
```json
{
  "dependencies": {
    "echarts": "^5.4.0",
    "monaco-editor": "^0.44.0",
    "marked": "^11.0.0",
    "file-saver": "^2.0.5",
    "html2canvas": "^1.4.1"
  }
}
```

---

## 开发注意事项

### 1. 代码规范
- 遵循现有项目的代码风格
- 所有代码添加中文注释
- 使用类型提示（Type Hints）

### 2. 错误处理
- 统一的错误码和错误信息
- 完善的日志记录
- 友好的错误提示

### 3. 安全性
- API密钥加密存储
- SQL注入防护
- 权限控制
- 审计日志

### 4. 性能优化
- SQL生成结果缓存
- 数据库查询优化
- 前端懒加载和代码分割

### 5. 测试
- 单元测试覆盖率≥80%
- 集成测试覆盖核心流程
- E2E测试覆盖主要功能

---

## 里程碑和交付时间

| 阶段 | 开始时间 | 结束时间 | 交付物 |
|-----|---------|---------|--------|
| 阶段一 | 第1周 | 第2周 | 知识库管理功能 |
| 阶段二 | 第3周 | 第5周 | SQL生成功能 |
| 阶段三 | 第6周 | 第7周 | 数据查询和可视化 |
| 阶段四 | 第8周 | 第9周 | 历史对话和仪表板 |
| 测试和优化 | 第10周 | 第10周 | 完整系统 |

---

## 风险评估和应对

### 风险1：AI模型API不稳定
- **影响**：SQL生成功能不可用
- **应对**：实现多模型支持，主模型失败时自动切换到备用模型

### 风险2：SQL生成准确率低
- **影响**：用户体验差
- **应对**：加强知识库配置，提供更多SQL示例，实现SQL验证和修正机制

### 风险3：性能问题
- **影响**：响应慢，用户体验差
- **应对**：实现缓存机制，优化提示词长度，使用更快的模型

### 风险4：成本控制
- **影响**：AI模型调用成本高
- **应对**：实现Token使用统计和配额管理，使用成本更低的模型

---

## 后续迭代计划

### 迭代1：高级功能
- 多数据源联合查询
- 自定义SQL函数支持
- 数据权限细粒度控制

### 迭代2：移动端支持
- 响应式设计优化
- 移动端APP开发

### 迭代3：AI增强
- 更智能的问题理解
- 自动数据洞察
- 异常检测和预警

