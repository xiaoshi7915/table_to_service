# AI模型配置指南

本文档介绍如何配置和使用系统中的各种AI大模型。

## 支持的AI模型提供商

系统目前支持以下12个国内大模型提供商：

### 第一梯队

1. **百度文心（ERNIE）**
   - 提供商代码：`ernie`
   - 默认模型：`ERNIE-4.0-8K`
   - API地址：`https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat`
   - API密钥格式：`access_key:secret_key` 或 `access_token`
   - 适用场景：多模态、行业插件、ToB落地
   - 获取方式：访问[百度智能云千帆大模型平台](https://cloud.baidu.com/product/wenxinworkshop)

2. **阿里通义千问（Qwen）**
   - 提供商代码：`qwen`
   - 默认模型：`qwen-turbo`
   - API地址：DashScope（无需base_url）
   - API密钥格式：DashScope API Key
   - 适用场景：代码/数学/Agent能力、长上下文
   - 获取方式：访问[阿里云DashScope](https://dashscope.aliyun.com/)

3. **腾讯混元（Hunyuan）**
   - 提供商代码：`hunyuan`
   - 默认模型：`hunyuan-pro`
   - API地址：`https://hunyuan.tencentcloudapi.com`
   - API密钥格式：`secret_id:secret_key`
   - 适用场景：多模态视频生成
   - 获取方式：访问[腾讯云混元大模型](https://cloud.tencent.com/product/hunyuan)

4. **字节豆包（Doubao）**
   - 提供商代码：`doubao`
   - 默认模型：`doubao-pro-4k`
   - API地址：`https://ark.cn-beijing.volces.com/api/v3`
   - API密钥格式：`access_key_id:secret_access_key` 或 `token`
   - 适用场景：低成本推理
   - 获取方式：访问[火山引擎豆包大模型](https://www.volcengine.com/product/doubao)

5. **华为盘古（Pangu）**
   - 提供商代码：`pangu`
   - 默认模型：`pangu-sigma`
   - API地址：`https://modelarts.cn-north-4.myhuaweicloud.com/v1`
   - API密钥格式：`access_key:secret_key` 或 `token`
   - 适用场景：ToB政企、工业、政务
   - 获取方式：访问[华为云ModelArts](https://www.huaweicloud.com/product/modelarts.html)

6. **智谱GLM**
   - 提供商代码：`glm`
   - 默认模型：`GLM-4-Plus`
   - API地址：`https://open.bigmodel.cn/api/paas/v4`
   - API密钥格式：智谱AI API Key
   - 适用场景：中文MMLU、Agent工具调用、代码、数学
   - 获取方式：访问[智谱AI开放平台](https://open.bigmodel.cn/)

### 第二梯队

7. **商汤日日新（SenseNova）**
   - 提供商代码：`sensetime`
   - 默认模型：`SenseNova-5.5`
   - API地址：`https://api.sensenova.cn/v1`
   - API密钥格式：商汤API Key
   - 适用场景：视觉-语言双模态、车规、金融、企业
   - 获取方式：访问[商汤科技开放平台](https://www.sensetime.com/)

8. **科大讯飞星火（Spark）**
   - 提供商代码：`spark`
   - 默认模型：`Spark-4.0-Ultra`
   - API地址：`https://spark-api.xf-yun.com/v1`
   - API密钥格式：`app_id:api_key:api_secret`
   - 适用场景：教育、医疗、司法
   - 获取方式：访问[讯飞开放平台](https://www.xfyun.cn/)

9. **月之暗面Kimi**
   - 提供商代码：`kimi`
   - 默认模型：`moonshot-v1-8k`
   - API地址：`https://api.moonshot.cn`
   - API密钥格式：Kimi API Key
   - 适用场景：长上下文
   - 获取方式：访问[月之暗面](https://platform.moonshot.cn/)

10. **MiniMax**
    - 提供商代码：`minimax`
    - 默认模型：`abab6.5`
    - API地址：`https://api.minimax.chat/v1`
    - API密钥格式：MiniMax API Key
    - 适用场景：角色扮演、社交
    - 获取方式：访问[MiniMax开放平台](https://www.minimax.chat/)

11. **零一万物Yi**
    - 提供商代码：`yi`
    - 默认模型：`yi-34b-chat`
    - API地址：`https://api.01.ai/v1`
    - API密钥格式：零一万物API Key
    - 适用场景：开源、性价比
    - 获取方式：访问[零一万物开放平台](https://www.01.ai/)

12. **昆仑万维Skywork**
    - 提供商代码：`skywork`
    - 默认模型：`skywork-13b-chat`
    - API地址：`https://api.skywork.ai/v1`
    - API密钥格式：昆仑万维API Key
    - 适用场景：通用对话
    - 获取方式：访问[昆仑万维开放平台](https://www.skywork.ai/)

## 应用场景说明

系统支持以下应用场景，您可以根据实际需求选择合适的场景：

- **general（通用）**：通用场景，适用于大多数任务
- **multimodal（多模态）**：支持图像、视频等多模态输入
- **code（代码）**：代码生成、代码理解、代码补全
- **math（数学）**：数学问题求解、公式推导
- **agent（Agent）**：智能体、工具调用、任务规划
- **long_context（长上下文）**：需要处理长文本的场景
- **low_cost（低成本）**：追求成本效益的场景
- **enterprise（企业）**：企业级应用、ToB场景
- **education（教育）**：教育、培训、学习辅助
- **medical（医疗）**：医疗咨询、健康管理
- **legal（司法）**：法律咨询、法条检索
- **finance（金融）**：金融分析、风险评估
- **government（政务）**：政务服务、政务咨询
- **industry（工业）**：工业场景、制造业
- **social（社交）**：社交对话、聊天机器人
- **roleplay（角色扮演）**：角色扮演、游戏对话

## 场景与模型推荐

| 场景 | 推荐模型 |
|------|---------|
| 通用 | 所有模型 |
| 多模态 | ERNIE, Hunyuan, SenseTime |
| 代码 | Qwen, GLM |
| 数学 | Qwen, GLM |
| Agent | Qwen, GLM |
| 长上下文 | Kimi, Qwen-Max-LongContext |
| 低成本 | Doubao |
| 企业 | Pangu, SenseTime |
| 教育 | Spark |
| 医疗 | Spark |
| 司法 | Spark |
| 金融 | SenseTime |
| 政务 | Pangu |
| 工业 | Pangu |
| 社交 | MiniMax |
| 角色扮演 | MiniMax |

## 配置步骤

1. **获取API密钥**
   - 访问对应提供商的开放平台
   - 注册账号并创建应用
   - 获取API密钥（注意密钥格式要求）

2. **添加模型配置**
   - 进入"AI模型配置"页面
   - 点击"添加模型"按钮
   - 填写模型信息：
     - 模型名称：自定义名称
     - 提供商：选择对应的提供商
     - API密钥：输入获取的API密钥
     - API地址：留空使用默认地址，或填写自定义地址
     - 模型标识：选择或输入具体的模型名称
     - 最大Token：设置最大token数（默认2000）
     - 温度参数：设置温度值（默认0.7）
     - 应用场景：选择适用的场景（可选）
     - 设为默认：是否设为默认模型

3. **测试连接**
   - 配置完成后，点击"测试"按钮
   - 系统会发送测试消息验证连接
   - 查看测试结果（成功/失败、响应时间）

4. **设置默认模型**
   - 选择一个模型作为默认模型
   - 点击"设默认"按钮
   - 系统将使用该模型进行智能问数

## 连接测试功能

系统提供连接测试功能，用于验证模型配置是否正确：

- **测试消息**：系统发送"你好"作为测试消息
- **测试参数**：使用较小的max_tokens（50）以减少消耗
- **测试结果**：
  - 成功：显示响应内容（前100字符）、响应时间、使用的token数
  - 失败：显示错误信息

## 注意事项

1. **API密钥安全**
   - API密钥在数据库中加密存储
   - 请妥善保管API密钥，不要泄露

2. **API调用限制**
   - 不同提供商可能有不同的调用频率限制
   - 请根据实际需求选择合适的模型

3. **成本考虑**
   - 不同模型的定价不同
   - 建议根据使用场景和预算选择合适的模型

4. **模型选择建议**
   - 根据场景选择：参考"场景与模型推荐"表
   - 根据性能选择：测试不同模型的响应速度和准确性
   - 根据成本选择：考虑token价格和使用量

5. **数据库迁移**
   - 首次使用需要运行迁移脚本添加scene字段
   - 执行命令：`python backend/migrations/add_scene_field_to_ai_model_configs.py`

## 故障排查

### 连接测试失败

1. **检查API密钥**
   - 确认API密钥格式正确
   - 确认API密钥未过期
   - 确认API密钥有足够的权限

2. **检查网络连接**
   - 确认服务器可以访问提供商的API地址
   - 检查防火墙设置

3. **检查配置信息**
   - 确认API地址正确
   - 确认模型名称正确
   - 确认参数设置合理

### 模型调用失败

1. **查看日志**
   - 检查后端日志中的错误信息
   - 根据错误信息进行排查

2. **联系支持**
   - 如问题无法解决，请联系系统管理员
   - 或查看提供商的官方文档

## 更新日志

- 2025-01-XX：初始版本，支持12个国内大模型提供商
- 2025-01-XX：添加场景选择功能
- 2025-01-XX：添加连接测试功能

