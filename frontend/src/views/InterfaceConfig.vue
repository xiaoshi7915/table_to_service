<template>
  <div class="interface-config">
    <el-page-header @back="goBack" title="返回">
      <template #content>
        <span class="text-large font-600 mr-3">数据表转接口</span>
      </template>
    </el-page-header>

    <el-card style="margin-top: 20px;">
      <!-- 步骤条 -->
      <el-steps :active="currentStep" finish-status="success" align-center>
        <el-step title="选择模式" />
        <el-step title="配置SQL" />
        <el-step title="基础信息" />
        <el-step title="代理接口" />
        <el-step title="风险管控" />
        <el-step title="确认配置" />
      </el-steps>

      <!-- 步骤0: 选择模式 -->
      <div v-if="currentStep === 0" class="step-content">
        <el-card class="mode-selection-card" style="margin-top: 30px;">
          <template #header>
            <div class="mode-header">
              <el-icon :size="24" style="margin-right: 8px;"><Setting /></el-icon>
              <span>选择录入模式</span>
            </div>
          </template>
          
          <div class="mode-container">
            <!-- 专家模式卡片 -->
            <div 
              class="mode-card expert-mode" 
              :class="{ 'active': formData.entry_mode === 'expert' }"
              @click="formData.entry_mode = 'expert'"
            >
              <div class="mode-icon-wrapper">
                <el-icon :size="60" class="mode-icon"><Document /></el-icon>
              </div>
              <div class="mode-title">专家模式</div>
              <div class="mode-subtitle">Expert Mode</div>
              <div class="mode-description">
                <p>适合熟悉SQL语法的开发者使用</p>
                <ul class="mode-features">
                  <li>
                    <el-icon><Check /></el-icon>
                    <span>直接编写SQL语句，灵活度高</span>
                  </li>
                  <li>
                    <el-icon><Check /></el-icon>
                    <span>支持复杂查询和高级SQL特性</span>
                  </li>
                  <li>
                    <el-icon><Check /></el-icon>
                    <span>使用 :param_name 格式定义参数</span>
                  </li>
                  <li>
                    <el-icon><Check /></el-icon>
                    <span>自动解析SQL中的参数信息</span>
                  </li>
                </ul>
              </div>
              <div class="mode-example">
                <div class="example-label">示例：</div>
                <pre class="example-code">SELECT * FROM users<br/>WHERE id = :id AND status = :status</pre>
              </div>
              <div class="mode-select-indicator" v-if="formData.entry_mode === 'expert'">
                <el-icon><Select /></el-icon>
                已选择
              </div>
            </div>
            
            <!-- 图形模式卡片 -->
            <div 
              class="mode-card graphical-mode" 
              :class="{ 'active': formData.entry_mode === 'graphical' }"
              @click="formData.entry_mode = 'graphical'"
            >
              <div class="mode-icon-wrapper">
                <el-icon :size="60" class="mode-icon"><Grid /></el-icon>
              </div>
              <div class="mode-title">图形模式</div>
              <div class="mode-subtitle">Graphical Mode</div>
              <div class="mode-description">
                <p>通过可视化界面配置SQL，无需编写代码</p>
                <ul class="mode-features">
                  <li>
                    <el-icon><Check /></el-icon>
                    <span>可视化选择表和字段</span>
                  </li>
                  <li>
                    <el-icon><Check /></el-icon>
                    <span>图形化配置WHERE条件</span>
                  </li>
                  <li>
                    <el-icon><Check /></el-icon>
                    <span>可视化设置排序规则</span>
                  </li>
                  <li>
                    <el-icon><Check /></el-icon>
                    <span>实时预览生成的SQL语句</span>
                  </li>
                </ul>
              </div>
              <div class="mode-example">
                <div class="example-label">特点：</div>
                <div class="example-text">无需SQL知识，通过点选即可完成配置，适合非技术人员使用</div>
              </div>
              <div class="mode-select-indicator" v-if="formData.entry_mode === 'graphical'">
                <el-icon><Select /></el-icon>
                已选择
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 步骤1: 配置SQL -->
      <div v-if="currentStep === 1" class="step-content">
        <el-card style="margin-top: 30px;">
          <template #header>
            <span>配置SQL</span>
          </template>

          <!-- 专家模式 -->
          <div v-if="formData.entry_mode === 'expert'">
            <el-form :model="formData" label-width="120px">
              <el-form-item label="数据库" required>
                <el-select 
                  v-model="formData.database_config_id" 
                  placeholder="请选择数据库"
                  style="width: 100%;"
                  @change="handleDatabaseChange"
                >
                  <el-option
                    v-for="db in databaseConfigs"
                    :key="db.id"
                    :label="db.name"
                    :value="db.id"
                  />
                </el-select>
              </el-form-item>
              
              <el-form-item label="SQL语句" required>
                <div style="margin-bottom: 8px;">
                  <el-button size="small" type="info" @click="copySqlExample('simple')">复制简单查询示例</el-button>
                  <el-button size="small" type="info" @click="copySqlExample('with_params')" style="margin-left: 8px;">复制带参数示例</el-button>
                  <el-button size="small" type="info" @click="copySqlExample('join')" style="margin-left: 8px;">复制JOIN示例</el-button>
                </div>
                <el-input
                  v-model="formData.sql_statement"
                  type="textarea"
                  :rows="10"
                  placeholder="请输入SQL语句，使用 :param_name 格式定义参数，例如: SELECT * FROM users WHERE id = :id"
                />
              </el-form-item>
              
              <el-form-item>
                <el-button type="primary" @click="parseSql" :loading="parsing">
                  解析SQL参数
                </el-button>
              </el-form-item>
              
              <!-- 专家模式显示表名和字段 -->
              <el-form-item label="数据表" v-if="formData.database_config_id && tables.length > 0">
                <el-select 
                  v-model="selectedTableForReference" 
                  placeholder="选择表名查看字段信息（不影响SQL）"
                  style="width: 100%;"
                  clearable
                  @change="handleTableSelectForReference"
                  :loading="loadingTableFields"
                >
                  <el-option
                    v-for="table in tables"
                    :key="table"
                    :label="table"
                    :value="table"
                  />
                </el-select>
                <div style="font-size: 12px; color: #909399; margin-top: 5px;">
                  提示：选择表名可查看该表的字段信息，便于编写SQL语句
                </div>
              </el-form-item>
              
              <!-- 显示选中表的字段信息 -->
              <el-form-item v-if="selectedTableForReference && tableFields.length > 0" label="表字段信息">
                <el-table :data="tableFields" border style="width: 100%;" max-height="300">
                  <el-table-column prop="name" label="字段名" width="150" />
                  <el-table-column prop="type" label="类型" width="120" />
                  <el-table-column prop="nullable" label="可空" width="80">
                    <template #default="{ row }">
                      <el-tag :type="row.nullable ? 'info' : 'danger'" size="small">
                        {{ row.nullable ? '是' : '否' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="default" label="默认值" width="120" />
                  <el-table-column prop="comment" label="注释" min-width="200" />
                </el-table>
                <div style="margin-top: 10px;">
                  <el-button size="small" type="primary" @click="copyTableNameToClipboard">
                    复制表名到剪贴板
                  </el-button>
                  <el-button size="small" type="info" @click="copyAllFieldsToClipboard" style="margin-left: 8px;">
                    复制所有字段名
                  </el-button>
                </div>
              </el-form-item>
              
              <!-- 请求参数映射 -->
              <el-form-item v-if="sqlParseResult.request_parameters?.length > 0" label="请求参数映射">
                <el-table :data="sqlParseResult.request_parameters" border style="width: 100%;">
                  <el-table-column prop="name" label="参数名" width="150" />
                  <el-table-column prop="type" label="类型" width="100" />
                  <el-table-column prop="description" label="描述" min-width="150" />
                  <el-table-column prop="constraint" label="约束" width="100">
                    <template #default="{ row }">
                      <el-tag :type="row.constraint === 'required' ? 'danger' : 'info'" size="small">
                        {{ row.constraint === 'required' ? '必填' : '可选' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="location" label="位置" width="100" />
                </el-table>
              </el-form-item>
              
              <!-- 响应参数映射 -->
              <el-form-item v-if="sqlParseResult.response_parameters?.length > 0" label="响应参数映射" style="margin-top: 20px;">
                <el-table :data="sqlParseResult.response_parameters" border style="width: 100%;">
                  <el-table-column prop="name" label="字段名" width="150" />
                  <el-table-column prop="type" label="类型" width="150" />
                  <el-table-column prop="description" label="描述" min-width="200" />
                </el-table>
              </el-form-item>
            </el-form>
          </div>

          <!-- 图形模式 -->
          <div v-else>
            <el-form :model="formData" label-width="120px">
              <el-form-item label="数据库" required>
                <el-select 
                  v-model="formData.database_config_id" 
                  placeholder="请选择数据库"
                  style="width: 100%;"
                  @change="handleDatabaseChange"
                >
                  <el-option
                    v-for="db in databaseConfigs"
                    :key="db.id"
                    :label="db.name"
                    :value="db.id"
                  />
                </el-select>
              </el-form-item>
              
              <el-form-item label="数据表" required>
                <el-select 
                  v-model="formData.table_name" 
                  placeholder="请选择数据表"
                  style="width: 100%;"
                  @change="handleTableChange"
                  :loading="loadingTables"
                >
                  <el-option
                    v-for="table in tables"
                    :key="table"
                    :label="table"
                    :value="table"
                  />
                </el-select>
              </el-form-item>
              
              <el-form-item label="选择字段" required>
                <el-checkbox-group v-model="formData.selected_fields" style="display: flex; flex-direction: column; gap: 12px;">
                  <el-checkbox 
                    v-for="col in tableColumns" 
                    :key="col.name" 
                    :label="col.name"
                    style="display: flex; align-items: center; padding: 8px; border: 1px solid #e4e7ed; border-radius: 4px;"
                  >
                    <div style="display: flex; flex-direction: column; margin-left: 8px;">
                      <div style="font-weight: 600; color: #303133;">
                        {{ col.name }}
                        <el-tag v-if="col.primary_key" type="danger" size="small" style="margin-left: 5px;">主键</el-tag>
                      </div>
                      <div style="font-size: 12px; color: #909399; margin-top: 2px;">
                        {{ col.type }}
                        <span v-if="col.comment" style="margin-left: 8px; color: #606266;">- {{ col.comment }}</span>
                      </div>
                    </div>
                  </el-checkbox>
                </el-checkbox-group>
                <div style="margin-top: 10px;">
                  <el-button size="small" @click="selectAllFields">全选</el-button>
                  <el-button size="small" @click="clearAllFields">清空</el-button>
                </div>
              </el-form-item>
              
              <el-form-item label="WHERE条件">
                <div v-for="(condition, index) in formData.where_conditions" :key="index" style="margin-bottom: 12px; padding: 16px; background: #f5f7fa; border-radius: 8px; border: 1px solid #e4e7ed;">
                  <el-row :gutter="12" style="align-items: center;">
                    <el-col :span="2">
                      <el-select v-model="condition.logic" v-if="index > 0" style="width: 100%;">
                        <el-option label="AND" value="AND" />
                        <el-option label="OR" value="OR" />
                      </el-select>
                      <span v-else style="line-height: 32px; color: #606266; font-weight: 600;">条件</span>
                    </el-col>
                    <el-col :span="6">
                      <el-select v-model="condition.field" placeholder="选择字段" style="width: 100%;" filterable>
                        <el-option
                          v-for="col in tableColumns"
                          :key="col.name"
                          :label="col.comment ? `${col.name} (${col.comment})` : col.name"
                          :value="col.name"
                        >
                          <span style="display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" :title="col.comment ? `${col.name} (${col.comment})` : col.name">
                            {{ col.comment ? `${col.name} (${col.comment})` : col.name }}
                          </span>
                        </el-option>
                      </el-select>
                    </el-col>
                    <el-col :span="4">
                      <el-select v-model="condition.operator" placeholder="操作符" style="width: 100%;">
                        <el-option label="等于" value="equal" />
                        <el-option label="不等于" value="not_equal" />
                        <el-option label="大于" value="greater" />
                        <el-option label="大于等于" value="greater_equal" />
                        <el-option label="小于" value="less" />
                        <el-option label="小于等于" value="less_equal" />
                        <el-option label="包含" value="like" />
                        <el-option label="不包含" value="not_like" />
                        <el-option label="在范围内" value="in" />
                        <el-option label="不在范围内" value="not_in" />
                        <el-option label="为空" value="is_null" />
                        <el-option label="不为空" value="is_not_null" />
                      </el-select>
                    </el-col>
                    <el-col :span="3">
                      <el-select v-model="condition.value_type" placeholder="值类型" style="width: 100%;">
                        <el-option label="常量" value="constant" />
                        <el-option label="变量" value="variable" />
                      </el-select>
                    </el-col>
                    <el-col :span="6" v-if="condition.value_type === 'constant'">
                      <el-input v-model="condition.value" placeholder="常量值" style="width: 100%;" />
                    </el-col>
                    <el-col :span="6" v-if="condition.value_type === 'variable'">
                      <el-input v-model="condition.variable_name" placeholder="变量名" style="width: 100%;" />
                    </el-col>
                    <el-col :span="3">
                      <el-button type="danger" size="small" @click="removeCondition(index)" style="width: 100%;">
                        <el-icon><Delete /></el-icon>
                        删除
                      </el-button>
                    </el-col>
                  </el-row>
                </div>
                <el-button type="primary" @click="addCondition" style="width: 100%;">
                  <el-icon><Plus /></el-icon>
                  添加条件
                </el-button>
              </el-form-item>
              
              <el-form-item label="排序字段">
                <div v-for="(order, index) in formData.order_by_fields" :key="index" style="margin-bottom: 12px; padding: 16px; background: #f5f7fa; border-radius: 8px; border: 1px solid #e4e7ed;">
                  <el-row :gutter="12" style="align-items: center;">
                    <el-col :span="14">
                      <el-select v-model="order.field" placeholder="选择字段" style="width: 100%;" filterable>
                        <el-option
                          v-for="col in tableColumns"
                          :key="col.name"
                          :label="col.comment ? `${col.name} (${col.comment})` : col.name"
                          :value="col.name"
                        >
                          <span style="display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" :title="col.comment ? `${col.name} (${col.comment})` : col.name">
                            {{ col.comment ? `${col.name} (${col.comment})` : col.name }}
                          </span>
                        </el-option>
                      </el-select>
                    </el-col>
                    <el-col :span="6">
                      <el-select v-model="order.direction" placeholder="排序方式" style="width: 100%;">
                        <el-option label="升序" value="ASC" />
                        <el-option label="降序" value="DESC" />
                      </el-select>
                    </el-col>
                    <el-col :span="4">
                      <el-button type="danger" size="small" @click="removeOrder(index)" style="width: 100%;">
                        <el-icon><Delete /></el-icon>
                        删除
                      </el-button>
                    </el-col>
                  </el-row>
                </div>
                <el-button type="primary" @click="addOrder" style="width: 100%;">
                  <el-icon><Plus /></el-icon>
                  添加排序
                </el-button>
              </el-form-item>
              
              <el-form-item label="SQL预览">
                <el-input
                  v-model="previewSqlText"
                  type="textarea"
                  :rows="5"
                  readonly
                />
              </el-form-item>
            </el-form>
          </div>
        </el-card>
      </div>

      <!-- 步骤2: 基础信息 -->
      <div v-if="currentStep === 2" class="step-content">
        <el-card style="margin-top: 30px;">
          <template #header>
            <span>基础信息</span>
          </template>
          
          <el-form :model="formData" label-width="120px">
            <el-form-item label="接口名称" required>
              <el-input v-model="formData.interface_name" placeholder="请输入接口名称" />
            </el-form-item>
            
            <el-form-item label="接口描述">
              <el-input 
                v-model="formData.interface_description" 
                type="textarea" 
                :rows="3"
                placeholder="请输入接口描述"
              />
            </el-form-item>
            
            <el-form-item label="使用说明">
              <el-input 
                v-model="formData.usage_instructions" 
                type="textarea" 
                :rows="5"
                placeholder="请输入使用说明"
              />
            </el-form-item>
            
            <el-form-item label="分类">
              <el-input v-model="formData.category" placeholder="请输入分类" />
            </el-form-item>
            
            <el-form-item label="状态">
              <el-radio-group v-model="formData.status">
                <el-radio label="draft">草稿</el-radio>
                <el-radio label="inactive">禁用</el-radio>
                <el-radio label="active">激活</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-form>
        </el-card>
      </div>

      <!-- 步骤3: 代理接口 -->
      <div v-if="currentStep === 3" class="step-content">
        <el-card style="margin-top: 30px;">
          <template #header>
            <span>定义代理接口</span>
          </template>
          
          <el-form :model="formData" label-width="120px">
            <el-form-item label="HTTP方法" required>
              <el-select v-model="formData.http_method" style="width: 100%;">
                <el-option label="GET" value="GET" />
                <el-option label="POST" value="POST" />
                <el-option label="PUT" value="PUT" />
                <el-option label="DELETE" value="DELETE" />
                <el-option label="PATCH" value="PATCH" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="代理路径" required>
              <el-input v-model="formData.proxy_path" placeholder="/api/v1/example" />
            </el-form-item>
            
            <el-form-item label="代理协议">
              <el-select v-model="formData.proxy_schemes" style="width: 100%;">
                <el-option label="http" value="http" />
                <el-option label="https" value="https" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="请求格式">
              <el-select v-model="formData.request_format" style="width: 100%;">
                <el-option label="application/json" value="application/json" />
                <el-option label="application/xml" value="application/xml" />
                <el-option label="application/x-www-form-urlencoded" value="application/x-www-form-urlencoded" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="响应格式">
              <el-select v-model="formData.response_format" style="width: 100%;">
                <el-option label="application/json" value="application/json" />
                <el-option label="application/xml" value="application/xml" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="扩展字段">
              <el-input 
                v-model="formData.extension_fields" 
                type="textarea" 
                :rows="3"
                placeholder="JSON格式的扩展字段"
              />
            </el-form-item>
            
            <el-form-item>
              <el-checkbox v-model="formData.sync_to_gateway">同步到网关</el-checkbox>
            </el-form-item>
            
            <el-form-item>
              <el-checkbox v-model="formData.associate_plugin">关联插件</el-checkbox>
            </el-form-item>
            
            <el-form-item>
              <el-checkbox v-model="formData.is_options_request">是否开启 OPTIONS 请求</el-checkbox>
            </el-form-item>
            
            <el-form-item>
              <el-checkbox v-model="formData.is_head_request">是否开启 HEAD 请求</el-checkbox>
            </el-form-item>
            
            <el-form-item>
              <el-checkbox v-model="formData.define_date_format">定义日期格式</el-checkbox>
            </el-form-item>
            
            <el-divider>跨域设置</el-divider>
            
            <el-form-item>
              <el-checkbox v-model="formData.enable_cors">开启系统跨域</el-checkbox>
            </el-form-item>
            
            <template v-if="formData.enable_cors">
              <el-form-item label="Access-Control-Allow-Origin" required>
                <el-input v-model="formData.cors_allow_origin" placeholder="例如: * 或 http://example.com" />
                <div style="font-size: 12px; color: #909399; margin-top: 5px;">
                  提示：* 表示允许所有域名，或指定具体域名
                </div>
              </el-form-item>
              
              <el-form-item label="Access-Control-Expose-Headers">
                <el-input v-model="formData.cors_expose_headers" placeholder="例如: Content-Length, X-Kuma-Revision" />
              </el-form-item>
              
              <el-form-item label="Access-Control-Max-Age">
                <el-input-number v-model="formData.cors_max_age" :min="0" :max="86400" placeholder="预检请求缓存时间（秒）" style="width: 100%;" />
              </el-form-item>
              
              <el-form-item label="Access-Control-Allow-Methods" required>
                <el-input v-model="formData.cors_allow_methods" placeholder="例如: GET, POST, PUT, DELETE, OPTIONS" />
                <div style="font-size: 12px; color: #909399; margin-top: 5px;">
                  提示：多个方法用逗号分隔
                </div>
              </el-form-item>
              
              <el-form-item label="Access-Control-Allow-Headers">
                <el-input v-model="formData.cors_allow_headers" placeholder="例如: Content-Type, Authorization" />
              </el-form-item>
              
              <el-form-item>
                <el-checkbox v-model="formData.cors_allow_credentials">Access-Control-Allow-Credentials</el-checkbox>
              </el-form-item>
            </template>
            
            <el-divider>HTTP Response Header 参数</el-divider>
            
            <el-form-item label="响应头列表">
              <div v-for="(header, index) in formData.response_headers" :key="index" style="margin-bottom: 12px; padding: 16px; background: #f5f7fa; border-radius: 8px; border: 1px solid #e4e7ed;">
                <el-row :gutter="12" style="align-items: center;">
                  <el-col :span="6">
                    <el-input v-model="header.name" placeholder="响应头名称，例如: X-Custom-Header" style="width: 100%;" />
                  </el-col>
                  <el-col :span="12">
                    <el-input v-model="header.value" placeholder="响应头值" style="width: 100%;" />
                  </el-col>
                  <el-col :span="4">
                    <el-input v-model="header.description" placeholder="描述（可选）" style="width: 100%;" />
                  </el-col>
                  <el-col :span="2">
                    <el-button type="danger" size="small" @click="removeResponseHeader(index)" style="width: 100%;">
                      <el-icon><Delete /></el-icon>
                      删除
                    </el-button>
                  </el-col>
                </el-row>
              </div>
              <el-button type="primary" @click="addResponseHeader" style="width: 100%;">
                <el-icon><Plus /></el-icon>
                添加响应头
              </el-button>
              <div style="font-size: 12px; color: #909399; margin-top: 8px;">
                提示：可以添加自定义HTTP响应头，例如 X-Request-ID、X-API-Version 等
              </div>
            </el-form-item>
          </el-form>
        </el-card>
      </div>

      <!-- 步骤4: 风险管控 -->
      <div v-if="currentStep === 4" class="step-content">
        <el-card style="margin-top: 30px;">
          <template #header>
            <span>风险管控设置</span>
          </template>
          
          <el-form :model="formData" label-width="150px">
            <el-form-item>
              <el-checkbox v-model="formData.enable_pagination">启用分页</el-checkbox>
              <div style="font-size: 12px; color: #909399; margin-top: 5px;">
                提示：启用分页后，接口调用需要传递 pageNumber 和 pageSize 参数
              </div>
            </el-form-item>
            
            <el-form-item v-if="formData.enable_pagination">
              <el-checkbox v-model="formData.return_total_count">返回总数</el-checkbox>
              <div style="font-size: 12px; color: #909399; margin-top: 5px;">
                提示：返回总数会增加一次COUNT查询，可能影响性能
              </div>
            </el-form-item>
            
            <el-form-item label="最大查询数量" v-if="!formData.enable_pagination">
              <el-input-number v-model="formData.max_query_count" :min="1" :max="10000" style="width: 100%;" />
              <div style="font-size: 12px; color: #909399; margin-top: 5px;">
                提示：不分页时，限制单次查询返回的最大记录数
              </div>
            </el-form-item>
            
            <el-form-item label="超时时间（秒）">
              <el-input-number v-model="formData.timeout_seconds" :min="1" :max="300" />
            </el-form-item>
            
            <el-form-item>
              <el-checkbox v-model="formData.enable_rate_limit">启用限流</el-checkbox>
            </el-form-item>
            
            <el-form-item label="代理认证">
              <el-select v-model="formData.proxy_auth" style="width: 100%;">
                <el-option label="免验证" value="no_auth" />
                <el-option label="Basic 验证" value="basic" />
                <el-option label="Digest 验证" value="digest" />
                <el-option label="Token 验证" value="token" />
                <el-option label="一次验证" value="once" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="数据加密方式">
              <el-select v-model="formData.encryption_method" style="width: 100%;">
                <el-option label="无加密" value="no_encryption" />
                <el-option label="SM4" value="sm4" />
                <el-option label="DES" value="des" />
                <el-option label="AES" value="aes" />
              </el-select>
            </el-form-item>
            
            <el-form-item>
              <el-checkbox v-model="formData.enable_replay_protection">启用重放保护</el-checkbox>
            </el-form-item>
            
            <el-form-item>
              <el-checkbox v-model="formData.enable_whitelist">启用白名单</el-checkbox>
            </el-form-item>
            
            <el-form-item label="白名单IP地址" v-if="formData.enable_whitelist">
              <el-input
                v-model="formData.whitelist_ips"
                type="textarea"
                :rows="3"
                placeholder="请输入IP地址，多个IP用换行分隔，例如：&#10;192.168.1.1&#10;192.168.1.2&#10;10.0.0.0/8"
              />
              <div style="font-size: 12px; color: #909399; margin-top: 5px;">
                提示：每行一个IP地址，支持CIDR格式（如 10.0.0.0/8）
              </div>
            </el-form-item>
            
            <el-form-item>
              <el-checkbox v-model="formData.enable_blacklist">启用黑名单</el-checkbox>
            </el-form-item>
            
            <el-form-item label="黑名单IP地址" v-if="formData.enable_blacklist">
              <el-input
                v-model="formData.blacklist_ips"
                type="textarea"
                :rows="3"
                placeholder="请输入IP地址，多个IP用换行分隔，例如：&#10;192.168.1.100&#10;192.168.1.101"
              />
              <div style="font-size: 12px; color: #909399; margin-top: 5px;">
                提示：每行一个IP地址，支持CIDR格式（如 192.168.1.0/24）
              </div>
            </el-form-item>
            
            <el-form-item>
              <el-checkbox v-model="formData.enable_audit_log">启用审计日志</el-checkbox>
            </el-form-item>
          </el-form>
        </el-card>
      </div>

      <!-- 步骤5: 确认配置 -->
      <div v-if="currentStep === 5" class="step-content">
        <el-card style="margin-top: 30px;">
          <template #header>
            <span>配置确认</span>
          </template>
          
          <el-descriptions :column="2" border>
            <el-descriptions-item label="录入模式">
              {{ formData.entry_mode === 'expert' ? '专家模式' : '图形模式' }}
            </el-descriptions-item>
            <el-descriptions-item label="数据库">
              {{ getDatabaseName(formData.database_config_id) }}
            </el-descriptions-item>
            <el-descriptions-item label="接口名称">{{ formData.interface_name }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="formData.status === 'active' ? 'success' : 'info'">
                {{ formData.status === 'active' ? '激活' : formData.status === 'inactive' ? '禁用' : '草稿' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="HTTP方法">{{ formData.http_method }}</el-descriptions-item>
            <el-descriptions-item label="代理路径">{{ formData.proxy_path }}</el-descriptions-item>
            <el-descriptions-item label="接口描述" :span="2">
              {{ formData.interface_description || '无' }}
            </el-descriptions-item>
            <el-descriptions-item label="SQL语句" :span="2" v-if="formData.entry_mode === 'expert'">
              <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto;">{{ formData.sql_statement }}</pre>
            </el-descriptions-item>
            <el-descriptions-item label="表名" v-if="formData.entry_mode === 'graphical'">
              {{ formData.table_name }}
            </el-descriptions-item>
            <el-descriptions-item label="选择字段" v-if="formData.entry_mode === 'graphical'">
              {{ formData.selected_fields?.join(', ') || '全部' }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </div>

      <!-- 操作按钮 -->
      <div style="margin-top: 30px; text-align: center;">
        <el-button v-if="currentStep > 0" @click="prevStep">上一步</el-button>
        <el-button 
          v-if="currentStep < 5" 
          type="primary" 
          @click="nextStep"
          :loading="saving"
        >
          下一步
        </el-button>
        <el-button 
          v-if="currentStep === 5" 
          type="primary" 
          @click="saveConfig"
          :loading="saving"
        >
          保存配置
        </el-button>
        <el-button @click="goBack">取消</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Document, Grid, Setting, Check, Select, Plus, Delete } from '@element-plus/icons-vue'
import api from '../api'

const router = useRouter()
const route = useRoute()

const currentStep = ref(0)
const saving = ref(false)
const parsing = ref(false)
const loadingTables = ref(false)
const databaseConfigs = ref([])
const tables = ref([])
const tableColumns = ref([])
const selectedTableForReference = ref('')
const tableFields = ref([])
const loadingTableFields = ref(false)
const sqlParseResult = reactive({
  request_parameters: [],
  response_parameters: []
})
const previewSqlText = ref('')

const formData = reactive({
  entry_mode: 'expert',
  database_config_id: null,
  sql_statement: '',
  table_name: '',
  selected_fields: [],
  where_conditions: [],
  order_by_fields: [],
  interface_name: '',
  interface_description: '',
  usage_instructions: '',
  category: '',
  status: 'draft',
  http_method: 'GET',
  proxy_schemes: 'http',
  proxy_path: '',
  request_format: 'application/json',
  response_format: 'application/json',
  extension_fields: '',
  sync_to_gateway: false,
  associate_plugin: false,
  is_options_request: false,
  is_head_request: false,
  define_date_format: false,
  return_total_count: false,
  enable_pagination: false,
  max_query_count: 10,
  enable_rate_limit: false,
  timeout_seconds: 10,
  proxy_auth: 'no_auth',
  encryption_method: 'no_encryption',
  enable_replay_protection: false,
  enable_whitelist: false,
  enable_blacklist: false,
  enable_audit_log: false,
  whitelist_ips: '',
  blacklist_ips: '',
  // 跨域设置
  enable_cors: false,
  cors_allow_origin: '*',
  cors_expose_headers: '',
  cors_max_age: 3600,
  cors_allow_methods: 'GET, POST, PUT, DELETE, OPTIONS',
  cors_allow_headers: 'Content-Type, Authorization',
  cors_allow_credentials: true,
  // HTTP Response Headers
  response_headers: []
})

// 监听数据库变化，加载表列表
watch(() => formData.database_config_id, (newVal) => {
  if (newVal) {
    loadTables()
  }
})

// 监听图形模式配置变化，更新SQL预览
watch(() => [
  formData.table_name,
  formData.selected_fields,
  formData.where_conditions,
  formData.order_by_fields
], () => {
  if (formData.entry_mode === 'graphical') {
    previewSql()
  }
}, { deep: true })

onMounted(() => {
  loadDatabaseConfigs()
  
  // 如果是编辑模式，加载配置
  const configId = route.query.id
  if (configId) {
    loadConfig(configId)
  }
})

const loadDatabaseConfigs = async () => {
  try {
    const res = await api.get('/database-configs')
    if (res.data.success) {
      databaseConfigs.value = res.data.data || []
    }
  } catch (error) {
    ElMessage.error('加载数据库配置失败: ' + (error.response?.data?.detail || error.message))
  }
}

const loadTables = async () => {
  if (!formData.database_config_id) return
  
  loadingTables.value = true
  try {
    const res = await api.get(`/database-configs/${formData.database_config_id}/tables`)
    if (res.data.success) {
      tables.value = res.data.data || []
    }
  } catch (error) {
    ElMessage.error('加载表列表失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loadingTables.value = false
  }
}

const handleDatabaseChange = () => {
  // 专家模式和图形模式都加载表列表
  loadTables()
  if (formData.entry_mode === 'graphical') {
    formData.table_name = ''
    tableColumns.value = []
    formData.selected_fields = []
    formData.where_conditions = []
    formData.order_by_fields = []
  }
}

const handleTableSelectForReference = async (tableName) => {
  // 选择表后加载字段信息
  if (tableName) {
    await loadTableFields(tableName)
  } else {
    tableFields.value = []
  }
}

const loadTableFields = async (tableName) => {
  if (!formData.database_config_id || !tableName) return
  
  loadingTableFields.value = true
  try {
    const res = await api.get(`/database-configs/${formData.database_config_id}/tables/${tableName}/info`)
    if (res.data.success && res.data.data) {
      tableFields.value = res.data.data.columns || []
    }
  } catch (error) {
    ElMessage.error('加载表字段信息失败: ' + (error.response?.data?.detail || error.message))
    tableFields.value = []
  } finally {
    loadingTableFields.value = false
  }
}

const copyTableNameToClipboard = async () => {
  if (selectedTableForReference.value) {
    try {
      await navigator.clipboard.writeText(selectedTableForReference.value)
      ElMessage.success('表名已复制到剪贴板')
    } catch (error) {
      ElMessage.error('复制失败')
    }
  }
}

const copyAllFieldsToClipboard = async () => {
  if (tableFields.value.length > 0) {
    const fields = tableFields.value.map(f => f.name).join(', ')
    try {
      await navigator.clipboard.writeText(fields)
      ElMessage.success('所有字段名已复制到剪贴板')
    } catch (error) {
      ElMessage.error('复制失败')
    }
  }
}

const copySqlExample = async (type) => {
  const examples = {
    simple: 'SELECT * FROM table_name LIMIT 10',
    with_params: 'SELECT * FROM users WHERE id = :id AND status = :status',
    join: `SELECT u.id, u.name, p.title 
FROM users u 
LEFT JOIN posts p ON u.id = p.user_id 
WHERE u.status = :status 
ORDER BY u.created_at DESC 
LIMIT :limit`
  }
  
  const sql = examples[type] || examples.simple
  try {
    await navigator.clipboard.writeText(sql)
    ElMessage.success('SQL示例已复制到剪贴板')
    formData.sql_statement = sql
  } catch (error) {
    // 降级方案
    const textarea = document.createElement('textarea')
    textarea.value = sql
    document.body.appendChild(textarea)
    textarea.select()
    try {
      document.execCommand('copy')
      ElMessage.success('SQL示例已复制到剪贴板')
      formData.sql_statement = sql
    } catch (e) {
      ElMessage.error('复制失败，请手动复制')
    }
    document.body.removeChild(textarea)
  }
}

const handleTableChange = async () => {
  if (!formData.database_config_id || !formData.table_name) return
  
  try {
    const tableName = encodeURIComponent(formData.table_name)
    const res = await api.get(`/database-configs/${formData.database_config_id}/tables/${tableName}/info`)
    if (res.data.success) {
      tableColumns.value = res.data.data.columns || []
      // 默认选择所有字段
      formData.selected_fields = tableColumns.value.map(col => col.name)
    }
  } catch (error) {
    ElMessage.error('加载表信息失败: ' + (error.response?.data?.detail || error.message))
  }
}

const selectAllFields = () => {
  formData.selected_fields = tableColumns.value.map(col => col.name)
}

const clearAllFields = () => {
  formData.selected_fields = []
}

const addCondition = () => {
  formData.where_conditions.push({
    logic: 'AND',
    field: '',
    operator: 'equal',
    value_type: 'constant',
    value: '',
    variable_name: ''
  })
}

const removeCondition = (index) => {
  formData.where_conditions.splice(index, 1)
}

const addOrder = () => {
  formData.order_by_fields.push({
    field: '',
    direction: 'ASC'
  })
}

const removeOrder = (index) => {
  formData.order_by_fields.splice(index, 1)
}

const addResponseHeader = () => {
  formData.response_headers.push({
    name: '',
    value: '',
    description: ''
  })
}

const removeResponseHeader = (index) => {
  formData.response_headers.splice(index, 1)
}

const previewSql = () => {
  if (!formData.table_name) {
    previewSqlText.value = ''
    return
  }
  
  // 构建SELECT字段
  let fields = '*'
  if (formData.selected_fields && formData.selected_fields.length > 0) {
    fields = formData.selected_fields.join(', ')
  }
  
  let sql = `SELECT ${fields} FROM ${formData.table_name}`
  
  // 构建WHERE子句
  if (formData.where_conditions && formData.where_conditions.length > 0) {
    const whereParts = []
    formData.where_conditions.forEach((cond, index) => {
      if (!cond.field) return
      
      const logic = index > 0 ? ` ${cond.logic} ` : ''
      let condition = ''
      
      if (cond.operator === 'is_null') {
        condition = `${cond.field} IS NULL`
      } else if (cond.operator === 'is_not_null') {
        condition = `${cond.field} IS NOT NULL`
      } else {
        const opMap = {
          equal: '=',
          not_equal: '!=',
          greater: '>',
          greater_equal: '>=',
          less: '<',
          less_equal: '<=',
          like: 'LIKE',
          not_like: 'NOT LIKE',
          in: 'IN',
          not_in: 'NOT IN'
        }
        const op = opMap[cond.operator] || '='
        
        let value = ''
        if (cond.value_type === 'variable') {
          value = `:${cond.variable_name}`
        } else {
          value = typeof cond.value === 'string' ? `'${cond.value}'` : cond.value
        }
        
        condition = `${cond.field} ${op} ${value}`
      }
      
      whereParts.push(logic + condition)
    })
    
    if (whereParts.length > 0) {
      sql += ' WHERE' + whereParts.join('')
    }
  }
  
  // 构建ORDER BY子句
  if (formData.order_by_fields && formData.order_by_fields.length > 0) {
    const orderParts = []
    formData.order_by_fields.forEach(order => {
      if (order.field) {
        orderParts.push(`${order.field} ${order.direction}`)
      }
    })
    if (orderParts.length > 0) {
      sql += ' ORDER BY ' + orderParts.join(', ')
    }
  }
  
  previewSqlText.value = sql
}

const parseSql = async () => {
  if (!formData.sql_statement) {
    ElMessage.warning('请先输入SQL语句')
    return
  }
  
  parsing.value = true
  try {
    const res = await api.post('/interface-configs/parse-sql', {
      sql: formData.sql_statement
    })
    if (res.data.success) {
      sqlParseResult.request_parameters = res.data.data.request_parameters || []
      sqlParseResult.response_parameters = res.data.data.response_parameters || []
      ElMessage.success('SQL解析成功')
    }
  } catch (error) {
    ElMessage.error('SQL解析失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    parsing.value = false
  }
}

const nextStep = () => {
  // 验证当前步骤
  if (currentStep.value === 1) {
    if (!formData.database_config_id) {
      ElMessage.warning('请选择数据库')
      return
    }
    if (formData.entry_mode === 'expert' && !formData.sql_statement) {
      ElMessage.warning('请输入SQL语句')
      return
    }
    if (formData.entry_mode === 'graphical' && !formData.table_name) {
      ElMessage.warning('请选择数据表')
      return
    }
    if (formData.entry_mode === 'graphical' && (!formData.selected_fields || formData.selected_fields.length === 0)) {
      ElMessage.warning('请至少选择一个字段')
      return
    }
  } else if (currentStep.value === 2) {
    if (!formData.interface_name) {
      ElMessage.warning('请输入接口名称')
      return
    }
  } else if (currentStep.value === 3) {
    if (!formData.proxy_path) {
      ElMessage.warning('请输入代理路径')
      return
    }
  }
  
  if (currentStep.value < 5) {
    currentStep.value++
  }
}

const prevStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

const getDatabaseName = (id) => {
  const db = databaseConfigs.value.find(d => d.id === id)
  return db ? db.name : ''
}

const loadConfig = async (configId) => {
  try {
    const res = await api.get(`/interface-configs/${configId}`)
    if (res.data.success) {
      const config = res.data.data
      Object.assign(formData, {
        entry_mode: config.entry_mode || 'expert',
        database_config_id: config.database_config_id,
        sql_statement: config.sql_statement || '',
        table_name: config.table_name || '',
        selected_fields: config.selected_fields || [],
        where_conditions: config.where_conditions || [],
        order_by_fields: config.order_by_fields || [],
        interface_name: config.interface_name || '',
        interface_description: config.interface_description || '',
        usage_instructions: config.usage_instructions || '',
        category: config.category || '',
        status: config.status || 'draft',
        http_method: config.http_method || 'GET',
        proxy_schemes: config.proxy_schemes || 'http',
        proxy_path: config.proxy_path || '',
        request_format: config.request_format || 'application/json',
        response_format: config.response_format || 'application/json',
        extension_fields: config.extension_fields || '',
        sync_to_gateway: config.sync_to_gateway || false,
        associate_plugin: config.associate_plugin || false,
        is_options_request: config.is_options_request || false,
        is_head_request: config.is_head_request || false,
        define_date_format: config.define_date_format || false,
        return_total_count: config.return_total_count || false,
        enable_pagination: config.enable_pagination || false,
        max_query_count: config.max_query_count || 10,
        enable_rate_limit: config.enable_rate_limit || false,
        timeout_seconds: config.timeout_seconds || 10,
        proxy_auth: config.proxy_auth || 'no_auth',
        encryption_method: config.encryption_method || 'no_encryption',
        enable_replay_protection: config.enable_replay_protection || false,
        enable_whitelist: config.enable_whitelist || false,
        whitelist_ips: config.whitelist_ips || '',
        enable_blacklist: config.enable_blacklist || false,
        blacklist_ips: config.blacklist_ips || '',
        enable_audit_log: config.enable_audit_log || false,
        // 跨域设置
        enable_cors: config.enable_cors || false,
        cors_allow_origin: config.cors_allow_origin || '*',
        cors_expose_headers: config.cors_expose_headers || '',
        cors_max_age: config.cors_max_age || 3600,
        cors_allow_methods: config.cors_allow_methods || 'GET, POST, PUT, DELETE, OPTIONS',
        cors_allow_headers: config.cors_allow_headers || 'Content-Type, Authorization',
        cors_allow_credentials: config.cors_allow_credentials !== undefined ? config.cors_allow_credentials : true,
        // HTTP Response Headers
        response_headers: config.response_headers || []
      })
      
      // 如果是图形模式，加载表信息
      if (config.entry_mode === 'graphical' && config.table_name) {
        await handleTableChange()
      }
    }
  } catch (error) {
    ElMessage.error('加载配置失败: ' + (error.response?.data?.detail || error.message))
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    const configData = { ...formData }
    
    // 如果是图形模式，生成SQL
    if (configData.entry_mode === 'graphical') {
      previewSql()
      configData.sql_statement = previewSqlText.value
    }
    
    const configId = route.query.id
    if (configId) {
      // 更新配置
      const res = await api.put(`/interface-configs/${configId}`, configData)
      if (res.data.success) {
        ElMessage.success('更新成功')
        try {
          await router.push('/interface-list')
        } catch (routerError) {
          ElMessage.error('更新成功，但页面跳转失败')
        }
      }
    } else {
      // 创建配置
      const res = await api.post('/interface-configs', configData)
      if (res && res.data && res.data.success) {
        ElMessage.success('创建成功')
        try {
          await router.push('/interface-list')
        } catch (routerError) {
          ElMessage.error('保存成功，但页面跳转失败')
        }
      } else {
        ElMessage.error('保存失败: 响应格式不正确')
      }
    }
  } catch (error) {
    ElMessage.error('保存失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    saving.value = false
  }
}

const goBack = () => {
  router.push('/interface-list')
}
</script>

<style scoped>
.interface-config {
  padding: 24px;
  min-height: calc(100vh - 120px);
}

.interface-config :deep(.el-page-header) {
  background: white;
  padding: 20px 24px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  margin-bottom: 24px;
}

.interface-config :deep(.el-page-header__left) {
  color: #667eea;
}

.interface-config :deep(.el-page-header__content .text-large) {
  font-size: 22px;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.interface-config :deep(.el-card) {
  border-radius: 12px;
  border: 1px solid #e4e7ed;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transition: all 0.3s;
  margin-bottom: 20px;
}

.interface-config :deep(.el-card:hover) {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.interface-config :deep(.el-card__header) {
  background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%);
  border-bottom: 2px solid #e4e7ed;
  padding: 16px 20px;
  font-weight: 600;
  font-size: 16px;
  color: #303133;
}

.step-content {
  min-height: 500px;
  padding: 20px 0;
}

.interface-config :deep(.el-steps) {
  padding: 30px 20px;
  background: white;
  border-radius: 12px;
  margin-bottom: 24px;
}

.interface-config :deep(.el-step__title) {
  font-weight: 600;
  font-size: 14px;
}

.interface-config :deep(.el-step__head.is-process) {
  color: #667eea;
  border-color: #667eea;
}

.interface-config :deep(.el-step__head.is-finish) {
  color: #67c23a;
  border-color: #67c23a;
}

.interface-config :deep(.el-step__title.is-process) {
  color: #667eea;
  font-weight: 700;
}

.interface-config :deep(.el-step__title.is-finish) {
  color: #67c23a;
}

.interface-config :deep(.el-radio-button) {
  border-radius: 8px;
  overflow: hidden;
  margin: 0 8px;
}

.interface-config :deep(.el-radio-button__inner) {
  border-radius: 8px;
  padding: 30px 20px;
  transition: all 0.3s;
  border: 2px solid #e4e7ed;
}

.interface-config :deep(.el-radio-button__inner:hover) {
  border-color: #667eea;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
}

.interface-config :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: #667eea;
  color: white;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.interface-config :deep(.el-form-item__label) {
  font-weight: 600;
  color: #606266;
}

.interface-config :deep(.el-input__wrapper) {
  border-radius: 8px;
  transition: all 0.3s;
}

.interface-config :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #667eea inset;
}

.interface-config :deep(.el-select) {
  width: 100%;
}

.interface-config :deep(.el-select .el-input__wrapper) {
  border-radius: 8px;
}

.interface-config :deep(.el-textarea__inner) {
  border-radius: 8px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.interface-config :deep(.el-button) {
  border-radius: 8px;
  padding: 10px 20px;
  font-weight: 500;
  transition: all 0.3s;
}

.interface-config :deep(.el-button--primary) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
}

.interface-config :deep(.el-button--primary:hover) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.interface-config :deep(.el-button--success) {
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
  border: none;
}

.interface-config :deep(.el-button--success:hover) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(103, 194, 58, 0.4);
}

.interface-config :deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
}

.interface-config :deep(.el-table th) {
  background: #f5f7fa;
  font-weight: 600;
}

.interface-config :deep(.el-tag) {
  border-radius: 6px;
  padding: 4px 12px;
  font-weight: 500;
}

.interface-config :deep(.el-divider__text) {
  background: white;
  font-weight: 600;
  color: #606266;
  font-size: 16px;
}

.interface-config :deep(.el-descriptions) {
  border-radius: 8px;
}

.interface-config :deep(.el-descriptions__label) {
  font-weight: 600;
  color: #606266;
}

.interface-config :deep(.el-descriptions__content) {
  color: #303133;
}

/* 代码预览样式 */
.interface-config :deep(pre) {
  background: #282c34;
  color: #abb2bf;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  border: 1px solid #3e4451;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}

/* 步骤按钮区域 */
.interface-config :deep(.el-card .el-card__body) {
  padding: 24px;
}

/* 模式选择卡片样式 */
.mode-selection-card {
  background: white;
}

.mode-header {
  display: flex;
  align-items: center;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.mode-container {
  display: flex;
  gap: 24px;
  padding: 20px 0;
  justify-content: center;
}

.mode-card {
  flex: 1;
  max-width: 480px;
  min-height: 600px;
  border: 3px solid #e4e7ed;
  border-radius: 16px;
  padding: 32px;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  background: white;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.mode-card:hover {
  border-color: #667eea;
  transform: translateY(-8px);
  box-shadow: 0 12px 32px rgba(102, 126, 234, 0.2);
}

.mode-card.active {
  border-color: #667eea;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.3);
  transform: translateY(-4px);
}

.mode-card.expert-mode.active {
  border-color: #667eea;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.08) 0%, rgba(118, 75, 162, 0.08) 100%);
}

.mode-card.graphical-mode.active {
  border-color: #4facfe;
  background: linear-gradient(135deg, rgba(79, 172, 254, 0.08) 0%, rgba(0, 242, 254, 0.08) 100%);
}

.mode-icon-wrapper {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  transition: all 0.4s;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e7ed 100%);
}

.mode-card.expert-mode.active .mode-icon-wrapper {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.mode-card.graphical-mode.active .mode-icon-wrapper {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.mode-icon {
  color: #606266;
  transition: all 0.4s;
}

.mode-card.expert-mode.active .mode-icon {
  color: white;
}

.mode-card.graphical-mode.active .mode-icon {
  color: white;
}

.mode-title {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 8px;
  transition: all 0.3s;
}

.mode-card.active .mode-title {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.mode-card.graphical-mode.active .mode-title {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.mode-subtitle {
  font-size: 14px;
  color: #909399;
  margin-bottom: 24px;
  font-weight: 500;
  letter-spacing: 1px;
}

.mode-description {
  text-align: left;
  margin-bottom: 24px;
  flex: 1;
}

.mode-description p {
  font-size: 15px;
  color: #606266;
  margin-bottom: 16px;
  font-weight: 500;
  text-align: center;
}

.mode-features {
  list-style: none;
  padding: 0;
  margin: 0;
}

.mode-features li {
  display: flex;
  align-items: flex-start;
  margin-bottom: 12px;
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}

.mode-features li .el-icon {
  color: #67c23a;
  margin-right: 8px;
  margin-top: 2px;
  flex-shrink: 0;
}

.mode-card.active .mode-features li .el-icon {
  color: #667eea;
}

.mode-card.graphical-mode.active .mode-features li .el-icon {
  color: #4facfe;
}

.mode-example {
  width: 100%;
  margin-top: 24px;
  padding: 16px;
  background: #fafbfc;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.example-label {
  font-size: 13px;
  font-weight: 600;
  color: #909399;
  margin-bottom: 8px;
  text-align: left;
}

.example-code {
  margin: 0;
  padding: 12px;
  background: #282c34;
  color: #abb2bf;
  border-radius: 6px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  text-align: left;
  border: 1px solid #3e4451;
}

.example-text {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  text-align: left;
}

.mode-select-indicator {
  position: absolute;
  top: 16px;
  right: 16px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
  animation: fadeInScale 0.3s ease-out;
}

.mode-card.graphical-mode.active .mode-select-indicator {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  box-shadow: 0 2px 8px rgba(79, 172, 254, 0.4);
}

@keyframes fadeInScale {
  from {
    opacity: 0;
    transform: scale(0.8);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .mode-container {
    flex-direction: column;
    align-items: center;
  }
  
  .mode-card {
    max-width: 100%;
    min-height: auto;
  }
}

@media (max-width: 768px) {
  .interface-config {
    padding: 16px;
  }
  
  .step-content {
    min-height: 300px;
  }
  
  .mode-container {
    flex-direction: column;
    gap: 16px;
  }
  
  .mode-card {
    padding: 24px;
    min-height: auto;
  }
  
  .mode-icon-wrapper {
    width: 100px;
    height: 100px;
  }
  
  .mode-icon {
    font-size: 48px;
  }
  
  .mode-title {
    font-size: 20px;
  }
}
</style>
