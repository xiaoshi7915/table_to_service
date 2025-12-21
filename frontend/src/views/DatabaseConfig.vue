<template>
  <div class="database-config">
    <el-card class="main-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon class="title-icon"><Connection /></el-icon>
            <span class="title-text">数据源配置</span>
            <el-tag v-if="configs.length > 0" type="info" size="small" class="count-tag">
              {{ configs.length }}
            </el-tag>
          </div>
          <div class="header-actions">
            <el-button type="primary" @click="handleAddConfig" class="action-btn">
              <el-icon><Plus /></el-icon>
              添加配置
            </el-button>
            <el-button @click="loadConfigs" :loading="loading" class="action-btn">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>
      
      <!-- 空状态 -->
      <el-empty v-if="configs.length === 0 && !loading" description="暂无数据源配置">
        <el-button type="primary" @click="handleAddConfig">添加配置</el-button>
      </el-empty>
      
      <!-- 配置表格 -->
      <el-table 
        v-else
        :data="configs" 
        class="config-table"
        v-loading="loading"
        stripe
        :header-cell-style="{ background: '#f5f7fa', color: '#606266', fontWeight: '600' }"
      >
        <el-table-column prop="name" label="配置名称" width="150" />
        <el-table-column prop="db_type" label="数据库类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getDbTypeTagType(row.db_type)">
              {{ getDbTypeLabel(row.db_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="host" label="主机" />
        <el-table-column prop="port" label="端口" width="80" />
        <el-table-column prop="database" label="数据库" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '已激活' : '未激活' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleTest(row)" :loading="row.testing">
              测试
            </el-button>
            <el-button size="small" type="primary" @click="handleEdit(row)">
              编辑
            </el-button>
            <el-button size="small" type="success" @click="handleCopy(row)">
              复制
            </el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div v-if="configs.length > 0 || pagination.total > 0" style="margin-top: 20px; display: flex; justify-content: flex-end;">
        <el-pagination
          v-model:current-page="pagination.currentPage"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
    
    <!-- 配置对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="配置名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入配置名称" />
        </el-form-item>
        
        <el-form-item label="数据库类型" prop="db_type">
          <el-select v-model="form.db_type" placeholder="请选择数据库类型" @change="handleDbTypeChange" style="width: 100%">
            <el-option label="MySQL" value="mysql" />
            <el-option label="PostgreSQL" value="postgresql" />
            <el-option label="SQLite" value="sqlite" />
            <el-option label="SQL Server" value="sqlserver" />
            <el-option label="Oracle" value="oracle" />
          </el-select>
        </el-form-item>
        
        <el-form-item 
          v-if="form.db_type !== 'sqlite'" 
          label="主机地址" 
          prop="host"
        >
          <el-input v-model="form.host" placeholder="localhost 或 IP地址" />
        </el-form-item>
        
        <el-form-item 
          v-if="form.db_type !== 'sqlite'" 
          label="端口" 
          prop="port"
        >
          <el-input-number v-model="form.port" :min="1" :max="65535" />
        </el-form-item>
        
        <el-form-item 
          :label="form.db_type === 'sqlite' ? '数据库文件路径' : '数据库名'" 
          prop="database"
        >
          <el-input 
            v-model="form.database" 
            :placeholder="form.db_type === 'sqlite' ? '请输入数据库文件路径' : '请输入数据库名'" 
          />
        </el-form-item>
        
        <el-form-item 
          v-if="form.db_type !== 'sqlite'" 
          label="用户名" 
          prop="username"
        >
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        
        <el-form-item 
          v-if="form.db_type !== 'sqlite'" 
          label="密码" 
          prop="password"
        >
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
          />
        </el-form-item>
        
        <el-form-item 
          v-if="form.db_type === 'mysql'" 
          label="字符集"
        >
          <el-input v-model="form.charset" placeholder="utf8mb4" />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleTestConnection" :loading="testing">
            <el-icon><Connection /></el-icon>
            测试连接
          </el-button>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Connection, Refresh } from '@element-plus/icons-vue'
import api from '@/api'

const configs = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('添加配置')
const submitting = ref(false)
const testing = ref(false)
const formRef = ref(null)

const form = reactive({
  id: null,
  name: '',
  db_type: 'mysql',
  host: '',
  port: 3306,
  database: '',
  username: '',
  password: '',
  charset: 'utf8mb4',
  extra_params: null,
  is_active: true
})

// 数据库类型默认端口映射
const dbTypePorts = {
  mysql: 3306,
  postgresql: 5432,
  sqlite: null,
  sqlserver: 1433,
  oracle: 1521
}

// 数据库类型标签映射
const dbTypeLabels = {
  mysql: 'MySQL',
  postgresql: 'PostgreSQL',
  sqlite: 'SQLite',
  sqlserver: 'SQL Server',
  oracle: 'Oracle'
}

// 数据库类型标签颜色映射
const dbTypeTagTypes = {
  mysql: 'success',
  postgresql: 'primary',
  sqlite: 'info',
  sqlserver: 'warning',
  oracle: 'danger'
}

const getDbTypeLabel = (dbType) => {
  return dbTypeLabels[dbType] || dbType || 'MySQL'
}

const getDbTypeTagType = (dbType) => {
  return dbTypeTagTypes[dbType] || 'success'
}

const handleDbTypeChange = (dbType) => {
  // 根据数据库类型设置默认端口
  if (dbType !== 'sqlite' && dbTypePorts[dbType]) {
    form.port = dbTypePorts[dbType]
  }
}

const rules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  db_type: [{ required: true, message: '请选择数据库类型', trigger: 'change' }],
  host: [
    { 
      required: true, 
      message: '请输入主机地址', 
      trigger: 'blur',
      validator: (rule, value, callback) => {
        if (form.db_type === 'sqlite') {
          callback()
        } else if (!value) {
          callback(new Error('请输入主机地址'))
        } else {
          callback()
        }
      }
    }
  ],
  port: [
    { 
      required: true, 
      message: '请输入端口', 
      trigger: 'blur',
      validator: (rule, value, callback) => {
        if (form.db_type === 'sqlite') {
          callback()
        } else if (!value) {
          callback(new Error('请输入端口'))
        } else {
          callback()
        }
      }
    }
  ],
  database: [{ required: true, message: '请输入数据库名或文件路径', trigger: 'blur' }],
  username: [
    { 
      required: true, 
      message: '请输入用户名', 
      trigger: 'blur',
      validator: (rule, value, callback) => {
        if (form.db_type === 'sqlite') {
          callback()
        } else if (!value) {
          callback(new Error('请输入用户名'))
        } else {
          callback()
        }
      }
    }
  ],
  password: [
    { 
      required: true, 
      message: '请输入密码', 
      trigger: 'blur',
      validator: (rule, value, callback) => {
        if (form.db_type === 'sqlite') {
          callback()
        } else if (!value) {
          callback(new Error('请输入密码'))
        } else {
          callback()
        }
      }
    }
  ]
}

const pagination = ref({
  currentPage: 1,
  pageSize: 10,
  total: 0
})

const loadConfigs = async () => {
  loading.value = true
  try {
    const response = await api.get('/database-configs', {
      params: {
        page: pagination.value.currentPage,
        page_size: pagination.value.pageSize
      }
    })
    if (response.data.success) {
      configs.value = (response.data.data || []).map(config => ({
        ...config,
        testing: false
      }))
      // 更新分页信息
      if (response.data.pagination) {
        pagination.value.total = response.data.pagination.total || 0
      }
    }
  } catch (error) {
    console.error('加载配置失败:', error)
    ElMessage.error('加载配置失败')
    configs.value = []
  } finally {
    loading.value = false
  }
}

const handleSizeChange = (val) => {
  pagination.value.pageSize = val
  pagination.value.currentPage = 1
  loadConfigs()
}

const handleCurrentChange = (val) => {
  pagination.value.currentPage = val
  loadConfigs()
}

const handleAddConfig = () => {
  dialogTitle.value = '添加配置'
  resetForm()
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑配置'
  Object.assign(form, {
    id: row.id,
    name: row.name,
    db_type: row.db_type || 'mysql',
    host: row.host,
    port: row.port,
    database: row.database,
    username: row.username,
    password: '', // 编辑时不显示密码
    charset: row.charset || 'utf8mb4',
    extra_params: row.extra_params || null,
    is_active: row.is_active
  })
  dialogVisible.value = true
}

const handleCopy = (row) => {
  dialogTitle.value = '复制配置'
  Object.assign(form, {
    id: null,
    name: `${row.name}_副本`,
    db_type: row.db_type || 'mysql',
    host: row.host,
    port: row.port,
    database: row.database,
    username: row.username,
    password: '', // 复制时需要重新输入密码
    charset: row.charset || 'utf8mb4',
    extra_params: row.extra_params || null,
    is_active: false
  })
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除此配置吗？', '提示', {
      type: 'warning'
    })
    
    await api.delete(`/database-configs/${row.id}`)
    ElMessage.success('删除成功')
    loadConfigs()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleTest = async (row) => {
  row.testing = true
  try {
    const response = await api.post(`/database-configs/${row.id}/test`)
    if (response.data.success) {
      ElMessage.success('连接测试成功')
      // 测试成功后自动设置为已激活
      row.is_active = true
      // 重新加载配置列表以获取最新的更新时间
      await loadConfigs()
    } else {
      ElMessage.error(response.data.message || '连接测试失败')
    }
  } catch (error) {
    ElMessage.error('连接测试失败')
  } finally {
    row.testing = false
  }
}

