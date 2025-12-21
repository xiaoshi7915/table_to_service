<template>
  <div class="data-probe">
    <el-card class="main-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon class="title-icon"><Search /></el-icon>
            <span class="title-text">数据连接探查</span>
            <el-tag v-if="tasks.length > 0" type="info" size="small" class="count-tag">
              找到相关结果{{ tasks.length }}条
            </el-tag>
          </div>
          <div class="header-actions">
            <el-button type="primary" @click="handleCreateTask" class="action-btn">
              <el-icon><Plus /></el-icon>
              创建任务
            </el-button>
            <el-button @click="loadTasks" :loading="loading" class="action-btn">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>
      
      <!-- 搜索栏 -->
      <div class="search-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="请输入搜索内容（如：mysql）"
          clearable
          @clear="handleSearch"
          @keyup.enter="handleSearch"
          style="width: 300px; margin-right: 10px;"
        />
        <el-button type="primary" @click="handleSearch">搜索</el-button>
      </div>
      
      <!-- 任务表格 -->
      <el-table 
        :data="tasks" 
        class="task-table"
        v-loading="loading"
        stripe
        :header-cell-style="{ background: '#f5f7fa', color: '#606266', fontWeight: '600' }"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="task_name" label="数据连接名称" min-width="150">
          <template #default="{ row }">
            <el-link type="primary" @click="handleViewResult(row)">{{ row.task_name }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="db_type" label="数据连接类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getDbTypeTagType(row.db_type)">
              {{ getDbTypeLabel(row.db_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="database_config_name" label="服务器" min-width="120" />
        <el-table-column prop="database_config_name" label="数据库" min-width="120" />
        <el-table-column prop="scheduling_type" label="调度频率" width="100">
          <template #default="{ row }">
            {{ row.scheduling_type === 'manual' ? '手动' : '定时' }}
          </template>
        </el-table-column>
        <el-table-column prop="start_time" label="开始时间" width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.start_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="last_probe_time" label="上次探查时间" width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.last_probe_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)">
              {{ getStatusLabel(row.status) }}
            </el-tag>
            <el-progress 
              v-if="row.status === 'running'" 
              :percentage="row.progress" 
              :stroke-width="6"
              style="margin-top: 5px;"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleTest(row)" :loading="row.testing">
              测试
            </el-button>
            <el-button size="small" type="primary" @click="handleViewResult(row)">
              执行结果
            </el-button>
            <el-button 
              v-if="row.status === 'pending' || row.status === 'stopped' || row.status === 'failed'"
              size="small" 
              type="success" 
              @click="handleStart(row)"
            >
              启动
            </el-button>
            <el-button 
              v-if="row.status === 'running'"
              size="small" 
              type="warning" 
              @click="handleStop(row)"
            >
              停止
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div v-if="tasks.length > 0 || pagination.total > 0" style="margin-top: 20px; display: flex; justify-content: flex-end;">
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
    
    <!-- 启动任务对话框 -->
    <el-dialog
      v-model="startDialogVisible"
      title="启动数据连接探查任务"
      width="500px"
    >
      <div style="margin-bottom: 20px;">
        <el-icon style="color: #E6A23C; font-size: 20px;"><QuestionFilled /></el-icon>
        <span style="margin-left: 10px;">是否启动以下{{ selectedTasks.length }}个探查任务</span>
      </div>
      
      <div style="margin-left: 30px; margin-bottom: 20px;">
        <div v-for="task in selectedTasks" :key="task.id" style="margin-bottom: 5px;">
          {{ task.task_name }}
        </div>
      </div>
      
      <el-form :model="startForm" label-width="100px">
        <el-form-item label="探查方式" required>
          <el-radio-group v-model="startForm.probe_mode">
            <el-radio label="basic">基础探查</el-radio>
            <el-radio label="advanced">高级探查</el-radio>
          </el-radio-group>
          <el-tooltip content="基础探查仅探查表结构，高级探查可以对表数据和表结构进行分析">
            <el-icon style="margin-left: 5px; cursor: help;"><QuestionFilled /></el-icon>
          </el-tooltip>
        </el-form-item>
        
        <el-form-item label="调度类型" required>
          <el-select v-model="startForm.scheduling_type" style="width: 100%">
            <el-option label="手动" value="manual" />
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="startDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmStart">确定</el-button>
      </template>
    </el-dialog>
    
    <!-- 创建任务对话框 -->
    <el-dialog
      v-model="createDialogVisible"
      title="创建探查任务"
      width="500px"
    >
      <el-form
        ref="createFormRef"
        :model="createForm"
        label-width="100px"
        :rules="{
          database_config_id: [{ required: true, message: '请选择数据源', trigger: 'change' }],
          task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }]
        }"
      >
        <el-form-item label="数据源" prop="database_config_id">
          <el-select 
            v-model="createForm.database_config_id" 
            placeholder="请选择数据源"
            style="width: 100%"
            @change="handleDatabaseConfigChange"
          >
            <el-option
              v-for="config in databaseConfigs"
              :key="config.id"
              :label="config.name"
              :value="config.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="任务名称" prop="task_name">
          <el-input v-model="createForm.task_name" placeholder="请输入任务名称" />
        </el-form-item>
        
        <el-form-item label="探查方式" prop="probe_mode">
          <el-radio-group v-model="createForm.probe_mode">
            <el-radio label="basic">基础探查</el-radio>
            <el-radio label="advanced">高级探查</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="探查级别" prop="probe_level">
          <el-select v-model="createForm.probe_level" style="width: 100%">
            <el-option label="库级" value="database" />
            <el-option label="表级" value="table" />
            <el-option label="列级" value="column" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="调度类型" prop="scheduling_type">
          <el-select v-model="createForm.scheduling_type" style="width: 100%">
            <el-option label="手动" value="manual" />
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmCreateTask">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, QuestionFilled, Plus } from '@element-plus/icons-vue'
import probeApi from '@/api/probe'
import api from '@/api'

