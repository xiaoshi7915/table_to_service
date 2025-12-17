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
        
        <el-form-item label="主机地址" prop="host">
          <el-input v-model="form.host" placeholder="localhost 或 IP地址" />
        </el-form-item>
        
        <el-form-item label="端口" prop="port">
          <el-input-number v-model="form.port" :min="1" :max="65535" />
        </el-form-item>
        
        <el-form-item label="数据库名" prop="database">
          <el-input v-model="form.database" placeholder="请输入数据库名" />
        </el-form-item>
        
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
          />
        </el-form-item>
        
        <el-form-item label="字符集">
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
  host: '',
  port: 3306,
  database: '',
  username: '',
  password: '',
  charset: 'utf8mb4',
  is_active: true
})

const rules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  host: [{ required: true, message: '请输入主机地址', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口', trigger: 'blur' }],
  database: [{ required: true, message: '请输入数据库名', trigger: 'blur' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
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
    host: row.host,
    port: row.port,
    database: row.database,
    username: row.username,
    password: '', // 编辑时不显示密码
    charset: row.charset || 'utf8mb4',
    is_active: row.is_active
  })
  dialogVisible.value = true
}

const handleCopy = (row) => {
  dialogTitle.value = '复制配置'
  Object.assign(form, {
    id: null,
    name: `${row.name}_副本`,
    host: row.host,
    port: row.port,
    database: row.database,
    username: row.username,
    password: '', // 复制时需要重新输入密码
    charset: row.charset || 'utf8mb4',
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
    } else {
      ElMessage.error(response.data.message || '连接测试失败')
    }
  } catch (error) {
    ElMessage.error('连接测试失败')
  } finally {
    row.testing = false
  }
}

const handleTestConnection = async () => {
  if (!formRef.value) return
  
  // 只验证必填项
  try {
    await formRef.value.validateField(['host', 'port', 'database', 'username', 'password'])
  } catch {
    ElMessage.warning('请先填写完整的连接信息')
    return
  }
  
  // 检查密码是否为空
  if (!form.password || form.password.trim() === '') {
    ElMessage.warning('请输入密码才能测试连接')
    return
  }
  
  testing.value = true
  try {
    // 直接测试连接（不保存配置）
    const testConfig = {
      host: form.host,
      port: form.port,
      database: form.database,
      username: form.username,
      password: form.password,
      charset: form.charset || 'utf8mb4'
    }
    
    const response = await api.post('/database-configs/test', testConfig)
    if (response.data.success) {
      ElMessage.success('连接测试成功')
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
          host: form.host,
          port: form.port,
          database: form.database,
          username: form.username,
          charset: form.charset || 'utf8mb4',
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
    host: '',
    port: 3306,
    database: '',
    username: '',
    password: '',
    charset: 'utf8mb4',
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
