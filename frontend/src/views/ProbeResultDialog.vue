<template>
  <div class="probe-result-dialog">
    <div class="dialog-header">
      <div class="header-info">
        <span class="task-name">{{ taskName }}</span>
        <el-tag :type="getStatusType(taskStatus)" size="small" style="margin-left: 10px;">
          {{ getStatusLabel(taskStatus) }}
        </el-tag>
        <el-progress 
          v-if="taskStatus === 'running' && taskProgress >= 0" 
          :percentage="taskProgress" 
          :status="taskStatus === 'completed' ? 'success' : ''"
          style="width: 200px; margin-left: 15px;"
        />
        <!-- 探查模式切换 -->
        <div style="margin-left: 20px;">
          <el-radio-group v-model="currentProbeMode" size="small" @change="handleProbeModeChange">
            <el-radio-button label="basic">基础探查</el-radio-button>
            <el-radio-button label="advanced">高级探查</el-radio-button>
          </el-radio-group>
        </div>
      </div>
      <div class="header-actions">
        <el-button type="primary" size="small" @click="handleExport('excel')">导出Excel</el-button>
        <el-button size="small" @click="handleExport('csv')">导出CSV</el-button>
        <el-button size="small" @click="handleExport('json')">导出JSON</el-button>
        <el-button type="success" size="small" @click="handleImportToKnowledge">导入到知识库</el-button>
        <el-button size="small" @click="loadData" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>
    
    <!-- Tab页 -->
    <el-tabs v-model="activeTab" @tab-change="handleTabChange" style="margin-top: 20px;">
      <el-tab-pane label="库级" name="database">
        <!-- 库级探查结果 -->
        <div v-if="databaseResult" class="database-section">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="数据库名">{{ databaseResult.database_name }}</el-descriptions-item>
            <el-descriptions-item label="数据库类型">{{ databaseResult.db_type }}</el-descriptions-item>
            <el-descriptions-item label="总大小">{{ databaseResult.total_size_mb || '-' }} MB</el-descriptions-item>
            <el-descriptions-item v-if="currentProbeMode === 'advanced'" label="增长速率">{{ databaseResult.growth_rate || '-' }}</el-descriptions-item>
            <el-descriptions-item label="表数量">{{ databaseResult.table_count || 0 }}</el-descriptions-item>
            <el-descriptions-item label="视图数量">{{ databaseResult.view_count || 0 }}</el-descriptions-item>
            <el-descriptions-item label="函数数量">{{ databaseResult.function_count || 0 }}</el-descriptions-item>
            <el-descriptions-item label="存储过程数量">{{ databaseResult.procedure_count || 0 }}</el-descriptions-item>
            <el-descriptions-item label="触发器数量">{{ databaseResult.trigger_count || 0 }}</el-descriptions-item>
            <el-descriptions-item label="事件数量">{{ databaseResult.event_count || 0 }}</el-descriptions-item>
            <el-descriptions-item label="序列数量">{{ databaseResult.sequence_count || 0 }}</el-descriptions-item>
          </el-descriptions>
          
          <!-- TOP N大表（高级探查显示） -->
          <div v-if="currentProbeMode === 'advanced' && databaseResult.top_n_tables" style="margin-top: 20px;">
            <h4>TOP N 大表</h4>
            <el-table :data="formatTopTables(databaseResult.top_n_tables)" stripe max-height="200">
              <el-table-column prop="table_name" label="表名" />
              <el-table-column prop="size_mb" label="大小(MB)" />
            </el-table>
          </div>
          
          <!-- 冷热表（高级探查显示） -->
          <div v-if="currentProbeMode === 'advanced' && (databaseResult.cold_tables || databaseResult.hot_tables)" style="margin-top: 20px;">
            <el-row :gutter="20">
              <el-col v-if="databaseResult.cold_tables" :span="12">
                <h4>冷表</h4>
                <el-table :data="formatTopTables(databaseResult.cold_tables)" stripe max-height="200">
                  <el-table-column prop="table_name" label="表名" />
                </el-table>
              </el-col>
              <el-col v-if="databaseResult.hot_tables" :span="12">
                <h4>热表</h4>
                <el-table :data="formatTopTables(databaseResult.hot_tables)" stripe max-height="200">
                  <el-table-column prop="table_name" label="表名" />
                </el-table>
              </el-col>
            </el-row>
          </div>
        </div>
        <el-empty v-else description="暂无库级探查结果" />
      </el-tab-pane>
      
      <el-tab-pane label="表" name="tables">
        <!-- 表列表 -->
        <div class="table-list-section">
          <div class="search-bar">
            <span>表名:</span>
            <el-input
              v-model="tableSearchKeyword"
              placeholder="请输入搜索内容"
              clearable
              style="width: 300px; margin-left: 10px; margin-right: 10px;"
              @keyup.enter="loadTableResults"
            />
            <el-button type="primary" @click="loadTableResults">搜索</el-button>
          </div>
          
          <el-table 
            ref="tableRef"
            :data="tableResults" 
            class="result-table"
            v-loading="loading"
            stripe
            @row-click="handleTableRowClick"
            max-height="400"
          >
            <el-table-column prop="table_name" label="表名" min-width="150">
              <template #default="{ row }">
                <el-link type="primary" @click.stop="handleSelectTable(row)">{{ row.table_name }}</el-link>
              </template>
            </el-table-column>
            <el-table-column prop="column_count" label="字段数" width="100" />
            <el-table-column prop="primary_key" label="主键" min-width="120">
              <template #default="{ row }">
                {{ formatPrimaryKey(row.primary_key) }}
              </template>
            </el-table-column>
            <el-table-column prop="row_count" label="数据量" width="120" />
            <!-- 高级探查显示额外字段 -->
            <el-table-column v-if="currentProbeMode === 'advanced'" prop="table_size_mb" label="表大小(MB)" width="120" />
            <el-table-column v-if="currentProbeMode === 'advanced'" prop="index_size_mb" label="索引大小(MB)" width="120" />
            <el-table-column v-if="currentProbeMode === 'advanced'" prop="is_hot_table" label="热表" width="80">
              <template #default="{ row }">
                <el-tag v-if="row.is_hot_table" type="danger" size="small">是</el-tag>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column v-if="currentProbeMode === 'advanced'" prop="is_cold_table" label="冷表" width="80">
              <template #default="{ row }">
                <el-tag v-if="row.is_cold_table" type="info" size="small">是</el-tag>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="comment" label="表注释" min-width="150" />
          </el-table>
          
          <!-- 分页 -->
          <div style="margin-top: 20px; display: flex; justify-content: flex-end;">
            <el-pagination
              v-model:current-page="tablePagination.currentPage"
              v-model:page-size="tablePagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="tablePagination.total"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleTableSizeChange"
              @current-change="handleTableCurrentChange"
            />
          </div>
        </div>
      </el-tab-pane>
      
      <el-tab-pane label="字段" name="columns">
        <div v-if="selectedTable" class="details-section">
          <h3>{{ selectedTable.table_name }} 表详情</h3>
          
          <!-- 字段列表 -->
          <div v-if="columnResults.length > 0" class="column-list">
            <h4>字段信息</h4>
            <el-table :data="columnResults" stripe max-height="400">
              <el-table-column prop="column_name" label="字段名" width="150" />
              <el-table-column prop="data_type" label="数据类型" width="120" />
              <el-table-column prop="nullable" label="可空" width="80">
                <template #default="{ row }">
                  {{ row.nullable ? '是' : '否' }}
                </template>
              </el-table-column>
              <!-- 高级探查显示额外字段 -->
              <el-table-column v-if="currentProbeMode === 'advanced'" prop="non_null_rate" label="非空率" width="100" />
              <el-table-column v-if="currentProbeMode === 'advanced'" prop="distinct_count" label="唯一值数" width="100" />
              <el-table-column v-if="currentProbeMode === 'advanced'" prop="duplicate_rate" label="重复率" width="100" />
              <el-table-column v-if="currentProbeMode === 'advanced'" prop="max_length" label="最大长度" width="100" />
              <el-table-column v-if="currentProbeMode === 'advanced'" prop="min_length" label="最小长度" width="100" />
              <el-table-column v-if="currentProbeMode === 'advanced'" prop="avg_length" label="平均长度" width="100" />
              <el-table-column v-if="currentProbeMode === 'advanced'" prop="max_value" label="最大值" width="120" />
              <el-table-column v-if="currentProbeMode === 'advanced'" prop="min_value" label="最小值" width="120" />
              <el-table-column prop="comment" label="注释" min-width="150" />
            </el-table>
            
            <!-- 高级探查显示Top值和敏感信息 -->
            <div v-if="currentProbeMode === 'advanced' && selectedTable" style="margin-top: 20px;">
              <el-collapse v-model="activeColumnDetails">
                <el-collapse-item 
                  v-for="column in columnResults" 
                  :key="column.id"
                  :title="column.column_name"
                  :name="column.id"
                >
                  <div v-if="column.top_values && column.top_values.length > 0">
                    <h5>Top 值</h5>
                    <el-table :data="formatTopValues(column.top_values)" stripe max-height="200" size="small">
                      <el-table-column prop="value" label="值" />
                      <el-table-column prop="count" label="次数" width="100" />
                    </el-table>
                  </div>
                  <div v-if="column.sensitive_info && column.sensitive_info.is_sensitive" style="margin-top: 10px;">
                    <el-alert
                      type="warning"
                      :title="`检测到敏感信息: ${column.sensitive_info.type || '未知类型'}`"
                      :closable="false"
                      show-icon
                    />
                  </div>
                  <div v-if="column.data_quality_issues && column.data_quality_issues.length > 0" style="margin-top: 10px;">
                    <h5>数据质量问题</h5>
                    <el-tag 
                      v-for="(issue, idx) in column.data_quality_issues" 
                      :key="idx"
                      type="warning"
                      style="margin-right: 5px;"
                    >
                      {{ issue }}
                    </el-tag>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </div>
          
          <!-- 示例数据 -->
          <div v-if="sampleData.length > 0" class="sample-data" style="margin-top: 20px;">
            <h4>示例数据</h4>
            <el-table :data="sampleData" stripe max-height="300">
              <el-table-column
                v-for="col in sampleColumns"
                :key="col"
                :prop="col"
                :label="col"
                min-width="120"
              />
            </el-table>
          </div>
          
          <el-empty v-if="columnResults.length === 0" description="暂无字段信息" />
        </div>
        <el-empty v-else description="请先选择表查看字段信息" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import probeApi from '@/api/probe'