const router = useRouter()

const loading = ref(false)
const tasks = ref([])
const searchKeyword = ref('')
const startDialogVisible = ref(false)
const selectedTasks = ref([])
const startForm = ref({
  probe_mode: 'basic',
  scheduling_type: 'manual'
})

const createDialogVisible = ref(false)
const createForm = ref({
  database_config_id: null,
  task_name: '',
  probe_mode: 'basic',
  probe_level: 'database',
  scheduling_type: 'manual'
})
const databaseConfigs = ref([])
const createFormRef = ref(null)

const pagination = ref({
  currentPage: 1,
  pageSize: 10,
  total: 0
})

// 加载数据库配置列表
const loadDatabaseConfigs = async () => {
  try {
    const response = await api.get('/database-configs', {
      params: { page: 1, page_size: 1000 }
    })
    if (response.data.success) {
      databaseConfigs.value = response.data.data || []
    }
  } catch (error) {
    ElMessage.error('加载数据源配置失败')
  }
}

// 创建任务
const handleCreateTask = () => {
  createForm.value = {
    database_config_id: null,
    task_name: '',
    probe_mode: 'basic',
    probe_level: 'database',
    scheduling_type: 'manual'
  }
  createDialogVisible.value = true
  loadDatabaseConfigs()
}

// 确认创建任务
const confirmCreateTask = async () => {
  if (!createFormRef.value) return
  
  try {
    await createFormRef.value.validate()
    
    const response = await probeApi.createTask(createForm.value)
    if (response.success) {
      ElMessage.success('任务创建成功')
      createDialogVisible.value = false
      loadTasks()
    }
  } catch (error) {
    if (error !== false) { // 验证失败时error为false
      ElMessage.error('创建任务失败：' + (error.message || '未知错误'))
    }
  }
}

