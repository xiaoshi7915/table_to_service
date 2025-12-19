<template>
  <div class="chat-container">
    <!-- 左侧：历史对话列表 -->
    <div class="chat-sidebar">
      <div class="sidebar-header">
        <h3>对话历史</h3>
        <el-button type="primary" size="small" @click="createNewSession">
          <el-icon><Plus /></el-icon>
          新建对话
        </el-button>
      </div>
      
      <div class="session-list">
        <div
          v-for="session in sessions"
          :key="session.id"
          class="session-item"
          :class="{ active: currentSessionId === session.id }"
          @click="selectSession(session.id)"
        >
          <div class="session-title">{{ session.title || '新对话' }}</div>
          <div class="session-meta">
            <span class="session-time">{{ formatTime(session.created_at) }}</span>
            <el-button
              type="danger"
              size="small"
              text
              @click.stop="deleteSession(session.id)"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 中间：对话消息区域 -->
    <div class="chat-main">
      <div v-if="!currentSessionId" class="empty-state">
        <el-empty description="请选择一个对话或创建新对话">
          <el-button type="primary" @click="showCreateSessionDialog">创建新对话</el-button>
        </el-empty>
      </div>
      
      <div v-else class="chat-messages">
        <!-- 数据源和表信息提示 -->
        <div v-if="currentSession" class="session-info-bar">
          <div class="info-item">
            <el-icon><Connection /></el-icon>
            <span class="info-label">数据源：</span>
            <el-tag type="primary" size="small">{{ currentSession.data_source_name || '未选择' }}</el-tag>
          </div>
          <div class="info-item" v-if="currentSession.selected_tables">
            <el-icon><Grid /></el-icon>
            <span class="info-label">已选表：</span>
            <el-tag
              v-for="(table, idx) in (typeof currentSession.selected_tables === 'string' ? JSON.parse(currentSession.selected_tables) : currentSession.selected_tables)"
              :key="idx"
              type="success"
              size="small"
              style="margin-right: 4px"
            >
              {{ table }}
            </el-tag>
          </div>
        </div>
        
        <div
          v-for="message in messages"
          :key="message.id"
          class="message-item"
          :class="{ 'user-message': message.role === 'user', 'assistant-message': message.role === 'assistant' }"
        >
          <div class="message-content">
            <div v-if="message.role === 'user'" class="message-text">
              {{ message.content }}
            </div>
            
            <div v-else class="assistant-content">
              <!-- SQL展示 -->
              <div v-if="message.sql" class="sql-section">
                <div class="section-header">
                  <span>生成的SQL</span>
                  <div class="sql-actions">
                    <el-button size="small" text @click="copySQL(message.sql)">
                      <el-icon><DocumentCopy /></el-icon>
                      复制
                    </el-button>
                    <el-button 
                      v-if="message.error || message.error_message" 
                      size="small" 
                      type="warning" 
                      @click="showEditSQLDialog(message)"
                    >
                      <el-icon><Edit /></el-icon>
                      编辑SQL
                    </el-button>
                  </div>
                </div>
                <pre class="sql-code">{{ message.sql }}</pre>
                <!-- 错误信息 -->
                <div v-if="message.error || message.error_message" class="error-message">
                  <el-alert
                    :title="message.error || message.error_message"
                    type="error"
                    :closable="false"
                    show-icon
                  >
                    <template #default>
                      <div style="margin-top: 8px">
                        <el-button size="small" type="primary" @click="showEditSQLDialog(message)">
                          编辑SQL并重试
                        </el-button>
                      </div>
                    </template>
                  </el-alert>
                </div>
              </div>
              
              <!-- 图表展示 -->
              <div v-if="message.chart_config" class="chart-section">
                <div class="section-header">
                  <span>数据可视化</span>
                  <div class="chart-actions">
                    <el-select
                      v-model="message.chart_type"
                      size="small"
                      style="width: 120px; margin-right: 8px"
                      @change="changeChartType(message)"
                    >
                      <el-option label="表格" value="table" />
                      <el-option label="柱状图" value="bar" />
                      <el-option label="折线图" value="line" />
                      <el-option label="饼图" value="pie" />
                      <el-option label="散点图" value="scatter" />
                      <el-option label="面积图" value="area" />
                    </el-select>
                    <el-button size="small" type="primary" @click="showAddToDashboardDialog(message)">
                      <el-icon><DataBoard /></el-icon>
                      添加到仪表板
                    </el-button>
                  </div>
                </div>
                <div
                  v-if="message.chart_type !== 'table'"
                  ref="chartContainer"
                  class="chart-container"
                  :style="{ height: '400px' }"
                ></div>
                <el-table
                  v-else
                  :data="message.data"
                  style="width: 100%"
                  max-height="400"
                >
                  <el-table-column
                    v-for="col in message.columns"
                    :key="col"
                    :prop="col"
                    :label="col"
                  />
                </el-table>
              </div>
              
              <!-- 数据明细 -->
              <div v-if="message.data && message.data.length > 0" class="data-section">
                <div class="section-header">
                  <span>数据明细（共{{ message.total_rows || message.data.length }}条）</span>
                  <el-button size="small" @click="exportData(message)">
                    <el-icon><Download /></el-icon>
                    导出
                  </el-button>
                </div>
                <el-table
                  :data="message.data"
                  style="width: 100%"
                  max-height="300"
                >
                  <el-table-column
                    v-for="col in message.columns || Object.keys(message.data[0] || {})"
                    :key="col"
                    :prop="col"
                    :label="col"
                  />
                </el-table>
              </div>
              
              <!-- 解释说明 -->
              <div v-if="message.explanation" class="explanation-section">
                {{ message.explanation }}
              </div>
            </div>
          </div>
          
          <div class="message-time">{{ formatTime(message.created_at) }}</div>
        </div>
        
        <div v-if="loading" class="loading-indicator">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>AI正在思考...</span>
        </div>
        
        <!-- 空状态提示 -->
        <div v-if="!loading && messages.length === 0" class="empty-message">
          <el-empty description="还没有消息，开始对话吧！" />
        </div>
      </div>
      
      <!-- 输入框 -->
      <div class="chat-input">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="3"
          placeholder="输入您的问题，按Enter提交，Ctrl+Enter换行"
          @keydown.enter.exact="handleEnter"
          @keydown.ctrl.enter="handleCtrlEnter"
        />
        <div class="input-actions">
          <el-button type="primary" @click="sendMessage" :loading="loading">
            发送
          </el-button>
        </div>
      </div>
    </div>
    
    <!-- 右侧：推荐问题（可选） -->
    <div class="chat-sidebar-right">
      <div class="sidebar-header">
        <h3>猜你想问</h3>
      </div>
      <div class="recommended-questions">
        <div
          v-for="(question, index) in recommendedQuestions"
          :key="index"
          class="question-item"
          @click="selectQuestion(question)"
        >
          {{ question }}
        </div>
      </div>
    </div>
    
    <!-- 新建会话对话框 -->
    <el-dialog
      v-model="createSessionDialogVisible"
      title="创建新对话"
      width="700px"
      @close="resetCreateSessionForm"
    >
      <div class="create-session-content">
        <!-- 提示信息 -->
        <el-alert
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 20px"
        >
          <template #default>
            <div class="alert-content">
              <p style="margin: 0 0 8px 0; font-weight: 500;">开启智能问数前，请先选择数据源和表</p>
              <p style="margin: 0; font-size: 12px; color: #909399;">
                我可以查询数据、生成图表、分析数据、预测数据等，请选择一个数据源，开启智能问数吧~
              </p>
            </div>
          </template>
        </el-alert>
        
        <el-form :model="createSessionForm" label-width="100px">
          <el-form-item label="对话标题">
            <el-input v-model="createSessionForm.title" placeholder="请输入对话标题（可选）" />
          </el-form-item>
          <el-form-item label="数据源" required>
            <el-select
              v-model="createSessionForm.data_source_id"
              placeholder="请选择数据源"
              style="width: 100%"
              @change="handleDataSourceChange"
            >
              <el-option
                v-for="ds in dataSources"
                :key="ds.id"
                :label="ds.name"
                :value="ds.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="选择表" required>
            <el-select
              v-model="createSessionForm.selected_tables"
              placeholder="请选择表（可多选）"
              multiple
              style="width: 100%"
              :disabled="!createSessionForm.data_source_id || loadingTables"
            >
              <el-option
                v-for="table in tables"
                :key="table.name"
                :label="table.name"
                :value="table.name"
              />
            </el-select>
            <div v-if="loadingTables" style="margin-top: 8px; color: #909399; font-size: 12px">
              正在加载表列表...
            </div>
            <div v-if="!loadingTables && createSessionForm.data_source_id && tables.length === 0" style="margin-top: 8px; color: #f56c6c; font-size: 12px">
              该数据源暂无可用表
            </div>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="createSessionDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          @click="confirmCreateSession"
          :disabled="!createSessionForm.data_source_id || !createSessionForm.selected_tables || createSessionForm.selected_tables.length === 0"
        >
          开启问数
        </el-button>
      </template>
    </el-dialog>
    
    <!-- 添加到仪表板对话框 -->
    <el-dialog
      v-model="addToDashboardDialogVisible"
      title="添加到仪表板"
      width="500px"
      @close="resetAddToDashboardForm"
    >
      <el-form :model="addToDashboardForm" label-width="100px">
        <el-form-item label="选择仪表板" required>
          <el-select
            v-model="addToDashboardForm.dashboard_id"
            placeholder="请选择仪表板"
            style="width: 100%"
            filterable
          >
            <el-option
              v-for="dashboard in dashboardList"
              :key="dashboard.id"
              :label="dashboard.name"
              :value="dashboard.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="组件标题">
          <el-input v-model="addToDashboardForm.title" placeholder="请输入组件标题" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addToDashboardDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          @click="confirmAddToDashboard"
          :disabled="!addToDashboardForm.dashboard_id"
        >
          添加
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import { Plus, Delete, DocumentCopy, Download, Loading, DataBoard } from '@element-plus/icons-vue'
import chatApi from '@/api/chat'
import request from '@/utils/request'
import dashboardsApi from '@/api/dashboards'

