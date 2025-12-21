<template>
  <div class="probe-result">
    <el-card class="main-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon class="back-icon" @click="goBack"><ArrowLeft /></el-icon>
            <span class="title-text">探查结果 {{ taskName }}</span>
          </div>
          <div class="header-actions">
            <el-button type="primary" @click="handleExport('excel')">导出Excel</el-button>
            <el-button @click="handleExport('csv')">导出CSV</el-button>
            <el-button type="success" @click="handleImportToKnowledge">导入到知识库</el-button>
            <el-button @click="loadData" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>
      
      <!-- Tab页 -->
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
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
              @selection-change="handleTableSelectionChange"
              @row-click="handleTableRowClick"
            >
              <el-table-column type="selection" width="55" />
              <el-table-column prop="table_name" label="表名" min-width="150">
                <template #default="{ row }">
                  <el-link type="primary" @click="handleSelectTable(row)">{{ row.table_name }}</el-link>
                </template>
              </el-table-column>
              <el-table-column prop="column_count" label="字段数" width="100" />
              <el-table-column prop="primary_key" label="主键" min-width="120">
                <template #default="{ row }">
                  {{ formatPrimaryKey(row.primary_key) }}
                </template>
              </el-table-column>
              <el-table-column prop="indexes" label="索引" min-width="120">
                <template #default="{ row }">
                  {{ row.indexes ? row.indexes.length : 0 }}个
                </template>
              </el-table-column>
              <el-table-column prop="row_count" label="数据量" width="120" />
              <el-table-column prop="comment" label="表注释" min-width="150" />
              <el-table-column prop="is_hidden" label="是否屏蔽" width="100">
                <template #default="{ row }">
                  {{ row.is_hidden ? '是' : '否' }}
                </template>
              </el-table-column>
            </el-table>
            
            <div class="table-actions">
              <el-checkbox v-model="selectAll" @change="handleSelectAll">全选</el-checkbox>
              <el-button @click="handleHideTables(true)">屏蔽</el-button>
              <el-button @click="handleHideTables(false)">取消屏蔽</el-button>
            </div>
            
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
        
        <el-tab-pane label="详情" name="details">
          <div v-if="selectedTable" class="details-section">
            <h3>{{ selectedTable.table_name }} 表详情</h3>
            
            <!-- 图表分析 -->
            <div v-if="columnResults.length > 0" class="chart-section">
              <h4>图表分析</h4>
              <div v-for="column in columnResults" :key="column.id" class="column-analysis">
                <h5>{{ column.column_name }}[{{ column.data_type }}]</h5>
                
                <div class="value-range">
                  <h6>值范围</h6>
                  <el-descriptions :column="2" border>
                    <el-descriptions-item label="最大值">{{ column.max_value || '-' }}</el-descriptions-item>
                    <el-descriptions-item label="最小值">{{ column.min_value || '-' }}</el-descriptions-item>
                  </el-descriptions>
                </div>
                
                <div v-if="column.top_values && column.top_values.length > 0" class="value-distribution">
                  <h6>数值分布</h6>
                  <!-- 这里可以集成图表库显示饼图和柱状图 -->
                  <el-table :data="column.top_values" style="width: 100%">
                    <el-table-column prop="value" label="值" />
                    <el-table-column prop="count" label="次数" />
                  </el-table>
                </div>
              </div>
            </div>
            
            <!-- 示例数据 -->
            <div class="sample-data-section">
              <h4>示例数据</h4>
              <el-table :data="sampleData" style="width: 100%">
                <el-table-column 
                  v-for="col in sampleColumns" 
                  :key="col"
                  :prop="col"
                  :label="col"
                />
              </el-table>
            </div>
          </div>
          <el-empty v-else description="请选择一个表查看详情" />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Refresh } from '@element-plus/icons-vue'
import probeApi from '@/api/probe'
import api from '@/api'

const route = useRoute()
const router = useRouter()

const taskId = computed(() => parseInt(route.params.id))
const loading = ref(false)
const taskName = ref('')
const taskInfo = ref(null)
const activeTab = ref('tables')
const tableSearchKeyword = ref('')
const tableResults = ref([])
const selectedTable = ref(null)
const columnResults = ref([])
const sampleData = ref([])
const sampleColumns = ref([])
const selectedTables = ref([])
const selectAll = ref(false)
const tableRef = ref(null)