// 加载任务列表
const loadTasks = async () => {
  loading.value = true
  try {
    const response = await probeApi.getTasks({
      page: pagination.value.currentPage,
      page_size: pagination.value.pageSize,
      search: searchKeyword.value || undefined
    })
    
    if (response.success) {
      tasks.value = response.data || []
      pagination.value.total = response.pagination?.total || 0
    }
  } catch (error) {
    ElMessage.error('加载任务列表失败：' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.value.currentPage = 1
  loadTasks()
}

// 测试连接
const handleTest = async (task) => {
  if (task.testing) return
  
  task.testing = true
  try {
    const response = await api.post(`/database-configs/${task.database_config_id}/test`)
    if (response.data.success) {
      ElMessage.success('连接测试成功')
    } else {
      ElMessage.error('连接测试失败：' + (response.data.message || '未知错误'))
    }
  } catch (error) {
    ElMessage.error('连接测试失败：' + (error.response?.data?.detail || error.message || '未知错误'))
  } finally {
    task.testing = false
  }
}

// 查看结果
const handleViewResult = (task) => {
  router.push(`/probe-result/${task.id}`)
}

// 启动任务
const handleStart = (task) => {
  selectedTasks.value = [task]
  startForm.value.probe_mode = 'basic'
  startForm.value.scheduling_type = 'manual'
  startDialogVisible.value = true
}

// 停止任务
const handleStop = async (task) => {
  try {
    await ElMessageBox.confirm('确定要停止该探查任务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await probeApi.stopTask(task.id)
    ElMessage.success('任务已停止')
    loadTasks()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('停止任务失败：' + (error.message || '未知错误'))
    }
  }
}

// 确认启动
const confirmStart = async () => {
  try {
    for (const task of selectedTasks.value) {
      await probeApi.startTask(task.id, {
        probe_mode: startForm.value.probe_mode,
        scheduling_type: startForm.value.scheduling_type
      })
    }
    ElMessage.success('任务已启动')
    startDialogVisible.value = false
    loadTasks()
  } catch (error) {
    ElMessage.error('启动任务失败：' + (error.message || '未知错误'))
  }
}

// 分页处理
const handleSizeChange = (size) => {
  pagination.value.pageSize = size
  pagination.value.currentPage = 1
  loadTasks()
}

const handleCurrentChange = (page) => {
  pagination.value.currentPage = page
  loadTasks()
}

// 工具函数
const getDbTypeLabel = (type) => {
  const labels = {
    mysql: 'MySQL',
    postgresql: 'PostgreSQL',
    sqlite: 'SQLite',
    sqlserver: 'SQL Server',
    oracle: 'Oracle'
  }
  return labels[type] || type
}

const getDbTypeTagType = (type) => {
  const types = {
    mysql: 'success',
    postgresql: 'info',
    sqlite: 'warning',
    sqlserver: 'danger',
    oracle: ''
  }
  return types[type] || ''
}

const getStatusLabel = (status) => {
  const labels = {
    pending: '待执行',
    running: '正在运行',
    completed: '已完成',
    failed: '失败',
    stopped: '已停止'
  }
  return labels[status] || status
}

const getStatusTagType = (status) => {
  const types = {
    pending: 'info',
    running: 'primary',
    completed: 'success',
    failed: 'danger',
    stopped: 'warning'
  }
  return types[status] || ''
}

const formatDateTime = (dateTime) => {
  if (!dateTime) return '-'
  const date = new Date(dateTime)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 数据源配置变化
const handleDatabaseConfigChange = () => {
  const config = databaseConfigs.value.find(c => c.id === createForm.value.database_config_id)
  if (config && !createForm.value.task_name) {
    createForm.value.task_name = `${config.name}_探查`
  }
}

onMounted(() => {
  loadTasks()
})
</script>

<style scoped>
.data-probe {
  padding: 20px;
}

.main-card {
  min-height: calc(100vh - 100px);
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
  color: #409EFF;
}

.title-text {
  font-size: 18px;
  font-weight: 600;
}

.search-bar {
  margin-bottom: 20px;
}

.task-table {
  margin-top: 20px;
}
</style>

