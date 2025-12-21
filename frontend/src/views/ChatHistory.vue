<template>
  <div class="chat-history-container">
    <el-card class="main-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon class="title-icon"><ChatLineRound /></el-icon>
            <span class="title-text">历史对话</span>
            <el-tag v-if="total > 0" type="info" size="small" class="count-tag">
              {{ total }}
            </el-tag>
          </div>
          <div class="header-actions">
            <el-button type="primary" @click="goToChat">
              <el-icon><Plus /></el-icon>
              新建对话
            </el-button>
            <el-button
              type="danger"
              :disabled="selectedSessions.length === 0"
              @click="batchDelete"
            >
              <el-icon><Delete /></el-icon>
              批量删除
            </el-button>
          </div>
        </div>
      </template>
      
      <!-- 搜索和筛选 -->
      <div class="filter-bar">
        <el-input
          v-model="filters.keyword"
          placeholder="搜索对话标题"
          style="width: 300px"
          clearable
          @clear="loadSessions"
          @keyup.enter="loadSessions"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        
        <el-select
          v-model="filters.data_source_id"
          placeholder="选择数据源"
          style="width: 200px; margin-left: 10px"
          clearable
          @change="loadSessions"
        >
          <el-option
            v-for="ds in dataSources"
            :key="ds.id"
            :label="ds.name"
            :value="ds.id"
          />
        </el-select>
        
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 300px; margin-left: 10px"
          @change="handleDateChange"
        />
        
        <el-button type="primary" style="margin-left: 10px" @click="loadSessions">
          <el-icon><Search /></el-icon>
          搜索
        </el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>
      
      <!-- 对话列表 -->
      <el-table
        :data="sessions"
        class="session-table"
        border
        stripe
        @selection-change="handleSelectionChange"
        :header-cell-style="{ background: '#f5f7fa', color: '#606266', fontWeight: '600', textAlign: 'center' }"
      >
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column prop="title" label="对话标题" min-width="200" align="center" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="session-title-cell">
              <el-icon><ChatLineRound /></el-icon>
              <span>{{ row.title || '未命名对话' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="data_source_name" label="数据源" width="150" align="center" />
        <el-table-column prop="message_count" label="消息数" width="100" align="center" />
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">
              {{ row.status === 'active' ? '活跃' : '已归档' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" align="center">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="160" align="center">
          <template #default="{ row }">
            {{ formatTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right" align="center">
          <template #default="{ row }">
            <div style="display: flex; gap: 4px; justify-content: center; flex-wrap: nowrap;">
              <el-button
                type="primary"
                size="small"
                text
                @click="viewSession(row)"
              >
                <el-icon><View /></el-icon>
                查看
              </el-button>
              <el-button
                type="warning"
                size="small"
                text
                @click="renameSession(row)"
              >
                <el-icon><Edit /></el-icon>
                重命名
              </el-button>
              <el-button
                type="danger"
                size="small"
                text
                @click="deleteSession(row.id)"
              >
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div v-if="sessions.length > 0 || total > 0" style="margin-top: 20px; display: flex; justify-content: flex-end;">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadSessions"
          @current-change="loadSessions"
        />
      </div>
    </el-card>
    
    <!-- 重命名对话框 -->
    <el-dialog
      v-model="renameDialogVisible"
      title="重命名对话"
      width="400px"
    >
      <el-input
        v-model="renameForm.title"
        placeholder="请输入新标题"
        maxlength="100"
        show-word-limit
      />
      <template #footer>
        <el-button @click="renameDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmRename">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ChatLineRound,
  Plus,
  Delete,
  Search,
  View,
  Edit
} from '@element-plus/icons-vue'
import chatApi from '@/api/chat'
import request from '@/utils/request'

// 获取数据源列表的API
const getDataSources = async () => {
  return await request({
    url: '/api/v1/database-configs',
    method: 'get'
  })
}

const router = useRouter()

const sessions = ref([])
const selectedSessions = ref([])
const total = ref(0)
const pagination = ref({
  page: 1,
  page_size: 20
})
const filters = ref({
  keyword: '',
  data_source_id: null,
  status: null
})
const dateRange = ref(null)
const dataSources = ref([])
const renameDialogVisible = ref(false)
const renameForm = ref({
  id: null,
  title: ''
})

// 加载数据源列表
const loadDataSources = async () => {
  try {
    const response = await getDataSources()
    if (response.code === 200) {
      dataSources.value = response.data || []
    }
  } catch (error) {
    console.error('加载数据源失败:', error)
  }
}

// 加载对话列表
const loadSessions = async () => {
  try {
    const params = {
      page: pagination.value.page,
      page_size: pagination.value.page_size,
      keyword: filters.value.keyword || undefined,
      data_source_id: filters.value.data_source_id || undefined,
      status: filters.value.status || undefined,
      start_date: dateRange.value?.[0] ? new Date(dateRange.value[0]).toISOString() : undefined,
      end_date: dateRange.value?.[1] ? new Date(dateRange.value[1]).toISOString() : undefined
    }
    
    const response = await chatApi.getSessions(params)
    if (response.code === 200) {
      sessions.value = response.data || []
      total.value = response.pagination?.total || 0
    }
  } catch (error) {
    ElMessage.error('加载对话列表失败')
  }
}

// 重置筛选条件
const resetFilters = () => {
  filters.value = {
    keyword: '',
    data_source_id: null,
    status: null
  }
  dateRange.value = null
  loadSessions()
}

// 处理日期范围变化
const handleDateChange = () => {
  loadSessions()
}

// 选择变化
const handleSelectionChange = (selection) => {
  selectedSessions.value = selection.map(s => s.id)
}

// 查看对话
const viewSession = (session) => {
  router.push(`/chat?session=${session.id}`)
}

// 跳转到对话页面
const goToChat = () => {
  router.push('/chat')
}

// 重命名对话
const renameSession = (session) => {
  renameForm.value = {
    id: session.id,
    title: session.title
  }
  renameDialogVisible.value = true
}

// 确认重命名
const confirmRename = async () => {
  if (!renameForm.value.title.trim()) {
    ElMessage.warning('请输入标题')
    return
  }
  
  try {
    const response = await chatApi.updateSession(renameForm.value.id, {
      title: renameForm.value.title.trim()
    })
    
    if (response.code === 200) {
      ElMessage.success('重命名成功')
      renameDialogVisible.value = false
      await loadSessions()
    }
  } catch (error) {
    ElMessage.error('重命名失败')
  }
}

// 删除对话
const deleteSession = async (sessionId) => {
  try {
    await ElMessageBox.confirm('确定要删除这个对话吗？删除后无法恢复。', '确认删除', {
      type: 'warning'
    })
    
    await chatApi.deleteSession(sessionId)
    ElMessage.success('删除成功')
    await loadSessions()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 批量删除
const batchDelete = async () => {
  if (selectedSessions.value.length === 0) {
    ElMessage.warning('请选择要删除的对话')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedSessions.value.length} 个对话吗？删除后无法恢复。`,
      '确认批量删除',
      {
        type: 'warning'
      }
    )
    
    const response = await chatApi.batchDeleteSessions(selectedSessions.value)
    if (response.code === 200) {
      ElMessage.success(response.message || '批量删除成功')
      selectedSessions.value = []
      await loadSessions()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量删除失败')
    }
  }
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return ''
  const date = new Date(time)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  loadDataSources()
  loadSessions()
})
</script>

<style scoped>
.chat-history-container {
  padding: 20px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
  min-height: calc(100vh - 100px);
}

.main-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transition: box-shadow 0.3s;
}

.main-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-icon {
  font-size: 20px;
  color: #409eff;
}

.title-text {
  font-size: 18px;
  font-weight: 600;
}

.count-tag {
  margin-left: 8px;
}

.filter-bar {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}

.session-table {
  width: 100%;
  margin-top: 20px;
}

.session-title-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>