const sessions = ref([])
const currentSessionId = ref(null)
const currentSession = ref(null)  // 当前会话信息，包含selected_tables
const messages = ref([])
const inputText = ref('')
const loading = ref(false)
const recommendedQuestions = ref([])
const chartInstances = ref({})

// 新建会话相关
const createSessionDialogVisible = ref(false)
const createSessionForm = ref({
  title: '',
  data_source_id: null,
  selected_tables: []
})
const dataSources = ref([])
const tables = ref([])
const loadingTables = ref(false)

// 添加到仪表板相关
const addToDashboardDialogVisible = ref(false)
const dashboardList = ref([])
const addToDashboardForm = ref({
  dashboard_id: null,
  title: ''
})
const currentMessageForDashboard = ref(null)

// 编辑SQL相关
const editSQLDialogVisible = ref(false)
const editSQLForm = ref({
  originalQuestion: '',
  sql: '',
  error: '',
  messageId: null
})
const retryingSQL = ref(false)

// 加载对话列表
const loadSessions = async () => {
  try {
    const response = await chatApi.getSessions()
    if (response.code === 200) {
      sessions.value = response.data || []
      if (sessions.value.length > 0 && !currentSessionId.value) {
        selectSession(sessions.value[0].id)
      }
    }
  } catch (error) {
    console.error('加载对话列表失败:', error)
  }
}