import api from '@/api'

const props = defineProps({
  taskId: {
    type: Number,
    required: false
  },
  taskName: {
    type: String,
    default: ''
  },
  databaseConfigId: {
    type: Number,
    required: false
  },
  probeMode: {
    type: String,
    default: 'basic'
  }
})

const loading = ref(false)
const activeTab = ref('database')
const tableSearchKeyword = ref('')
const tableResults = ref([])
const selectedTable = ref(null)
const columnResults = ref([])
const sampleData = ref([])
const sampleColumns = ref([])
const taskStatus = ref('')
const taskProgress = ref(0)
const databaseResult = ref(null)
const tableRef = ref(null)
const activeColumnDetails = ref([])
const currentProbeMode = ref(props.probeMode || 'basic')

const tablePagination = ref({
  currentPage: 1,
  pageSize: 10,
  total: 0
})

// 加载任务信息
const loadTaskInfo = async () => {
  try {
    // 如果有databaseConfigId但没有taskId，使用默认任务（表级任务）
    let taskId = props.taskId
    if (props.databaseConfigId && !taskId) {
      const taskResponse = await probeApi.getTaskByDatabaseConfig(
        props.databaseConfigId,
        currentProbeMode.value,
        'table'
      )
      if (taskResponse.success && taskResponse.data) {
        taskId = taskResponse.data.id
      }
    }
    
    if (!taskId) {
      return
    }
    
    const response = await probeApi.getTask(taskId)
    if (response.success) {
      taskStatus.value = response.data.status || ''
      taskProgress.value = response.data.progress || 0
    }
  } catch (error) {
    console.error('加载任务信息失败:', error)
  }
}