const tablePagination = ref({
  currentPage: 1,
  pageSize: 10,
  total: 0
})

// 加载数据
const loadData = async () => {
  await Promise.all([
    loadTaskInfo(),
    loadTableResults()
  ])
}

// 加载任务信息
const loadTaskInfo = async () => {
  try {
    const response = await probeApi.getTask(taskId.value)
    if (response.success) {
      taskInfo.value = response.data
      taskName.value = response.data.task_name
    }
  } catch (error) {
    ElMessage.error('加载任务信息失败')
  }
}

// 加载表结果
const loadTableResults = async () => {
  loading.value = true
  try {
    const response = await probeApi.getTableResults(taskId.value, {
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
  if (tabName === 'details' && tableResults.value.length > 0 && !selectedTable.value) {
    selectedTable.value = tableResults.value[0]
    loadColumnResults()
    loadSampleData()
  }
}

// 加载列结果
const loadColumnResults = async () => {
  if (!selectedTable.value) return
  
  try {
    const response = await probeApi.getColumnResults(taskId.value, selectedTable.value.table_name)
    if (response.success) {
      columnResults.value = response.data || []
    }
  } catch (error) {
    ElMessage.error('加载列结果失败')
  }
}

// 加载示例数据
const loadSampleData = async () => {
  if (!selectedTable.value || !taskInfo.value) return
  
  try {
    // 通过数据库配置API获取表的示例数据
    const response = await api.get(`/database-configs/${taskInfo.value.database_config_id}/tables/${selectedTable.value.table_name}/sample`, {
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
    // 如果API不存在，尝试直接查询
    sampleData.value = []
    sampleColumns.value = []
  }
}

// 表格选择变化
const handleTableSelectionChange = (selection) => {
  selectedTables.value = selection
}

// 选择表查看详情
const handleSelectTable = (table) => {
  selectedTable.value = table
  activeTab.value = 'details'
  loadColumnResults()
  loadSampleData()
}

// 表格行点击
const handleTableRowClick = (row) => {
  handleSelectTable(row)
}

// 全选
const handleSelectAll = (checked) => {
  if (tableRef.value) {
    if (checked) {
      tableResults.value.forEach(row => {
        tableRef.value.toggleRowSelection(row, true)
      })
    } else {
      tableRef.value.clearSelection()
    }
  }
}

// 屏蔽/取消屏蔽表
const handleHideTables = async (isHidden) => {
  if (selectedTables.value.length === 0) {
    ElMessage.warning('请先选择要操作的表')
    return
  }
  
  try {
    for (const table of selectedTables.value) {
      await probeApi.hideTable(taskId.value, table.table_name, isHidden)
    }
    ElMessage.success('操作成功')
    loadTableResults()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

// 导出
const handleExport = async (format) => {
  try {
    const response = await probeApi.exportResults(taskId.value, format)
    
    // 创建下载链接
    const blob = new Blob([response.data], { 
      type: format === 'csv' ? 'application/zip' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    
    const filename = `探查结果_${taskName.value}_${new Date().getTime()}.${format === 'csv' ? 'zip' : 'xlsx'}`
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
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
    
    const response = await probeApi.importToKnowledge(taskId.value)
    if (response.success) {
      ElMessage.success(`导入成功，共导入 ${response.data.imported_count} 条知识`)
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('导入失败')
    }
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

// 工具函数
const formatPrimaryKey = (pk) => {
  if (!pk) return '-'
  if (Array.isArray(pk)) {
    return pk.join(', ')
  }
  return String(pk)
}

const goBack = () => {
  router.push('/data-probe')
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.probe-result {
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

.back-icon {
  font-size: 20px;
  cursor: pointer;
  color: #409EFF;
}

.title-text {
  font-size: 18px;
  font-weight: 600;
}

.search-bar {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
}

.table-actions {
  margin-top: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.details-section {
  padding: 20px;
}

.chart-section {
  margin-bottom: 30px;
}

.column-analysis {
  margin-bottom: 30px;
  padding: 20px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
}

.value-range, .value-distribution {
  margin-top: 15px;
}

.sample-data-section {
  margin-top: 30px;
}
</style>