// 格式化日期时间
const formatDateTime = (dateTimeStr) => {
  if (!dateTimeStr) return '-'
  try {
    const date = new Date(dateTimeStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  } catch (error) {
    return dateTimeStr
  }
}

const handleTestConnection = async () => {
  if (!formRef.value) return
  
  // 根据数据库类型验证必填项
  const fieldsToValidate = ['name', 'db_type', 'database']
  if (form.db_type !== 'sqlite') {
    fieldsToValidate.push('host', 'port', 'username', 'password')
  }
  
  try {
    await formRef.value.validateField(fieldsToValidate)
  } catch {
    ElMessage.warning('请先填写完整的连接信息')
    return
  }
  
  // 对于非SQLite数据库，检查密码是否为空
  if (form.db_type !== 'sqlite' && (!form.password || form.password.trim() === '')) {
    ElMessage.warning('请输入密码才能测试连接')
    return
  }
  
  testing.value = true
  try {
    // 直接测试连接（不保存配置）
    const testConfig = {
      db_type: form.db_type,
      host: form.host,
      port: form.port,
      database: form.database,
      username: form.username,
      password: form.password,
      charset: form.charset || 'utf8mb4',
      extra_params: form.extra_params
    }
    
    const response = await api.post('/database-configs/test', testConfig)
    if (response.data.success) {
      ElMessage.success('连接测试成功')
      // 安全：测试成功后不清除密码（用户可能还要保存配置）
    } else {
      ElMessage.error(response.data.message || '连接测试失败')
    }
  } catch (error) {
    const errorMsg = error.response?.data?.message || error.response?.data?.detail || '连接测试失败'
    // 如果错误信息包含换行符，使用更友好的显示方式
    if (errorMsg.includes('\n')) {
      ElMessage({
        message: errorMsg,
        type: 'error',
        duration: 10000, // 显示10秒
        showClose: true
      })
    } else {
      ElMessage.error(errorMsg)
    }
  } finally {
    testing.value = false
    // 注意：密码在HTTP请求中会以明文传输（如果使用HTTPS则传输层加密）
    // 这是测试连接的必要行为，但请确保使用HTTPS协议
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        const submitData = {
          name: form.name,
          db_type: form.db_type,
          host: form.host,
          port: form.port,
          database: form.database,
          username: form.username,
          charset: form.charset || 'utf8mb4',
          extra_params: form.extra_params,
          is_active: form.is_active
        }
        
        // 如果是编辑模式且密码为空，不更新密码（保留原有密码）
        // 如果是新增模式或密码不为空，则更新密码
        if (!form.id || (form.password && form.password.trim() !== '')) {
          submitData.password = form.password
        }
        
        if (form.id) {
          await api.put(`/database-configs/${form.id}`, submitData)
          ElMessage.success('更新成功')
        } else {
          await api.post('/database-configs', submitData)
          ElMessage.success('添加成功')
        }
        dialogVisible.value = false
        loadConfigs()
      } catch (error) {
        const errorMsg = error.response?.data?.detail || '操作失败'
        ElMessage.error(errorMsg)
      } finally {
        submitting.value = false
      }
    }
  })
}

const resetForm = () => {
  Object.assign(form, {
    id: null,
    name: '',
    db_type: 'mysql',
    host: '',
    port: 3306,
    database: '',
    username: '',
    password: '',
    charset: 'utf8mb4',
    extra_params: null,
    is_active: true
  })
  formRef.value?.clearValidate()
}

onMounted(() => {
  loadConfigs()
})
</script>

<style scoped>
.database-config {
  padding: 20px;
}

.main-card {
  border-radius: 12px;
  border: 1px solid #e4e7ed;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title-icon {
  font-size: 20px;
  color: #667eea;
}

.title-text {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.count-tag {
  margin-left: 8px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.action-btn {
  border-radius: 6px;
}

.config-table {
  width: 100%;
}

.config-table :deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}
</style>