// 探查模式切换处理
const handleProbeModeChange = (mode) => {
  currentProbeMode.value = mode
  // 重新加载数据
  loadData()
}

// 加载库级结果
const loadDatabaseResult = async () => {
  try {
    // 如果有databaseConfigId，查找库级任务（库级结果必须使用库级任务的ID）
    let taskId = null
    if (props.databaseConfigId) {
      const taskResponse = await probeApi.getTaskByDatabaseConfig(
        props.databaseConfigId,
        currentProbeMode.value,
        'database'
      )
      if (taskResponse.success && taskResponse.data) {
        taskId = taskResponse.data.id
      }
    } else if (props.taskId) {
      // 如果没有databaseConfigId，检查当前taskId是否是库级任务
      const taskResponse = await probeApi.getTask(props.taskId)
      if (taskResponse.success && taskResponse.data && taskResponse.data.probe_level === 'database') {
        taskId = props.taskId
      }
    }
    
    if (!taskId) {
      databaseResult.value = null
      return
    }
    
    const response = await probeApi.getDatabaseResult(taskId)
    if (response.success) {
      databaseResult.value = response.data
    } else {
      databaseResult.value = null
    }
  } catch (error) {
    console.error('加载库级结果失败:', error)
    databaseResult.value = null
  }
}