// 选择对话
const selectSession = async (sessionId) => {
  currentSessionId.value = sessionId
  // 获取会话详情，包含selected_tables
  try {
    const response = await chatApi.getSession(sessionId)
    if (response.code === 200) {
      currentSession.value = response.data
    }
  } catch (error) {
    console.error('获取会话详情失败:', error)
  }
  await loadMessages(sessionId)
  await loadRecommendedQuestions()
}

// 加载消息
const loadMessages = async (sessionId) => {
  try {
    const response = await chatApi.getMessages(sessionId)
    if (response.code === 200) {
      messages.value = response.data || []
      // 为每个消息初始化图表类型
      messages.value.forEach(msg => {
        if (msg.chart_config) {
          msg.chart_type = msg.chart_config.type || 'table'
          msg.columns = msg.chart_config.columns || Object.keys(msg.data?.[0] || {})
        }
      })
      await nextTick()
      renderCharts()
    }
  } catch (error) {
    console.error('加载消息失败:', error)
  }
}

// 显示创建会话对话框
const showCreateSessionDialog = async () => {
  createSessionDialogVisible.value = true
  await loadDataSources()
}

// 加载数据源列表
const loadDataSources = async () => {
  try {
    const response = await request({
      url: '/api/v1/database-configs',
      method: 'get'
    })
    if (response.code === 200) {
      dataSources.value = response.data || []
    }
  } catch (error) {
    ElMessage.error('加载数据源失败')
  }
}

