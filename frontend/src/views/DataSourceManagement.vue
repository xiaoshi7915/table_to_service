<template>
  <div class="data-source-management">
    <el-card class="main-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon class="title-icon"><Connection /></el-icon>
            <span class="title-text">数据源管理</span>
            <el-tag v-if="dataSources.length > 0" type="info" size="small" class="count-tag">
              {{ pagination.total }}
            </el-tag>
          </div>
          <div class="header-actions">
            <el-button type="primary" @click="handleAdd" class="action-btn">
              <el-icon><Plus /></el-icon>
              添加数据源
            </el-button>
            <el-button @click="loadDataSources" :loading="loading" class="action-btn">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>
      
      <!-- 数据源列表 -->
      <el-table 
        :data="dataSources" 
        class="config-table"
        v-loading="loading"
        stripe
        :header-cell-style="{ background: '#f5f7fa', color: '#606266', fontWeight: '600', textAlign: 'center' }"
      >
        <el-table-column prop="name" label="名称" min-width="150" align="center" />
        <el-table-column prop="source_type" label="类型" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.source_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sync_enabled" label="同步状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.sync_enabled ? 'success' : 'info'" size="small">
              {{ row.sync_enabled ? '已启用' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sync_frequency" label="同步频率" width="120" align="center">
          <template #default="{ row }">
            {{ row.sync_frequency ? `${row.sync_frequency}秒` : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="last_sync_at" label="最后同步" width="160" align="center">
          <template #default="{ row }">
            {{ row.last_sync_at ? formatDateTime(row.last_sync_at) : '从未同步' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" align="center">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons" style="display: flex; gap: 4px; justify-content: center; flex-wrap: nowrap;">
              <el-button size="small" @click="handleSync(row)" :loading="row.syncing">
                同步
              </el-button>
              <el-button size="small" type="primary" @click="handleEdit(row)">
                编辑
              </el-button>
              <el-button size="small" type="danger" @click="handleDelete(row)">
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div v-if="dataSources.length > 0 || pagination.total > 0" style="margin-top: 20px; display: flex; justify-content: flex-end;">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
    
    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="800px"
    >
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="120px">
        <el-form-item label="数据源类型" required prop="source_type">
          <el-select v-model="form.source_type" placeholder="请选择" @change="handleSourceTypeChange" style="width: 100%">
            <el-option label="PostgreSQL" value="postgresql" />
            <el-option label="MySQL" value="mysql" />
            <el-option label="MongoDB" value="mongodb" />
            <el-option label="S3" value="s3" />
            <el-option label="Azure Blob" value="azure_blob" />
            <el-option label="Google Drive" value="google_drive" />
            <el-option label="REST API" value="rest_api" />
            <el-option label="GraphQL" value="graphql" />
          </el-select>
        </el-form-item>
        
        <!-- 从数据库配置复制 -->
        <el-form-item label="快速配置" v-if="form.source_type === 'postgresql' || form.source_type === 'mysql'">
          <el-select 
            v-model="selectedDbConfig" 
            placeholder="从已有数据库配置复制" 
            clearable
            @change="handleCopyFromDbConfig"
            style="width: 100%"
          >
            <el-option
              v-for="dbConfig in dbConfigs"
              :key="dbConfig.id"
              :label="`${dbConfig.name} (${dbConfig.db_type})`"
              :value="dbConfig.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="名称" required prop="name">
          <el-input v-model="form.name" placeholder="数据源名称" />
        </el-form-item>
        
        <!-- 根据数据源类型显示不同的配置表单 -->
        <template v-if="form.source_type === 'postgresql' || form.source_type === 'mysql'">
          <el-form-item label="主机" prop="host">
            <el-input v-model="form.host" placeholder="数据库主机地址" />
          </el-form-item>
          <el-form-item label="端口" prop="port">
            <el-input-number v-model="form.port" :min="1" :max="65535" style="width: 100%" />
          </el-form-item>
          <el-form-item label="数据库" prop="database">
            <el-input v-model="form.database" placeholder="数据库名称" />
          </el-form-item>
          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" placeholder="数据库用户名" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input v-model="form.password" type="password" placeholder="数据库密码" show-password />
          </el-form-item>
        </template>
        
        <template v-else-if="form.source_type === 'mongodb'">
          <el-form-item label="连接字符串" prop="connection_string">
            <el-input 
              v-model="form.connection_string" 
              type="textarea" 
              :rows="2"
              placeholder="MongoDB连接字符串，例如: mongodb://username:password@host:port/database" 
            />
          </el-form-item>
        </template>
        
        <template v-else-if="form.source_type === 's3'">
          <el-form-item label="Bucket名称" prop="bucket_name">
            <el-input v-model="form.bucket_name" placeholder="S3 Bucket名称" />
          </el-form-item>
          <el-form-item label="Access Key" prop="access_key">
            <el-input v-model="form.access_key" placeholder="AWS Access Key" />
          </el-form-item>
          <el-form-item label="Secret Key" prop="secret_key">
            <el-input v-model="form.secret_key" type="password" placeholder="AWS Secret Key" show-password />
          </el-form-item>
          <el-form-item label="区域" prop="region">
            <el-input v-model="form.region" placeholder="AWS区域，例如: us-east-1" />
          </el-form-item>
        </template>
        
        <template v-else-if="form.source_type === 'azure_blob'">
          <el-form-item label="容器名称" prop="container_name">
            <el-input v-model="form.container_name" placeholder="Azure Blob容器名称" />
          </el-form-item>
          <el-form-item label="连接字符串" prop="connection_string">
            <el-input 
              v-model="form.connection_string" 
              type="textarea" 
              :rows="2"
              placeholder="Azure Storage连接字符串" 
            />
          </el-form-item>
        </template>
        
        <template v-else-if="form.source_type === 'google_drive'">
          <el-form-item label="客户端ID" prop="client_id">
            <el-input v-model="form.client_id" placeholder="Google OAuth客户端ID" />
          </el-form-item>
          <el-form-item label="客户端密钥" prop="client_secret">
            <el-input v-model="form.client_secret" type="password" placeholder="Google OAuth客户端密钥" show-password />
          </el-form-item>
          <el-form-item label="刷新令牌" prop="refresh_token">
            <el-input 
              v-model="form.refresh_token" 
              type="textarea" 
              :rows="2"
              placeholder="OAuth刷新令牌" 
            />
          </el-form-item>
        </template>
        
        <template v-else-if="form.source_type === 'rest_api' || form.source_type === 'graphql'">
          <el-form-item label="API地址" prop="api_url">
            <el-input v-model="form.api_url" placeholder="API基础URL，例如: https://api.example.com" />
          </el-form-item>
          <el-form-item label="认证方式" prop="auth_type">
            <el-select v-model="form.auth_type" placeholder="请选择" style="width: 100%">
              <el-option label="无认证" value="none" />
              <el-option label="Bearer Token" value="bearer" />
              <el-option label="API Key" value="api_key" />
              <el-option label="Basic Auth" value="basic" />
            </el-select>
          </el-form-item>
          <el-form-item 
            v-if="form.auth_type === 'bearer' || form.auth_type === 'api_key'" 
            :label="form.auth_type === 'bearer' ? 'Token' : 'API Key'"
            prop="auth_token"
          >
            <el-input v-model="form.auth_token" type="password" placeholder="认证令牌" show-password />
          </el-form-item>
          <el-form-item 
            v-if="form.auth_type === 'basic'" 
            label="用户名"
            prop="auth_username"
          >
            <el-input v-model="form.auth_username" placeholder="Basic Auth用户名" />
          </el-form-item>
          <el-form-item 
            v-if="form.auth_type === 'basic'" 
            label="密码"
            prop="auth_password"
          >
            <el-input v-model="form.auth_password" type="password" placeholder="Basic Auth密码" show-password />
          </el-form-item>
        </template>
        
        <!-- 高级配置（JSON编辑） -->
        <el-form-item label="高级配置（JSON）">
          <el-collapse>
            <el-collapse-item title="点击展开JSON配置编辑器" name="json">
              <el-input
                v-model="form.config_json"
                type="textarea"
                :rows="8"
                placeholder='JSON格式配置（高级用户）'
              />
              <div style="margin-top: 10px; font-size: 12px; color: #909399;">
                <el-button size="small" text @click="loadExampleConfig">加载示例配置</el-button>
                <el-button size="small" text @click="formatJson">格式化JSON</el-button>
              </div>
            </el-collapse-item>
          </el-collapse>
        </el-form-item>
        
        <el-form-item label="启用同步">
          <el-switch v-model="form.sync_enabled" />
        </el-form-item>
        <el-form-item label="同步频率(秒)" v-if="form.sync_enabled">
          <el-input-number v-model="form.sync_frequency" :min="60" :step="60" style="width: 100%" />
          <div style="font-size: 12px; color: #909399; margin-top: 5px;">
            {{ formatFrequency(form.sync_frequency) }}
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Connection, Plus, Refresh } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const dataSources = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('添加数据源')
const editingId = ref(null)
const submitting = ref(false)
const formRef = ref(null)
const dbConfigs = ref([])
const selectedDbConfig = ref(null)

// 配置示例
const configExamples = {
  postgresql: {
    connection_string: 'postgresql://username:password@host:port/database'
  },
  mysql: {
    connection_string: 'mysql://username:password@host:port/database'
  },
  mongodb: {
    connection_string: 'mongodb://username:password@host:port/database'
  },
  s3: {
    bucket_name: 'my-bucket',
    access_key: 'your-access-key',
    secret_key: 'your-secret-key',
    region: 'us-east-1'
  },
  azure_blob: {
    container_name: 'my-container',
    connection_string: 'DefaultEndpointsProtocol=https;AccountName=...'
  },
  google_drive: {
    client_id: 'your-client-id',
    client_secret: 'your-client-secret',
    refresh_token: 'your-refresh-token'
  },
  rest_api: {
    api_url: 'https://api.example.com',
    auth_type: 'bearer',
    auth_token: 'your-token'
  },
  graphql: {
    api_url: 'https://api.example.com/graphql',
    auth_type: 'bearer',
    auth_token: 'your-token'
  }
}

const form = reactive({
  source_type: '',
  name: '',
  // 关系型数据库字段
  host: '',
  port: 5432,
  database: '',
  username: '',
  password: '',
  // MongoDB字段
  connection_string: '',
  // S3字段
  bucket_name: '',
  access_key: '',
  secret_key: '',
  region: '',
  // Azure Blob字段
  container_name: '',
  // Google Drive字段
  client_id: '',
  client_secret: '',
  refresh_token: '',
  // API字段
  api_url: '',
  auth_type: 'none',
  auth_token: '',
  auth_username: '',
  auth_password: '',
  // 通用字段
  config_json: '{}',
  sync_enabled: true,
  sync_frequency: 3600
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

// 表单验证规则
const formRules = {
  source_type: [
    { required: true, message: '请选择数据源类型', trigger: 'change' }
  ],
  name: [
    { required: true, message: '请输入数据源名称', trigger: 'blur' },
    { min: 1, max: 100, message: '长度在 1 到 100 个字符', trigger: 'blur' }
  ]
}

// 加载数据库配置列表（用于复制）
const loadDbConfigs = async () => {
  try {
    const response = await request.get('/database-configs', { params: { page: 1, page_size: 100 } })
    if (response.data.code === 200) {
      dbConfigs.value = response.data.data || []
    }
  } catch (error) {
    console.error('加载数据库配置失败:', error)
  }
}

// 从数据库配置复制
const handleCopyFromDbConfig = (configId) => {
  if (!configId) return
  
  const dbConfig = dbConfigs.value.find(c => c.id === configId)
  if (!dbConfig) return
  
  // 根据数据库类型设置数据源类型
  if (dbConfig.db_type === 'postgresql') {
    form.source_type = 'postgresql'
    form.port = dbConfig.port || 5432
  } else if (dbConfig.db_type === 'mysql') {
    form.source_type = 'mysql'
    form.port = dbConfig.port || 3306
  }
  
  form.host = dbConfig.host || ''
  form.database = dbConfig.database || ''
  form.username = dbConfig.username || ''
  form.name = `${dbConfig.name}_sync` // 自动生成名称
  
  // 更新JSON配置
  updateConfigJson()
  
  ElMessage.success('已从数据库配置复制信息')
}

// 数据源类型变化时重置表单
const handleSourceTypeChange = () => {
  // 重置所有字段
  Object.assign(form, {
    host: '',
    port: form.source_type === 'postgresql' ? 5432 : form.source_type === 'mysql' ? 3306 : 3306,
    database: '',
    username: '',
    password: '',
    connection_string: '',
    bucket_name: '',
    access_key: '',
    secret_key: '',
    region: '',
    container_name: '',
    client_id: '',
    client_secret: '',
    refresh_token: '',
    api_url: '',
    auth_type: 'none',
    auth_token: '',
    auth_username: '',
    auth_password: '',
    config_json: '{}'
  })
  
  // 加载示例配置
  loadExampleConfig()
}

// 加载示例配置
const loadExampleConfig = () => {
  if (!form.source_type) return
  
  const example = configExamples[form.source_type]
  if (example) {
    form.config_json = JSON.stringify(example, null, 2)
  }
}

// 格式化JSON
const formatJson = () => {
  try {
    const parsed = JSON.parse(form.config_json)
    form.config_json = JSON.stringify(parsed, null, 2)
    ElMessage.success('JSON格式化成功')
  } catch (e) {
    ElMessage.error('JSON格式错误，无法格式化')
  }
}

// 根据表单字段更新JSON配置
const updateConfigJson = () => {
  const config = {}
  
  if (form.source_type === 'postgresql' || form.source_type === 'mysql') {
    // 构建连接字符串
    const password = form.password ? `:${form.password}` : ''
    const auth = form.username ? `${form.username}${password}@` : ''
    config.connection_string = `${form.source_type}://${auth}${form.host}:${form.port}/${form.database}`
    // 也保存单独字段
    config.host = form.host
    config.port = form.port
    config.database = form.database
    config.username = form.username
    if (form.password) config.password = form.password
  } else if (form.source_type === 'mongodb') {
    config.connection_string = form.connection_string
  } else if (form.source_type === 's3') {
    config.bucket_name = form.bucket_name
    config.access_key = form.access_key
    if (form.secret_key) config.secret_key = form.secret_key
    config.region = form.region
  } else if (form.source_type === 'azure_blob') {
    config.container_name = form.container_name
    config.connection_string = form.connection_string
  } else if (form.source_type === 'google_drive') {
    config.client_id = form.client_id
    if (form.client_secret) config.client_secret = form.client_secret
    config.refresh_token = form.refresh_token
  } else if (form.source_type === 'rest_api' || form.source_type === 'graphql') {
    config.api_url = form.api_url
    config.auth_type = form.auth_type
    if (form.auth_token) config.auth_token = form.auth_token
    if (form.auth_username) config.auth_username = form.auth_username
    if (form.auth_password) config.auth_password = form.auth_password
  }
  
  form.config_json = JSON.stringify(config, null, 2)
}

// 从JSON配置加载到表单字段
const loadConfigFromJson = () => {
  try {
    const config = JSON.parse(form.config_json || '{}')
    
    if (form.source_type === 'postgresql' || form.source_type === 'mysql') {
      // 尝试从连接字符串解析
      if (config.connection_string) {
        const match = config.connection_string.match(/(\w+):\/\/(?:([^:]+):([^@]+)@)?([^:]+):(\d+)\/(.+)/)
        if (match) {
          form.username = match[2] || ''
          form.password = match[3] || ''
          form.host = match[4] || ''
          form.port = parseInt(match[5]) || (form.source_type === 'postgresql' ? 5432 : 3306)
          form.database = match[6] || ''
        }
      }
      // 从单独字段加载
      if (config.host) form.host = config.host
      if (config.port) form.port = config.port
      if (config.database) form.database = config.database
      if (config.username) form.username = config.username
      if (config.password) form.password = config.password
    } else if (form.source_type === 'mongodb') {
      form.connection_string = config.connection_string || ''
    } else if (form.source_type === 's3') {
      form.bucket_name = config.bucket_name || ''
      form.access_key = config.access_key || ''
      form.secret_key = config.secret_key || ''
      form.region = config.region || ''
    } else if (form.source_type === 'azure_blob') {
      form.container_name = config.container_name || ''
      form.connection_string = config.connection_string || ''
    } else if (form.source_type === 'google_drive') {
      form.client_id = config.client_id || ''
      form.client_secret = config.client_secret || ''
      form.refresh_token = config.refresh_token || ''
    } else if (form.source_type === 'rest_api' || form.source_type === 'graphql') {
      form.api_url = config.api_url || ''
      form.auth_type = config.auth_type || 'none'
      form.auth_token = config.auth_token || ''
      form.auth_username = config.auth_username || ''
      form.auth_password = config.auth_password || ''
    }
  } catch (e) {
    console.error('解析配置JSON失败:', e)
  }
}

// 加载数据源列表
const loadDataSources = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size
    }
    
    const response = await request.get('/data-sources', { params })
    if (response.data.code === 200) {
      dataSources.value = response.data.data.data_sources || []
      pagination.total = response.data.data.total || 0
    }
  } catch (error) {
    console.error('加载数据源列表失败:', error)
    ElMessage.error('加载数据源列表失败')
  } finally {
    loading.value = false
  }
}

// 添加
const handleAdd = () => {
  editingId.value = null
  dialogTitle.value = '添加数据源'
  selectedDbConfig.value = null
  Object.assign(form, {
    source_type: '',
    name: '',
    host: '',
    port: 5432,
    database: '',
    username: '',
    password: '',
    connection_string: '',
    bucket_name: '',
    access_key: '',
    secret_key: '',
    region: '',
    container_name: '',
    client_id: '',
    client_secret: '',
    refresh_token: '',
    api_url: '',
    auth_type: 'none',
    auth_token: '',
    auth_username: '',
    auth_password: '',
    config_json: '{}',
    sync_enabled: true,
    sync_frequency: 3600
  })
  dialogVisible.value = true
  loadDbConfigs()
}

// 编辑
const handleEdit = (row) => {
  editingId.value = row.id
  dialogTitle.value = '编辑数据源'
  selectedDbConfig.value = null
  
  form.source_type = row.source_type
  form.name = row.name
  form.sync_enabled = row.sync_enabled
  form.sync_frequency = row.sync_frequency || 3600
  
  // 加载配置JSON
  form.config_json = JSON.stringify(row.config || {}, null, 2)
  
  // 从JSON加载到表单字段
  loadConfigFromJson()
  
  dialogVisible.value = true
  loadDbConfigs()
}

// 提交
const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    // 表单验证
    await formRef.value.validate()
    
    // 更新JSON配置
    updateConfigJson()
    
    submitting.value = true
    
    const config = JSON.parse(form.config_json)
    
    const data = {
      source_type: form.source_type,
      name: form.name,
      config: config,
      sync_enabled: form.sync_enabled,
      sync_frequency: form.sync_enabled ? form.sync_frequency : null
    }
    
    if (editingId.value) {
      await request.put(`/data-sources/${editingId.value}`, data)
      ElMessage.success('更新成功')
    } else {
      await request.post('/data-sources', data)
      ElMessage.success('创建成功')
    }
    
    dialogVisible.value = false
    loadDataSources()
  } catch (error) {
    if (error !== false) { // 表单验证失败时 error 为 false
      console.error('提交失败:', error)
      ElMessage.error('提交失败: ' + (error.response?.data?.detail || error.message || '未知错误'))
    }
  } finally {
    submitting.value = false
  }
}

// 同步
const handleSync = async (row) => {
  row.syncing = true
  try {
    const response = await request.post(`/data-sources/${row.id}/sync`)
    if (response.data.code === 200) {
      ElMessage.success('同步成功')
      loadDataSources()
    }
  } catch (error) {
    console.error('同步失败:', error)
    ElMessage.error('同步失败')
  } finally {
    row.syncing = false
  }
}

// 删除
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该数据源吗？', '提示', {
      type: 'warning'
    })
    
    const response = await request.delete(`/data-sources/${row.id}`)
    if (response.data.code === 200) {
      ElMessage.success('删除成功')
      loadDataSources()
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 分页
const handleSizeChange = () => {
  loadDataSources()
}

const handleCurrentChange = () => {
  loadDataSources()
}

// 格式化频率
const formatFrequency = (seconds) => {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}小时`
  return `${Math.floor(seconds / 86400)}天`
}

// 格式化日期时间
const formatDateTime = (dateTime) => {
  if (!dateTime) return '-'
  return new Date(dateTime).toLocaleString('zh-CN')
}

onMounted(() => {
  loadDataSources()
  loadDbConfigs()
})
</script>

<style scoped>
.data-source-management {
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 60px);
}

.main-card {
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.main-card :deep(.el-card__header) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 8px 8px 0 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-icon {
  font-size: 24px;
  color: white;
}

.title-text {
  font-size: 20px;
  font-weight: 600;
  color: white;
}

.count-tag {
  margin-left: 10px;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.action-btn {
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
}

.config-table {
  margin-top: 20px;
}

.config-table :deep(.el-table__header) {
  background: #fafafa;
}

.config-table :deep(.el-table__row:hover) {
  background: #f0f9ff;
}

.action-buttons {
  display: flex;
  gap: 4px;
  justify-content: center;
  flex-wrap: nowrap;
}

.action-buttons .el-button {
  margin: 0;
}

/* 对话框样式优化 */
:deep(.el-dialog__header) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  margin: 0;
  border-radius: 8px 8px 0 0;
}

:deep(.el-dialog__title) {
  color: white;
  font-weight: 600;
}

:deep(.el-dialog__headerbtn .el-dialog__close) {
  color: white;
}

:deep(.el-dialog__headerbtn:hover .el-dialog__close) {
  color: #f0f0f0;
}

/* 表单样式优化 */
:deep(.el-form-item__label) {
  font-weight: 500;
  color: #606266;
}

:deep(.el-input__inner),
:deep(.el-textarea__inner) {
  border-radius: 4px;
}

:deep(.el-select) {
  width: 100%;
}
</style>