// 格式化TOP表数据
const formatTopTables = (topTables) => {
  if (!topTables) return []
  if (typeof topTables === 'string') {
    try {
      return JSON.parse(topTables)
    } catch {
      return []
    }
  }
  return Array.isArray(topTables) ? topTables : []
}

// 格式化Top值数据
const formatTopValues = (topValues) => {
  if (!topValues) return []
  if (typeof topValues === 'string') {
    try {
      return JSON.parse(topValues)
    } catch {
      return []
    }
  }
  return Array.isArray(topValues) ? topValues : []
}

// 不再需要轮询，按钮状态由父组件控制

// 加载表结果
const loadTableResults = async () => {
  loading.value = true
  try {
    // 如果有databaseConfigId，先查找表级任务
    let taskId = props.taskId
    if (props.databaseConfigId && !taskId) {
      const taskResponse = await probeApi.getTaskByDatabaseConfig(
        props.databaseConfigId,
        currentProbeMode.value,
        'table'
      )
      if (taskResponse.success && taskResponse.data) {
        taskId = taskResponse.data.id
      }
    }
    
    if (!taskId) {
      tableResults.value = []
      tablePagination.value.total = 0
      loading.value = false
      return
    }
    
    const response = await probeApi.getTableResults(taskId, {
      page: tablePagination.value.currentPage,
      page_size: tablePagination.value.pageSize,
      search: tableSearchKeyword.value || undefined
    })
    if (response.success) {
      tableResults.value = response.data || []
      tablePagination.value.total = response.pagination?.total || 0
    }
  } catch (error) {
    ElMessage.error('加载表结果失败')
  } finally {
    loading.value = false
  }
}

// Tab切换
const handleTabChange = (tabName) => {
  if (tabName === 'database') {
    loadDatabaseResult()
  } else if (tabName === 'tables') {
    loadTableResults()
  } else if (tabName === 'columns') {
    if (tableResults.value.length > 0 && !selectedTable.value) {
      selectedTable.value = tableResults.value[0]
      loadColumnResults()
      loadSampleData()
    }
  }
}

// 选择表查看字段
const handleSelectTable = (table) => {
  selectedTable.value = table
  activeTab.value = 'columns'
  loadColumnResults()
  loadSampleData()
}

// 表格行点击
const handleTableRowClick = (row) => {
  handleSelectTable(row)
}