// 数据源变化时加载表列表
const handleDataSourceChange = async () => {
  if (!createSessionForm.value.data_source_id) {
    tables.value = []
    createSessionForm.value.selected_tables = []
    return
  }
  
  loadingTables.value = true
  try {
    const response = await request({
      url: `/api/v1/chat/datasources/${createSessionForm.value.data_source_id}/tables`,
      method: 'get'
    })
    if (response.code === 200 || response.success) {
      // 处理响应数据格式：后端返回 {tables: [...], total: ...}
      const responseData = response.data || {}
      if (responseData.tables && Array.isArray(responseData.tables)) {
        tables.value = responseData.tables
      } else if (Array.isArray(responseData)) {
        tables.value = responseData
      } else {
        tables.value = []
      }
      
      if (tables.value.length === 0) {
        ElMessage.warning('该数据源暂无表')
      }
    } else {
      ElMessage.error('加载表列表失败：' + (response.message || '未知错误'))
      tables.value = []
    }
  } catch (error) {
    console.error('加载表列表错误:', error)
    ElMessage.error('加载表列表失败：' + (error.response?.data?.detail || error.message || '未知错误'))
    tables.value = []
  } finally {
    loadingTables.value = false
  }
}

// 确认创建会话
const confirmCreateSession = async () => {
  if (!createSessionForm.value.data_source_id || !createSessionForm.value.selected_tables || createSessionForm.value.selected_tables.length === 0) {
    ElMessage.warning('请选择数据源和至少一个表')
    return
  }
  
  try {
    const response = await chatApi.createSession({
      title: createSessionForm.value.title || `对话 ${new Date().toLocaleString('zh-CN')}`,
      data_source_id: createSessionForm.value.data_source_id,
      selected_tables: createSessionForm.value.selected_tables
    })
    
    if (response.code === 200) {
      ElMessage.success('创建对话成功')
      createSessionDialogVisible.value = false
      await loadSessions()
      selectSession(response.data.id)
      resetCreateSessionForm()
    }
  } catch (error) {
    ElMessage.error('创建对话失败：' + (error.response?.data?.detail || error.message || '未知错误'))
  }
}

// 重置创建会话表单
const resetCreateSessionForm = () => {
  createSessionForm.value = {
    title: '',
    data_source_id: null,
    selected_tables: []
  }
  tables.value = []
}

// 创建新对话（保留原有方法，改为显示对话框）
const createNewSession = () => {
  showCreateSessionDialog()
}

// 删除对话
const deleteSession = async (sessionId) => {
  try {
    await chatApi.deleteSession(sessionId)
    await loadSessions()
    if (currentSessionId.value === sessionId) {
      currentSessionId.value = null
      messages.value = []
    }
  } catch (error) {
    ElMessage.error('删除对话失败')
  }
}