// 加载列结果
const loadColumnResults = async () => {
  if (!selectedTable.value) return
  
  try {
    // 如果有databaseConfigId，查找包含字段级结果的任务
    // 字段级结果可能保存在 column、all 或 table 级别的任务中
    let taskId = props.taskId
    if (props.databaseConfigId && !taskId) {
      // 按优先级查找：column -> all -> table
      const probeLevels = ['column', 'all', 'table']
      let foundTask = null
      
      for (const level of probeLevels) {
        const taskResponse = await probeApi.getTaskByDatabaseConfig(
          props.databaseConfigId,
          currentProbeMode.value,
          level
        )
        if (taskResponse.success && taskResponse.data && taskResponse.data.status === 'completed') {
          foundTask = taskResponse.data
          taskId = taskResponse.data.id
          break
        }
      }
    }
    
    if (!taskId) {
      columnResults.value = []
      return
    }
    
    const response = await probeApi.getColumnResults(taskId, selectedTable.value.table_name)
    if (response.success) {
      const rawData = response.data || []
      
      // 去重：如果有重复的字段名，只保留第一个
      const seen = new Set()
      columnResults.value = rawData.filter(item => {
        if (seen.has(item.column_name)) {
          return false
        }
        seen.add(item.column_name)
        return true
      })
    } else {
      columnResults.value = []
    }
  } catch (error) {
    console.error('加载列结果失败:', error)
    columnResults.value = []
  }
}

// 加载示例数据
const loadSampleData = async () => {
  if (!selectedTable.value) return
  
  try {
    // 如果有databaseConfigId，直接使用；否则从task中获取
    let databaseConfigId = props.databaseConfigId
    if (!databaseConfigId) {
      // 如果有databaseConfigId但没有taskId，先查找表级任务
      let taskId = props.taskId
      if (!taskId) {
        return
      }
      const taskResponse = await probeApi.getTask(taskId)
      if (taskResponse.success && taskResponse.data) {
        databaseConfigId = taskResponse.data.database_config_id
      } else {
        return
      }
    } else {
      // 如果已经有databaseConfigId，直接使用
    }
    
    if (!databaseConfigId) {
      return
    }
    
    const response = await api.get(`/database-configs/${databaseConfigId}/tables/${selectedTable.value.table_name}/sample`, {
      params: { limit: 10 }
    })
    
    if (response.data.success && response.data.data) {
      const data = response.data.data
      if (Array.isArray(data) && data.length > 0) {
        sampleData.value = data
        sampleColumns.value = Object.keys(data[0])
      } else {
        sampleData.value = []
        sampleColumns.value = []
      }
    }
  } catch (error) {
    console.error('加载示例数据失败:', error)
    sampleData.value = []
    sampleColumns.value = []
  }
}

// 分页处理
const handleTableSizeChange = (size) => {
  tablePagination.value.pageSize = size
  tablePagination.value.currentPage = 1
  loadTableResults()
}

const handleTableCurrentChange = (page) => {
  tablePagination.value.currentPage = page
  loadTableResults()
}

// 格式化主键
const formatPrimaryKey = (primaryKey) => {
  if (!primaryKey) return '-'
  if (typeof primaryKey === 'string') {
    try {
      const pk = JSON.parse(primaryKey)
      return Array.isArray(pk) ? pk.join(', ') : pk
    } catch {
      return primaryKey
    }
  }
  return Array.isArray(primaryKey) ? primaryKey.join(', ') : '-'
}

// 获取状态类型
const getStatusType = (status) => {
  const types = {
    'pending': 'info',
    'running': 'warning',
    'completed': 'success',
    'failed': 'danger',
    'stopped': 'info'
  }
  return types[status] || 'info'
}

// 获取状态标签
const getStatusLabel = (status) => {
  const labels = {
    'pending': '待执行',
    'running': '运行中',
    'completed': '已完成',
    'failed': '失败',
    'stopped': '已停止'
  }
  return labels[status] || status
}

// 导出
const handleExport = async (format) => {
  try {
    // 获取taskId（可能需要根据不同的导出类型查找不同的任务）
    let taskId = props.taskId
    if (!taskId && props.databaseConfigId) {
      // 如果没有taskId，尝试查找任务
      // 对于导出，优先使用表级任务（因为表级任务通常包含最完整的数据）
      const taskResponse = await probeApi.getTaskByDatabaseConfig(
        props.databaseConfigId,
        currentProbeMode.value,
        'table'
      )
      if (taskResponse.success && taskResponse.data) {
        taskId = taskResponse.data.id
      }
    }
    
    if (!taskId) {
      ElMessage.error('无法找到探查任务')
      return
    }
    
    // 使用axios下载文件，确保认证头正确传递
    const authStore = useAuthStore()
    const token = authStore.token
    
    if (!token) {
      ElMessage.error('未登录，请先登录')
      return
    }
    
    // 使用axios的request工具，它会自动添加认证头和baseURL
    const response = await api.get(`/probe-results/task/${taskId}/export`, {
      params: { format },
      responseType: 'blob', // 重要：设置为blob以处理二进制文件
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    
    // 根据格式确定文件扩展名
    let fileExt = format
    if (format === 'excel') {
      fileExt = 'xlsx'
    } else if (format === 'csv') {
      fileExt = 'csv'
    } else if (format === 'json') {
      fileExt = 'json'
    }
    
    // 创建下载链接
    const blob = new Blob([response.data])
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `probe_result_${taskId}_${new Date().getTime()}.${fileExt}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('导出成功')
  } catch (error) {
    let errorMsg = '未知错误'
    if (error.response?.data) {
      // 如果错误响应是blob，尝试解析为JSON
      if (error.response.data instanceof Blob) {
        try {
          const text = await error.response.data.text()
          const errorData = JSON.parse(text)
          errorMsg = errorData.detail || errorData.message || text
        } catch {
          errorMsg = '导出失败'
        }
      } else {
        errorMsg = error.response.data.detail || error.response.data.message || '导出失败'
      }
    } else {
      errorMsg = error.message || '导出失败'
    }
    ElMessage.error('导出失败：' + errorMsg)
  }
}

// 导入到知识库
const handleImportToKnowledge = async () => {
  try {
    await ElMessageBox.confirm('确定要将探查结果导入到知识库吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    })
    
    const response = await probeApi.importToKnowledge(props.taskId)
    if (response.success) {
      ElMessage.success('导入成功')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('导入失败：' + (error.message || '未知错误'))
    }
  }
}

// 加载数据
const loadData = () => {
  loadTaskInfo()
  if (activeTab.value === 'database') {
    loadDatabaseResult()
  } else if (activeTab.value === 'tables') {
    loadTableResults()
  } else if (activeTab.value === 'columns' && selectedTable.value) {
    loadColumnResults()
    loadSampleData()
  }
}

// 监听taskId变化
watch(() => props.taskId, () => {
  if (props.taskId) {
    loadTaskInfo()
    loadDatabaseResult()
    loadTableResults()
  }
}, { immediate: true })

onMounted(() => {
  loadTaskInfo()
  loadDatabaseResult()
  loadTableResults()
})

// 不再需要轮询清理
</script>

<style scoped>
.probe-result-dialog {
  padding: 10px;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 15px;
  border-bottom: 1px solid #ebeef5;
}

.header-info {
  display: flex;
  align-items: center;
}

.task-name {
  font-size: 16px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.table-list-section {
  margin-top: 15px;
}

.search-bar {
  margin-bottom: 15px;
  display: flex;
  align-items: center;
}

.result-table {
  margin-top: 15px;
}

.details-section {
  padding: 15px 0;
}

.details-section h3 {
  margin-bottom: 15px;
  color: #303133;
}

.details-section h4 {
  margin: 15px 0 10px 0;
  color: #606266;
}

.column-list,
.sample-data {
  margin-top: 15px;
}
</style>