// 发送消息
const sendMessage = async () => {
  if (!inputText.value.trim()) {
    ElMessage.warning('请输入问题')
    return
  }
  
  // 如果没有会话，先创建会话
  if (!currentSessionId.value) {
    ElMessage.warning('请先创建或选择一个对话')
    showCreateSessionDialog()
    return
  }
  
  // 确保已加载会话详情（如果还没有）
  if (!currentSession.value) {
    try {
      const sessionResponse = await chatApi.getSession(currentSessionId.value)
      if (sessionResponse.code === 200) {
        currentSession.value = sessionResponse.data
      }
    } catch (error) {
      console.error('获取会话详情失败:', error)
    }
  }
  
  const question = inputText.value.trim()
  inputText.value = ''
  loading.value = true
  
  try {
    // 获取当前会话的selected_tables
    let selectedTables = null
    if (currentSession.value && currentSession.value.selected_tables) {
      try {
        selectedTables = typeof currentSession.value.selected_tables === 'string' 
          ? JSON.parse(currentSession.value.selected_tables)
          : currentSession.value.selected_tables
      } catch (e) {
        console.error('解析selected_tables失败:', e)
      }
    }
    
    // 获取数据源ID（优先从currentSession获取）
    const dataSourceId = currentSession.value?.data_source_id 
      || sessions.value.find(s => s.id === currentSessionId.value)?.data_source_id
    
    if (!dataSourceId) {
      ElMessage.error('会话未关联数据源，请重新创建会话')
      loading.value = false
      return
    }
    
    const response = await chatApi.sendMessage(currentSessionId.value, {
      question,
      data_source_id: dataSourceId,
      selected_tables: selectedTables
    })
    
    if (response.code === 200 || response.success) {
      await loadMessages(currentSessionId.value)
      await loadRecommendedQuestions()
      
      // 滚动到底部
      await nextTick()
      const messagesContainer = document.querySelector('.chat-messages')
      if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight
      }
    } else {
      // 如果失败但有SQL，允许用户编辑重试
      if (response.data?.sql && response.data?.can_retry) {
        ElMessage.warning('SQL执行失败，您可以编辑SQL后重试')
      } else {
        ElMessage.error(response.message || '发送失败')
      }
    }
  } catch (error) {
    ElMessage.error('发送消息失败：' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 加载推荐问题
const loadRecommendedQuestions = async () => {
  // 如果没有当前会话，不加载推荐问题
  if (!currentSessionId.value) {
    recommendedQuestions.value = []
    return
  }
  
  try {
    const response = await chatApi.getRecommendedQuestions(currentSessionId.value)
    if (response.code === 200) {
      recommendedQuestions.value = response.data || []
    }
  } catch (error) {
    console.error('加载推荐问题失败:', error)
  }
}

// 选择推荐问题
const selectQuestion = (question) => {
  inputText.value = question
  
  // 检查是否有会话、数据源和表
  if (!currentSessionId.value) {
    ElMessage.warning('请先创建或选择一个对话')
    showCreateSessionDialog()
    return
  }
  
  // 确保已加载会话详情
  if (!currentSession.value) {
    ElMessage.warning('正在加载会话信息，请稍候...')
    return
  }
  
  if (!currentSession.value.data_source_id) {
    ElMessage.warning('当前会话未关联数据源，请先选择数据源和表')
    showCreateSessionDialog()
    return
  }
  
  if (!currentSession.value.selected_tables) {
    ElMessage.warning('当前会话未选择表，请先选择数据源和表')
    showCreateSessionDialog()
    return
  }
  
  sendMessage()
}

// 复制SQL
const copySQL = (sql) => {
  navigator.clipboard.writeText(sql).then(() => {
    ElMessage.success('SQL已复制到剪贴板')
  })
}

// 导出数据
const exportData = async (message) => {
  try {
    // 显示导出格式选择对话框
    const { value: format } = await ElMessageBox.prompt(
      '请选择导出格式',
      '导出数据',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputType: 'select',
        inputOptions: {
          excel: 'Excel (.xlsx)',
          csv: 'CSV (.csv)',
          png: 'PNG图片（仅图表）'
        },
        inputValue: 'excel'
      }
    )
    
    if (!format) return
    
    // 显示加载提示
    const loadingMessage = ElMessage({
      message: '正在导出，请稍候...',
      type: 'info',
      duration: 0
    })
    
    try {
      // 调用导出API
      const response = await chatApi.exportData(message.id, format)
      
      // 创建下载链接
      const blob = new Blob([response.data], {
        type: format === 'png' ? 'image/png' : format === 'csv' ? 'text/csv' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      
      // 从响应头获取文件名，或使用默认名称
      const contentDisposition = response.headers['content-disposition']
      let filename = `导出_${message.id}_${new Date().getTime()}`
      if (contentDisposition) {
        const matches = contentDisposition.match(/filename="?(.+)"?/i)
        if (matches && matches[1]) {
          filename = decodeURIComponent(matches[1])
        }
      } else {
        filename += format === 'png' ? '.png' : format === 'csv' ? '.csv' : '.xlsx'
      }
      
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
      loadingMessage.close()
      ElMessage.success('导出成功')
    } catch (error) {
      loadingMessage.close()
      throw error
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('导出失败：' + (error.message || '未知错误'))
    }
  }
}

// 切换图表类型
const changeChartType = async (message) => {
  // TODO: 调用后端API切换图表类型
  await nextTick()
  renderChart(message)
}

// 渲染图表
const renderCharts = () => {
  messages.value.forEach(msg => {
    if (msg.chart_config && msg.chart_type && msg.chart_type !== 'table') {
      renderChart(msg)
    }
  })
}

const renderChart = (message) => {
  const chartId = `chart-${message.id}`
  const container = document.querySelector(`.chart-container`)
  if (!container) return
  
  // 销毁旧图表
  if (chartInstances.value[chartId]) {
    chartInstances.value[chartId].dispose()
  }
  
  // 创建新图表
  const chart = echarts.init(container)
  const config = message.chart_config
  
  let option = {}
  if (message.chart_type === 'bar') {
    option = {
      title: { text: config.title },
      xAxis: config.xAxis,
      yAxis: config.yAxis,
      series: config.series
    }
  } else if (message.chart_type === 'line') {
    option = {
      title: { text: config.title },
      xAxis: config.xAxis,
      yAxis: config.yAxis,
      series: config.series
    }
  } else if (message.chart_type === 'pie') {
    option = {
      title: { text: config.title },
      series: config.series
    }
  } else if (message.chart_type === 'scatter') {
    option = {
      title: { text: config.title },
      xAxis: config.xAxis,
      yAxis: config.yAxis,
      series: config.series
    }
  } else if (message.chart_type === 'area') {
    option = {
      title: { text: config.title },
      xAxis: config.xAxis,
      yAxis: config.yAxis,
      series: config.series.map(s => ({ ...s, areaStyle: {} }))
    }
  }
  
  chart.setOption(option)
  chartInstances.value[chartId] = chart
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return ''
  const date = new Date(time)
  return date.toLocaleString('zh-CN')
}

// 快捷键处理
const handleEnter = (e) => {
  if (!e.shiftKey && !e.ctrlKey) {
    e.preventDefault()
    sendMessage()
  }
}

const handleCtrlEnter = () => {
  // Ctrl+Enter换行，不需要特殊处理
}

// 显示添加到仪表板对话框
const showAddToDashboardDialog = async (message) => {
  currentMessageForDashboard.value = message
  addToDashboardForm.value.title = message.chart_config?.title || `图表 ${new Date().toLocaleString('zh-CN')}`
  
  // 加载仪表板列表
  try {
    const response = await dashboardsApi.getDashboards({ page: 1, page_size: 100 })
    if (response.code === 200 || response.success) {
      dashboardList.value = response.data?.data || response.data || []
    }
  } catch (error) {
    ElMessage.error('加载仪表板列表失败')
    console.error('加载仪表板列表失败:', error)
  }
  
  addToDashboardDialogVisible.value = true
}

// 重置添加到仪表板表单
const resetAddToDashboardForm = () => {
  addToDashboardForm.value = {
    dashboard_id: null,
    title: ''
  }
  currentMessageForDashboard.value = null
}

// 确认添加到仪表板
const confirmAddToDashboard = async () => {
  if (!currentMessageForDashboard.value) {
    ElMessage.error('消息不存在')
    return
  }
  
  if (!addToDashboardForm.value.dashboard_id) {
    ElMessage.warning('请选择仪表板')
    return
  }
  
  try {
    const message = currentMessageForDashboard.value
    const chartConfig = message.chart_config || {}
    
    const widgetData = {
      widget_type: message.chart_type === 'table' ? 'table' : 'chart',
      title: addToDashboardForm.value.title || chartConfig.title || '图表',
      config: {
        ...chartConfig,
        type: message.chart_type,
        data: message.data,
        columns: message.columns
      },
      message_id: message.id,
      position_x: 0,
      position_y: 0,
      width: 400,
      height: 300
    }
    
    const response = await dashboardsApi.createWidget(addToDashboardForm.value.dashboard_id, widgetData)
    if (response.code === 200 || response.success) {
      ElMessage.success('已添加到仪表板')
      addToDashboardDialogVisible.value = false
      resetAddToDashboardForm()
    } else {
      ElMessage.error(response.message || '添加失败')
    }
  } catch (error) {
    ElMessage.error('添加到仪表板失败：' + (error.message || '未知错误'))
    console.error('添加到仪表板失败:', error)
  }
}

// 显示编辑SQL对话框
const showEditSQLDialog = (message) => {
  // 找到原始问题（从用户消息中）
  const userMessage = messages.value.find(m => 
    m.role === 'user' && 
    messages.value.indexOf(m) < messages.value.indexOf(message)
  )
  
  editSQLForm.value = {
    originalQuestion: userMessage?.content || message.question || '',
    sql: message.sql || '',
    error: message.error || message.error_message || '',
    messageId: message.id
  }
  editSQLDialogVisible.value = true
}

// 重置编辑SQL表单
const resetEditSQLForm = () => {
  editSQLForm.value = {
    originalQuestion: '',
    sql: '',
    error: '',
    messageId: null
  }
}

// 确认重试SQL
const confirmRetrySQL = async () => {
  if (!editSQLForm.value.sql.trim()) {
    ElMessage.warning('请输入SQL语句')
    return
  }
  
  if (!currentSessionId.value) {
    ElMessage.warning('请先选择或创建一个对话')
    return
  }
  
  retryingSQL.value = true
  try {
    // 获取当前会话信息
    const dataSourceId = currentSession.value?.data_source_id 
      || sessions.value.find(s => s.id === currentSessionId.value)?.data_source_id
    
    if (!dataSourceId) {
      ElMessage.error('会话未关联数据源')
      retryingSQL.value = false
      return
    }
    
    // 发送编辑后的SQL
    const response = await chatApi.sendMessage(currentSessionId.value, {
      question: editSQLForm.value.originalQuestion,
      data_source_id: dataSourceId,
      selected_tables: currentSession.value?.selected_tables 
        ? (typeof currentSession.value.selected_tables === 'string' 
          ? JSON.parse(currentSession.value.selected_tables) 
          : currentSession.value.selected_tables)
        : null,
      edited_sql: editSQLForm.value.sql
    })
    
    if (response.code === 200 || response.success) {
      ElMessage.success('SQL执行成功')
      editSQLDialogVisible.value = false
      resetEditSQLForm()
      // 重新加载消息
      await loadMessages(currentSessionId.value)
    } else {
      ElMessage.error(response.message || 'SQL执行失败')
      // 如果失败，更新错误信息
      if (response.data?.error) {
        editSQLForm.value.error = response.data.error
      }
    }
  } catch (error) {
    console.error('重试SQL失败:', error)
    ElMessage.error('重试SQL失败：' + (error.response?.data?.detail || error.message || '未知错误'))
    if (error.response?.data?.error) {
      editSQLForm.value.error = error.response.data.error
    }
  } finally {
    retryingSQL.value = false
  }
}

onMounted(async () => {
  await loadSessions()
  // 等待会话加载完成后再加载推荐问题
  // loadSessions 中会自动选择第一个会话，所以这里可以安全调用
  loadRecommendedQuestions()
})
</script>

<style scoped>
.chat-container {
  display: flex;
  height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
}

.chat-sidebar {
  width: 250px;
  background: white;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.session-list {
  flex: 1;
  overflow-y: auto;
}

.session-item {
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background 0.2s;
}

.session-item:hover {
  background: #f5f7fa;
}

.session-item.active {
  background: #ecf5ff;
  border-left: 3px solid #409eff;
}

.session-title {
  font-weight: 500;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #909399;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-message {
  padding: 40px;
  text-align: center;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  scroll-behavior: smooth;
}

.session-info-bar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-item .el-icon {
  font-size: 16px;
}

.info-label {
  font-size: 14px;
  font-weight: 500;
}

.create-session-content {
  padding: 10px 0;
}

.alert-content {
  line-height: 1.6;
}

.message-item {
  margin-bottom: 20px;
}

.user-message {
  text-align: right;
}

.user-message .message-content {
  display: inline-block;
  background: #409eff;
  color: white;
  padding: 10px 16px;
  border-radius: 8px;
  max-width: 70%;
}

.assistant-message .message-content {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 8px;
  max-width: 90%;
}

.message-time {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.sql-section,
.chart-section,
.data-section {
  margin-bottom: 16px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-weight: 600;
}

.chart-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sql-code {
  background: #282c34;
  color: #abb2bf;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  font-family: 'Courier New', monospace;
  font-size: 14px;
}

.sql-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.error-message {
  margin-top: 12px;
}

.chart-container {
  width: 100%;
}

.explanation-section {
  padding: 12px;
  background: #e6f7ff;
  border-left: 3px solid #1890ff;
  border-radius: 4px;
  margin-top: 16px;
}

.loading-indicator {
  text-align: center;
  padding: 20px;
  color: #909399;
}

.chat-input {
  padding: 16px;
  border-top: 1px solid #e4e7ed;
}

.input-actions {
  margin-top: 8px;
  text-align: right;
}

.chat-sidebar-right {
  width: 200px;
  background: white;
  border-left: 1px solid #e4e7ed;
  padding: 16px;
}

.recommended-questions {
  margin-top: 16px;
}

.question-item {
  padding: 8px 12px;
  margin-bottom: 8px;
  background: #f5f7fa;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
  font-size: 14px;
}

.question-item:hover {
  background: #ecf5ff;
}
</style>

