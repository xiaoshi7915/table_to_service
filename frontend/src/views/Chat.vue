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
          <div class="session-title">
            <span>{{ session.title || '新对话' }}</span>
            <el-button
              type="primary"
              size="small"
              text
              @click.stop="editSessionTitle(session)"
              style="margin-left: 8px"
            >
              <el-icon><Edit /></el-icon>
            </el-button>
          </div>
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
            <el-tooltip
              v-for="(table, idx) in (typeof currentSession.selected_tables === 'string' ? JSON.parse(currentSession.selected_tables) : currentSession.selected_tables)"
              :key="idx"
              :raw-content="true"
              :content="getTableTooltipContent(table)"
              placement="top"
              :disabled="getTableTooltipContent(table) === null"
              effect="dark"
              popper-class="table-fields-tooltip"
              :show-after="300"
            >
              <el-tag
                type="success"
                size="small"
                style="margin-right: 4px; cursor: help;"
                @mouseenter="loadTableFields(table)"
              >
                {{ table }}
                <span v-if="getTableDescription(table)" class="table-description">
                  ({{ getTableDescription(table) }})
                </span>
              </el-tag>
            </el-tooltip>
            <el-button
              type="primary"
              size="small"
              text
              @click="showEditTablesDialog"
              style="margin-left: 8px"
            >
              <el-icon><Edit /></el-icon>
              编辑表
            </el-button>
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
              <!-- 显示问题改写信息（如果有） -->
              <div v-if="message.question_rewrite && message.question_rewrite.rewritten !== message.content" class="question-rewrite-info">
                <el-collapse>
                  <el-collapse-item name="rewrite">
                    <template #title>
                      <el-icon><Edit /></el-icon>
                      <span style="margin-left: 4px; font-size: 12px; color: #909399">
                        问题已优化（点击查看）
                      </span>
                    </template>
                    <div class="rewrite-details">
                      <div class="rewrite-item">
                        <span class="rewrite-label">原始问题：</span>
                        <span class="rewrite-value">{{ message.question_rewrite.original }}</span>
                      </div>
                      <div class="rewrite-item">
                        <span class="rewrite-label">优化后：</span>
                        <span class="rewrite-value rewritten">{{ message.question_rewrite.rewritten }}</span>
                      </div>
                      <div v-if="message.question_rewrite.changes && message.question_rewrite.changes.length > 0" class="rewrite-item">
                        <span class="rewrite-label">优化说明：</span>
                        <ul class="rewrite-changes">
                          <li v-for="(change, idx) in message.question_rewrite.changes" :key="idx">{{ change }}</li>
                        </ul>
                      </div>
                    </div>
                  </el-collapse-item>
                </el-collapse>
              </div>
            </div>
            
            <div v-else class="assistant-content">
              <!-- 加载中状态 -->
              <div v-if="message.is_loading" class="loading-message">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span style="margin-left: 8px;">正在思考中...</span>
              </div>
              <template v-else>
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
                
                <!-- 复杂SQL提示（包含CREATE等语句，需要手动执行） -->
                <div v-if="message.contains_complex_sql" class="complex-sql-notice">
                  <el-alert
                    title="此SQL包含复杂逻辑，需要手动执行"
                    type="info"
                    :closable="false"
                    show-icon
                  >
                    <template #default>
                      <div class="complex-sql-info">
                        <p>生成的SQL包含CREATE等语句，为了数据安全，系统不会自动执行此类SQL。</p>
                        <p><strong>说明：</strong></p>
                        <ul>
                          <li>您可以在数据库管理工具中手动执行此SQL</li>
                          <li>建议：如果可能，请尝试用更简单的查询方式重新提问，例如使用子查询或CTE（WITH子句）代替临时表</li>
                        </ul>
                      </div>
                    </template>
                  </el-alert>
                </div>
                
                <!-- 错误信息 -->
                <div v-if="message.error || message.error_message" class="error-message">
                  <el-alert
                    :title="`SQL执行失败：${message.error || message.error_message}`"
                    type="error"
                    :closable="false"
                    show-icon
                  >
                    <template #default>
                      <div class="error-actions">
                        <div class="error-description">
                          <p><strong>执行的SQL：</strong></p>
                          <pre class="error-sql">{{ message.sql }}</pre>
                          <p><strong>错误原因：</strong>{{ message.error || message.error_message }}</p>
                        </div>
                        <div class="error-buttons">
                          <el-button size="small" type="primary" @click="showEditSQLDialog(message)">
                            <el-icon><Edit /></el-icon>
                            直接编辑SQL
                          </el-button>
                          <el-button size="small" type="success" @click="continueWithNaturalLanguage(message)">
                            <el-icon><ChatLineRound /></el-icon>
                            继续用自然语言提问
                          </el-button>
                        </div>
                      </div>
                    </template>
                  </el-alert>
                  
                  <!-- 错误时也显示推荐问题 -->
                  <div v-if="message.recommended_questions && message.recommended_questions.length > 0" class="recommended-questions-section" style="margin-top: 12px">
                    <div class="recommended-questions-header">
                      <el-icon><ChatLineRound /></el-icon>
                      <span>猜你想问</span>
                    </div>
                    <div class="recommended-questions-list">
                      <el-tag
                        v-for="(question, idx) in message.recommended_questions"
                        :key="idx"
                        class="recommended-question-tag"
                        @click="selectRecommendedQuestion(question, message)"
                      >
                        {{ question }}
                      </el-tag>
                    </div>
                  </div>
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
                  :id="`chart-${message.id}`"
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
              
              <!-- 解释说明（包含LLM生成的数据分析总结） -->
              <div v-if="message.explanation || (message.content && message.role === 'assistant')" class="explanation-section">
                <div v-html="formatExplanation(message.explanation || message.content)"></div>
              </div>
              
              <!-- 推荐问题（显示在AI回复下方，基于当前会话上下文） -->
              <div v-if="message.recommended_questions && message.recommended_questions.length > 0" class="recommended-questions-section">
                <div class="recommended-questions-header">
                  <el-icon><ChatLineRound /></el-icon>
                  <span>猜你想问</span>
                </div>
                <div class="recommended-questions-list">
                  <el-tag
                    v-for="(question, idx) in message.recommended_questions"
                    :key="idx"
                    class="recommended-question-tag"
                    @click="selectRecommendedQuestion(question, message)"
                  >
                    {{ question }}
                  </el-tag>
                </div>
              </div>
              </template>
            </div>
          </div>
          
          <div class="message-time">{{ formatTime(message.created_at) }}</div>
        </div>
        
        <!-- 移除全局loading指示器，使用消息内的loading状态 -->
        
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
                :key="table.name || table"
                :value="table.name || table"
              >
                <div style="display: flex; align-items: center; justify-content: space-between;">
                  <span>{{ table.name || table }}</span>
                  <span v-if="table.description" style="color: #f56c6c; font-size: 12px; margin-left: 8px;">
                    {{ table.description }}
                  </span>
                </div>
              </el-option>
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
    
    <!-- 导出数据对话框 -->
    <el-dialog
      v-model="exportDialogVisible"
      title="导出数据"
      width="500px"
      @close="resetExportForm"
    >
      <el-form :model="exportForm" label-width="100px">
        <el-form-item label="导出格式" required>
          <el-select
            v-model="exportForm.format"
            placeholder="请选择导出格式"
            style="width: 100%"
          >
            <el-option label="Excel (.xlsx)" value="excel" />
            <el-option label="CSV (.csv)" value="csv" />
            <el-option label="JSON (.json)" value="json" />
            <el-option label="XML (.xml)" value="xml" />
            <el-option label="PNG图片（仅图表）" value="png" />
            <el-option label="生成服务接口" value="generate_interface" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="exportDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          @click="confirmExport"
          :disabled="!exportForm.format"
        >
          确定
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
    
    <!-- 编辑表对话框 -->
    <el-dialog
      v-model="editTablesDialogVisible"
      title="编辑选择的表"
      width="600px"
      @close="resetEditTablesForm"
    >
      <el-form :model="editTablesForm" label-width="100px">
        <el-form-item label="数据源">
          <el-select
            v-model="editTablesForm.data_source_id"
            placeholder="请选择数据源"
            style="width: 100%"
            disabled
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
            v-model="editTablesForm.selected_tables"
            placeholder="请选择表（可多选）"
            multiple
            style="width: 100%"
            :disabled="loadingEditTables"
          >
            <el-option
              v-for="table in editTablesList"
              :key="table.name || table"
              :value="table.name || table"
            >
              <div style="display: flex; align-items: center; justify-content: space-between;">
                <span>{{ table.name || table }}</span>
                <span v-if="table.description" style="color: #f56c6c; font-size: 12px; margin-left: 8px;">
                  {{ table.description }}
                </span>
              </div>
            </el-option>
          </el-select>
          <div v-if="loadingEditTables" style="margin-top: 8px; color: #909399; font-size: 12px">
            正在加载表列表...
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editTablesDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          @click="confirmEditTables"
          :disabled="!editTablesForm.selected_tables || editTablesForm.selected_tables.length === 0"
        >
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch, h } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import { Plus, Delete, DocumentCopy, Download, Loading, DataBoard, Edit, ChatLineRound, Connection, Grid } from '@element-plus/icons-vue'
import chatApi from '@/api/chat'
import request from '@/utils/request'
import dashboardsApi from '@/api/dashboards'
import api from '@/api'

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
  data_source_id: null,
  selected_tables: []
})
const dataSources = ref([])
const tables = ref([])
const loadingTables = ref(false)
const tableDescriptions = ref({}) // 存储表名和描述的映射
const tableFieldsCache = ref({}) // 存储表字段信息缓存 { tableName: { columns: [...], loading: false } }

// 编辑表相关
const editTablesDialogVisible = ref(false)
const editTablesForm = ref({
  data_source_id: null,
  selected_tables: []
})
const editTablesList = ref([])
const loadingEditTables = ref(false)

// 导出数据相关
const exportDialogVisible = ref(false)
const exportForm = ref({
  format: 'excel'
})
const currentMessageForExport = ref(null)

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
      // 为每个消息初始化图表类型和推荐问题
      messages.value.forEach(msg => {
        if (msg.chart_config) {
          msg.chart_type = msg.chart_config.type || 'table'
          msg.columns = msg.chart_config.columns || Object.keys(msg.data?.[0] || {})
        }
        // 确保推荐问题字段存在（如果没有则初始化为空数组）
        if (!msg.recommended_questions) {
          msg.recommended_questions = []
        }
        // 确保contains_complex_sql字段存在
        if (msg.contains_complex_sql === undefined) {
          msg.contains_complex_sql = false
        }
        // 确保thinking_steps字段存在（从后端加载的消息可能包含此字段）
        if (!msg.thinking_steps) {
          msg.thinking_steps = []
        }
        // 确保is_loading字段存在（加载完成后应该为false）
        if (msg.is_loading === undefined) {
          msg.is_loading = false
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
        let tableList = []
        if (responseData.tables && Array.isArray(responseData.tables)) {
          tableList = responseData.tables
        } else if (Array.isArray(responseData)) {
          tableList = responseData
        } else {
          tableList = []
        }
        
        // 处理表列表，保留表名和描述的对象结构（与编辑表对话框保持一致）
        tables.value = tableList.map(item => {
          if (typeof item === 'string') {
            return { name: item, description: '' }
          } else {
            const tableName = item.name || item
            const description = item.description || ''
            
            // 存储表描述到映射中（用于其他地方）
            if (description) {
              tableDescriptions.value[tableName] = description
            }
            
            return { name: tableName, description: description }
          }
        })
        
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
    // 提取表名（如果tables是对象数组，需要提取name字段）
    const selectedTableNames = createSessionForm.value.selected_tables.map(t => 
      typeof t === 'string' ? t : (t.name || t)
    )
    
    // 不传title，让后端自动生成默认标题
    const response = await chatApi.createSession({
      data_source_id: createSessionForm.value.data_source_id,
      selected_tables: selectedTableNames
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

// 获取表描述
const getTableDescription = (tableName) => {
  // 如果当前会话中有表信息，优先使用
  if (currentSession.value && currentSession.value.table_info) {
    const tableInfo = currentSession.value.table_info.find(t => t.name === tableName)
    if (tableInfo && tableInfo.description) {
      return tableInfo.description
    }
  }
  
  // 从存储的描述中获取
  if (tableDescriptions.value[tableName]) {
    return tableDescriptions.value[tableName]
  }
  
  return ''
}

// 加载表字段信息（懒加载）
const loadTableFields = async (tableName) => {
  // 如果已缓存或正在加载，跳过
  if (tableFieldsCache.value[tableName] && 
      (tableFieldsCache.value[tableName].columns || tableFieldsCache.value[tableName].loading)) {
    return
  }
  
  // 如果没有数据源ID，无法加载
  if (!currentSession.value?.data_source_id) {
    return
  }
  
  // 标记为加载中
  if (!tableFieldsCache.value[tableName]) {
    tableFieldsCache.value[tableName] = { loading: true, columns: null }
  } else {
    tableFieldsCache.value[tableName].loading = true
  }
  
  try {
    const response = await request({
      url: `/database-configs/${currentSession.value.data_source_id}/tables/${encodeURIComponent(tableName)}/info`,
      method: 'get'
    })
    // request拦截器已经处理了响应格式
    // 如果响应有success字段，data在response.data中
    // 如果响应有code字段，data在response.data中
    let columns = null
    if (response.code === 200 || response.success) {
      if (response.data?.columns) {
        columns = response.data.columns
      } else if (response.data?.data?.columns) {
        // 兼容双重嵌套的情况
        columns = response.data.data.columns
      }
    }
    
    if (columns && columns.length > 0) {
      tableFieldsCache.value[tableName] = {
        loading: false,
        columns: columns
      }
      console.log(`✅ 表 ${tableName} 字段信息加载成功，共 ${columns.length} 个字段`)
    } else {
      tableFieldsCache.value[tableName] = { loading: false, columns: null }
      console.warn(`⚠️ 表 ${tableName} 字段信息为空，response结构:`, {
        code: response.code,
        success: response.success,
        hasData: !!response.data,
        hasDataColumns: !!response.data?.columns,
        hasDataDataColumns: !!response.data?.data?.columns
      })
    }
  } catch (error) {
    console.error(`❌ 加载表 ${tableName} 字段信息失败:`, error)
    tableFieldsCache.value[tableName] = { loading: false, columns: null }
  }
}

// 获取表字段悬停提示内容
const getTableTooltipContent = (tableName) => {
  const cached = tableFieldsCache.value[tableName]
  
  // 如果正在加载，显示加载提示
  if (cached && cached.loading) {
    return '<div style="padding: 8px;">正在加载字段信息...</div>'
  }
  
  // 如果没有字段信息，返回null（不显示提示）
  if (!cached || !cached.columns || cached.columns.length === 0) {
    // 调试：记录为什么没有字段信息
    if (!cached) {
      console.debug(`🔍 表 ${tableName} 字段缓存不存在，需要加载`)
    } else if (!cached.columns) {
      console.debug(`🔍 表 ${tableName} 字段数据为空`)
    } else if (cached.columns.length === 0) {
      console.debug(`🔍 表 ${tableName} 字段数组为空`)
    }
    return null
  }
  
  // 构建字段信息HTML（两列布局：字段名和字段描述）
  const fieldsHtml = cached.columns
    .map(col => {
      const comment = col.comment || '无注释'
      return `<tr style="border-bottom: 1px solid #e4e7ed;">
        <td style="padding: 6px 8px; font-weight: 600; color: #409EFF; background-color: #f0f9ff; border-right: 1px solid #e4e7ed; white-space: nowrap;">
          ${col.name}
        </td>
        <td style="padding: 6px 8px; color: #303133; background-color: #ffffff;">
          ${comment}
        </td>
      </tr>`
    })
    .join('')
  
  return `<div style="max-width: 500px; max-height: 400px; overflow-y: auto; background-color: #ffffff;">
    <div style="font-weight: 600; margin-bottom: 8px; padding: 8px; background-color: #409EFF; color: #ffffff; border-radius: 4px 4px 0 0;">
      ${tableName} - 字段列表
    </div>
    <table style="width: 100%; border-collapse: collapse; background-color: #ffffff;">
      <thead>
        <tr style="background-color: #f5f7fa; border-bottom: 2px solid #409EFF;">
          <th style="padding: 8px; text-align: left; font-weight: 600; color: #303133; border-right: 1px solid #e4e7ed;">字段名</th>
          <th style="padding: 8px; text-align: left; font-weight: 600; color: #303133;">字段描述</th>
        </tr>
      </thead>
      <tbody>
        ${fieldsHtml}
      </tbody>
    </table>
  </div>`
}

// 重置创建会话表单
const resetCreateSessionForm = () => {
  createSessionForm.value = {
    data_source_id: null,
    selected_tables: []
  }
  tables.value = []
  tableDescriptions.value = {}
}

// 显示编辑表对话框
const showEditTablesDialog = async () => {
  if (!currentSession.value || !currentSession.value.data_source_id) {
    ElMessage.warning('当前会话没有数据源，无法编辑表')
    return
  }
  
  // 初始化表单
  editTablesForm.value = {
    data_source_id: currentSession.value.data_source_id,
    selected_tables: []
  }
  
  // 获取当前已选择的表
  if (currentSession.value.selected_tables) {
    try {
      const currentTables = typeof currentSession.value.selected_tables === 'string'
        ? JSON.parse(currentSession.value.selected_tables)
        : currentSession.value.selected_tables
      editTablesForm.value.selected_tables = currentTables.map(t => t)
    } catch (e) {
      console.error('解析已选表失败:', e)
    }
  }
  
  // 加载表列表
  await loadEditTablesList()
  
  editTablesDialogVisible.value = true
}

// 加载编辑表列表
const loadEditTablesList = async () => {
  if (!editTablesForm.value.data_source_id) {
    editTablesList.value = []
    return
  }
  
  loadingEditTables.value = true
  try {
    const response = await request({
      url: `/api/v1/chat/datasources/${editTablesForm.value.data_source_id}/tables`,
      method: 'get'
    })
    
    if (response.code === 200 || response.success) {
      const responseData = response.data || {}
      let tableList = []
      if (responseData.tables && Array.isArray(responseData.tables)) {
        tableList = responseData.tables
      } else if (Array.isArray(responseData)) {
        tableList = responseData
      }
      
      // 处理表列表，保留表名和描述的对象结构
      editTablesList.value = tableList.map(item => {
        if (typeof item === 'string') {
          return { name: item, description: '' }
        } else {
          const tableName = item.name || item
          const description = item.description || ''
          return { name: tableName, description: description }
        }
      })
    } else {
      ElMessage.error('加载表列表失败：' + (response.message || '未知错误'))
      editTablesList.value = []
    }
  } catch (error) {
    console.error('加载表列表错误:', error)
    ElMessage.error('加载表列表失败：' + (error.response?.data?.detail || error.message || '未知错误'))
    editTablesList.value = []
  } finally {
    loadingEditTables.value = false
  }
}

// 确认编辑表
const confirmEditTables = async () => {
  if (!currentSessionId.value || !editTablesForm.value.selected_tables || editTablesForm.value.selected_tables.length === 0) {
    ElMessage.warning('请至少选择一个表')
    return
  }
  
  try {
    // 提取表名（如果tables是对象数组，需要提取name字段）
    const selectedTableNames = editTablesForm.value.selected_tables.map(t => 
      typeof t === 'string' ? t : (t.name || t)
    )
    
    // 调用更新会话API
    const response = await chatApi.updateSession(currentSessionId.value, {
      selected_tables: selectedTableNames
    })
    
    if (response.code === 200) {
      ElMessage.success('更新表选择成功')
      editTablesDialogVisible.value = false
      
      // 重新加载会话详情
      await selectSession(currentSessionId.value)
    } else {
      ElMessage.error(response.message || '更新失败')
    }
  } catch (error) {
    ElMessage.error('更新表选择失败：' + (error.response?.data?.detail || error.message || '未知错误'))
  }
}

// 重置编辑表表单
const resetEditTablesForm = () => {
  editTablesForm.value = {
    data_source_id: null,
    selected_tables: []
  }
  editTablesList.value = []
}

// 创建新对话（保留原有方法，改为显示对话框）
const createNewSession = () => {
  showCreateSessionDialog()
}

// 编辑对话标题
const editSessionTitle = async (session) => {
  try {
    const { value: newTitle } = await ElMessageBox.prompt(
      '请输入新的对话标题',
      '编辑标题',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputValue: session.title || '',
        inputPlaceholder: '请输入标题',
        inputValidator: (value) => {
          if (!value || !value.trim()) {
            return '标题不能为空'
          }
          if (value.length > 100) {
            return '标题长度不能超过100个字符'
          }
          return true
        }
      }
    )
    
    if (newTitle && newTitle.trim()) {
      const response = await chatApi.updateSession(session.id, {
        title: newTitle.trim()
      })
      
      if (response.code === 200) {
        ElMessage.success('标题更新成功')
        await loadSessions()
        // 如果当前正在查看这个会话，更新currentSession
        if (currentSessionId.value === session.id && currentSession.value) {
          currentSession.value.title = newTitle.trim()
        }
      }
    }
  } catch (error) {
    // 用户取消编辑
    if (error !== 'cancel') {
      ElMessage.error('更新标题失败：' + (error.response?.data?.detail || error.message || '未知错误'))
    }
  }
}

// 删除对话
const deleteSession = async (sessionId) => {
  // 找到要删除的会话信息
  const session = sessions.value.find(s => s.id === sessionId)
  const sessionTitle = session?.title || '该对话'
  
  try {
    await ElMessageBox.confirm(
      `确定要删除"${sessionTitle}"吗？删除后无法恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
        dangerouslyUseHTMLString: false
      }
    )
    
    // 用户确认删除
    await chatApi.deleteSession(sessionId)
    ElMessage.success('删除成功')
    await loadSessions()
    if (currentSessionId.value === sessionId) {
      currentSessionId.value = null
      messages.value = []
      currentSession.value = null
    }
  } catch (error) {
    // 用户取消删除或删除失败
    if (error !== 'cancel') {
      ElMessage.error('删除对话失败：' + (error.response?.data?.detail || error.message || '未知错误'))
    }
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
  
  // 立即添加用户消息到消息列表（临时消息，ID为负数）
  const tempUserMessageId = -Date.now()
  const tempUserMessage = {
    id: tempUserMessageId,
    role: 'user',
    content: question,
    created_at: new Date().toISOString(),
    session_id: currentSessionId.value
  }
  messages.value.push(tempUserMessage)
  
  // 立即添加一个加载中的AI回复消息
  const tempAssistantMessageId = -Date.now() - 1
  const tempAssistantMessage = {
    id: tempAssistantMessageId,
    role: 'assistant',
    content: '正在思考中...',
    created_at: new Date().toISOString(),
    session_id: currentSessionId.value,
    is_loading: true
  }
  messages.value.push(tempAssistantMessage)
  
  // 滚动到底部
  await nextTick()
  const messagesContainer = document.querySelector('.chat-messages')
  if (messagesContainer) {
    messagesContainer.scrollTop = messagesContainer.scrollHeight
  }
  
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
      // 移除临时消息
      messages.value = messages.value.filter(m => m.id !== tempUserMessageId && m.id !== tempAssistantMessageId)
      loading.value = false
      return
    }
    
    const response = await chatApi.sendMessage(currentSessionId.value, {
      question,
      data_source_id: dataSourceId,
      selected_tables: selectedTables
    })
    
    if (response.code === 200 || response.success) {
      // 如果标题被自动更新，重新加载会话列表以显示新标题
      await loadSessions()
      
      // 重新加载消息列表（这会替换临时消息）
      await loadMessages(currentSessionId.value)
      
      // 保存问题改写信息到最后一个用户消息（如果有）
      if (response.data?.question_rewrite) {
        const lastUserMessage = messages.value.filter(m => m.role === 'user').pop()
        if (lastUserMessage) {
          lastUserMessage.question_rewrite = response.data.question_rewrite
        }
      }
      
      // 将推荐问题和复杂SQL标记保存到对应的AI回复消息中
      if (response.data?.recommended_questions && response.data.recommended_questions.length > 0) {
        // 找到最后一条AI回复消息并添加推荐问题
        const lastAssistantMessage = messages.value.filter(m => m.role === 'assistant').pop()
        if (lastAssistantMessage) {
          lastAssistantMessage.recommended_questions = response.data.recommended_questions
        }
      }
      
      // 保存复杂SQL标记
      const lastAssistantMessage = messages.value.filter(m => m.role === 'assistant').pop()
      if (lastAssistantMessage) {
        if (response.data?.contains_complex_sql !== undefined) {
          lastAssistantMessage.contains_complex_sql = response.data.contains_complex_sql
        }
      }
    } else {
      // 如果失败但有SQL，允许用户编辑重试或继续用自然语言提问
      if (response.data?.sql && response.data?.can_retry) {
        // 重新加载消息以显示错误信息（这会替换临时消息）
        await loadMessages(currentSessionId.value)
        
        // 如果响应中包含推荐问题，保存到错误消息中
        if (response.data?.recommended_questions && response.data.recommended_questions.length > 0) {
          const lastAssistantMessage = messages.value.filter(m => m.role === 'assistant').pop()
          if (lastAssistantMessage) {
            lastAssistantMessage.recommended_questions = response.data.recommended_questions
          }
        }
        
        ElMessage.warning('SQL执行失败，您可以编辑SQL后重试或继续用自然语言提问')
      } else if (response.data?.warnings && response.data.warnings.length > 0) {
        // 权限警告
        ElMessage.warning({
          message: response.data.warnings[0] + (response.data.suggestion ? '\n' + response.data.suggestion : ''),
          duration: 5000,
          showClose: true
        })
      } else {
        ElMessage.error(response.message || '发送失败')
        // 移除临时消息
        messages.value = messages.value.filter(m => m.id !== tempUserMessageId && m.id !== tempAssistantMessageId)
      }
    }
  } catch (error) {
    ElMessage.error('发送消息失败：' + (error.message || '未知错误'))
    // 移除临时消息
    messages.value = messages.value.filter(m => m.id !== tempUserMessageId && m.id !== tempAssistantMessageId)
  } finally {
    loading.value = false
    
    // 滚动到底部
    await nextTick()
    const messagesContainer = document.querySelector('.chat-messages')
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight
    }
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

// 选择推荐问题（从AI回复下方的推荐问题）
const selectRecommendedQuestion = (question, message) => {
  inputText.value = question
  sendMessage()
}

// 选择推荐问题（保留原有方法，用于兼容）
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

// 继续用自然语言提问（当SQL执行错误时）
const continueWithNaturalLanguage = (message) => {
  // 将错误信息作为上下文，让用户继续提问
  if (message.error || message.error_message) {
    // 可以自动填充一些提示文本，或者直接让用户输入
    inputText.value = ''
    // 聚焦到输入框
    nextTick(() => {
      const input = document.querySelector('.chat-input textarea')
      if (input) {
        input.focus()
      }
    })
  }
}

// 复制SQL（带错误处理和降级方案）
const copySQL = (sql) => {
  // 检查SQL是否为空
  if (!sql || !sql.trim()) {
    ElMessage.warning('没有可复制的SQL')
    return
  }
  
  // 降级复制函数（使用document.execCommand）
  const fallbackCopy = (text) => {
    try {
      // 创建临时文本区域
      const textArea = document.createElement('textarea')
      textArea.value = text
      textArea.style.position = 'fixed'
      textArea.style.left = '-999999px'
      textArea.style.top = '-999999px'
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      
      // 尝试复制
      const successful = document.execCommand('copy')
      document.body.removeChild(textArea)
      
      if (successful) {
        ElMessage.success('SQL已复制到剪贴板')
      } else {
        ElMessage.error('复制失败，请手动复制')
      }
    } catch (err) {
      console.error('降级复制方案失败:', err)
      ElMessage.error('复制失败，请手动复制')
    }
  }
  
  // 优先使用现代 Clipboard API
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(sql).then(() => {
      ElMessage.success('SQL已复制到剪贴板')
    }).catch((err) => {
      console.error('Clipboard API复制失败:', err)
      // 降级到传统方法
      fallbackCopy(sql)
    })
  } else {
    // 浏览器不支持 Clipboard API，使用降级方案
    fallbackCopy(sql)
  }
}

// 导出数据
const exportData = async (message) => {
  // 显示导出对话框
  currentMessageForExport.value = message
  exportForm.value.format = 'excel'
  exportDialogVisible.value = true
}

// 确认导出
const confirmExport = async () => {
  if (!currentMessageForExport.value) {
    ElMessage.error('消息不存在')
    return
  }
  
  const message = currentMessageForExport.value
  const format = exportForm.value.format
  
  if (!format) {
    ElMessage.warning('请选择导出格式')
    return
  }
  
  // 关闭对话框
  exportDialogVisible.value = false
  
  // 如果选择生成接口
  if (format === 'generate_interface') {
    await generateInterfaceFromMessage(message)
    return
  }
  
  // 显示加载提示
  const loadingMessage = ElMessage({
    message: '正在导出，请稍候...',
    type: 'info',
    duration: 0
  })
  
  try {
    // 调用导出API
    const response = await chatApi.exportData(message.id, format)
    
    // 确定MIME类型
    let mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    if (format === 'png') {
      mimeType = 'image/png'
    } else if (format === 'csv') {
      mimeType = 'text/csv'
    } else if (format === 'json') {
      mimeType = 'application/json'
    } else if (format === 'xml') {
      mimeType = 'application/xml'
    }
    
    // 创建下载链接
    const blob = new Blob([response.data], { type: mimeType })
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
      const extensions = {
        'png': '.png',
        'csv': '.csv',
        'json': '.json',
        'xml': '.xml',
        'excel': '.xlsx'
      }
      filename += extensions[format] || '.xlsx'
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
    ElMessage.error('导出失败：' + (error.response?.data?.detail || error.message || '未知错误'))
  } finally {
    resetExportForm()
  }
}

// 重置导出表单
const resetExportForm = () => {
  exportForm.value = {
    format: 'excel'
  }
  currentMessageForExport.value = null
}

// 从问数结果生成接口
const generateInterfaceFromMessage = async (message) => {
  try {
    // 检查消息是否有SQL
    if (!message.sql || !message.sql.trim()) {
      ElMessage.warning('该消息没有SQL语句，无法生成接口')
      return
    }
    
    // 获取会话标题作为默认路径
    let defaultPath = `/query-${message.id}`
    if (currentSession.value && currentSession.value.title) {
      // 使用会话标题生成路径（清理特殊字符，转换为URL友好格式）
      const sessionTitle = currentSession.value.title
        .replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '-')  // 替换特殊字符为连字符
        .replace(/-+/g, '-')  // 合并多个连字符
        .replace(/^-|-$/g, '')  // 移除首尾连字符
        .toLowerCase()
      
      if (sessionTitle && sessionTitle.length > 0) {
        // 限制长度，避免路径过长
        const maxLength = 30
        defaultPath = `/${sessionTitle.length > maxLength ? sessionTitle.substring(0, maxLength) : sessionTitle}`
      }
    }
    
    // 显示接口路径输入对话框（只输入/api/query之后的路径）
    const { value: proxyPath } = await ElMessageBox.prompt(
      '请输入接口路径（固定前缀：/api/query）',
      '生成服务接口',
      {
        confirmButtonText: '生成',
        cancelButtonText: '取消',
        inputPlaceholder: '/school-count',
        inputValue: defaultPath,
        inputValidator: (value) => {
          if (!value || !value.trim()) {
            return '接口路径不能为空'
          }
          // 如果用户输入了/api/query前缀，提示只需要后续路径
          if (value.startsWith('/api/query')) {
            return '只需输入/api/query之后的路径，例如：/school-count'
          }
          if (!value.startsWith('/')) {
            return '接口路径必须以/开头'
          }
          return true
        }
      }
    ).catch(() => ({ value: null }))
    
    if (!proxyPath) return
    
    // 显示加载提示
    const loadingMessage = ElMessage({
      message: '正在生成接口，请稍候...',
      type: 'info',
      duration: 0
    })
    
    try {
      // 调用生成接口API
      const response = await chatApi.generateInterface(message.id, proxyPath)
      
      loadingMessage.close()
      
      if (response.code === 200 || response.success) {
        const data = response.data
        ElMessage.success('接口生成成功！')
        
        // 显示成功对话框，包含接口信息和复制按钮
        const copyUrl = () => {
          const url = data.full_url
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(url).then(() => {
              ElMessage.success('URL已复制到剪贴板')
            }).catch(() => {
              // 降级方案
              const textArea = document.createElement('textarea')
              textArea.value = url
              textArea.style.position = 'fixed'
              textArea.style.left = '-999999px'
              document.body.appendChild(textArea)
              textArea.select()
              document.execCommand('copy')
              document.body.removeChild(textArea)
              ElMessage.success('URL已复制到剪贴板')
            })
          } else {
            // 降级方案
            const textArea = document.createElement('textarea')
            textArea.value = url
            textArea.style.position = 'fixed'
            textArea.style.left = '-999999px'
            document.body.appendChild(textArea)
            textArea.select()
            document.execCommand('copy')
            document.body.removeChild(textArea)
            ElMessage.success('URL已复制到剪贴板')
          }
        }
        
        // 显示成功对话框，包含接口信息和复制按钮
        ElMessageBox.alert(
          `<div style="text-align: left;">
            <p style="margin: 8px 0;"><strong>接口ID：</strong>${data.interface_id}</p>
            <p style="margin: 8px 0;"><strong>接口名称：</strong>${data.interface_name}</p>
            <p style="margin: 8px 0;"><strong>接口路径：</strong><code style="background: #f5f5f5; padding: 2px 6px; border-radius: 3px;">${data.proxy_path}</code></p>
            <p style="margin: 8px 0;"><strong>完整URL：</strong><code style="background: #f5f5f5; padding: 2px 6px; border-radius: 3px; word-break: break-all; display: inline-block; max-width: 100%;">${data.full_url}</code></p>
            <div style="margin: 12px 0; padding: 10px; background: #f0f9ff; border-left: 3px solid #409eff; border-radius: 4px;">
              <p style="margin: 4px 0; font-weight: 500; color: #409eff;">分页参数说明：</p>
              <p style="margin: 4px 0; font-size: 13px; color: #606266;">
                • <strong>pageSize</strong>：每页数量，默认值为 <code style="background: #fff; padding: 1px 4px; border-radius: 2px;">10</code>
              </p>
              <p style="margin: 4px 0; font-size: 13px; color: #606266;">
                • <strong>pageNumber</strong>：页码，默认值为 <code style="background: #fff; padding: 1px 4px; border-radius: 2px;">1</code>
              </p>
              <p style="margin: 4px 0; font-size: 12px; color: #909399; margin-top: 6px;">
                示例：<code style="background: #fff; padding: 1px 4px; border-radius: 2px;">${data.full_url}?pageNumber=1&pageSize=10</code>
              </p>
            </div>
            <p style="margin-top: 15px;">
              <button id="copy-url-btn" style="padding: 6px 15px; background: #409eff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px;">复制URL</button>
            </p>
          </div>`,
          '接口生成成功',
          {
            dangerouslyUseHTMLString: true,
            confirmButtonText: '查看接口文档',
            cancelButtonText: '关闭',
            showCancelButton: true,
            beforeClose: (action, instance, done) => {
              // 移除事件监听器
              const btn = document.getElementById('copy-url-btn')
              if (btn) {
                btn.removeEventListener('click', copyUrl)
              }
              done()
            }
          }
        ).then(() => {
          // 跳转到接口文档页面
          window.open(`/#/interface-list?id=${data.interface_id}`, '_blank')
        }).catch(() => {
          // 用户点击关闭
        })
        
        // 等待DOM更新后绑定复制按钮事件
        await nextTick()
        const copyBtn = document.getElementById('copy-url-btn')
        if (copyBtn) {
          copyBtn.addEventListener('click', copyUrl)
        }
      } else {
        ElMessage.error(response.message || '生成接口失败')
      }
    } catch (error) {
      loadingMessage.close()
      throw error
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('生成接口失败：' + (error.response?.data?.detail || error.message || '未知错误'))
    }
  }
}

// 切换图表类型
const changeChartType = async (message) => {
  // 更新图表类型后，重新渲染图表
  await nextTick()
  // 确保DOM已更新
  setTimeout(() => {
    renderChart(message)
  }, 100)
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
  // 使用消息ID作为容器选择器，确保每个消息有独立的图表容器
  const container = document.getElementById(chartId)
  if (!container) {
    console.warn(`图表容器不存在: ${chartId}`)
    return
  }
  
  // 销毁旧图表
  if (chartInstances.value[chartId]) {
    chartInstances.value[chartId].dispose()
    delete chartInstances.value[chartId]
  }
  
  // 确保容器有尺寸
  if (container.offsetWidth === 0 || container.offsetHeight === 0) {
    console.warn(`图表容器尺寸为0: ${chartId}`)
    return
  }
  
  // 创建新图表
  const chart = echarts.init(container)
  const config = message.chart_config
  
  // 如果没有配置，尝试从数据生成配置
  if (!config) {
    console.warn('图表配置不存在')
    return
  }
  
  // 获取数据用于单条数据时的图表生成
  const data = message.data || []
  const columns = message.columns || (data.length > 0 ? Object.keys(data[0]) : [])
  
  // 处理单条数据的情况
  const hasData = data && data.length > 0
  const isSingleRow = hasData && data.length === 1
  
  let option = {
    title: {
      text: config.title || '数据图表',
      left: 'center',
      textStyle: {
        fontSize: 16
      }
    },
    tooltip: {
      trigger: message.chart_type !== 'pie' ? 'axis' : 'item'
    },
    legend: {
      show: message.chart_type !== 'pie' && config.series && config.series.length > 1,
      data: config.series ? config.series.map(s => s.name || '系列') : []
    }
  }
  
  if (message.chart_type === 'bar') {
    // 柱状图：处理单条数据的情况
    let xAxisData = config.xAxis?.data || []
    let seriesData = config.series || []
    
    // 如果配置为空且只有一条数据，从数据生成配置
    if (isSingleRow && (!xAxisData.length || !seriesData.length)) {
      const row = data[0]
      if (columns.length >= 2) {
        // 两列：第一列作为X轴，第二列作为Y轴
        xAxisData = [String(row[columns[0]] || '数据')]
        seriesData = [{
          name: columns[1] || '数值',
          type: 'bar',
          data: [Number(row[columns[1]]) || 0]
        }]
      } else if (columns.length === 1) {
        // 单列：使用列名作为X轴，值作为Y轴
        xAxisData = [columns[0] || '数据']
        seriesData = [{
          name: columns[0] || '数值',
          type: 'bar',
          data: [Number(row[columns[0]]) || 0]
        }]
      }
    }
    
    option = {
      ...option,
      xAxis: {
        type: 'category',
        data: xAxisData,
        ...(config.xAxis || {})
      },
      yAxis: config.yAxis || {
        type: 'value'
      },
      series: seriesData
    }
  } else if (message.chart_type === 'line') {
    // 折线图：处理单条数据的情况
    let xAxisData = config.xAxis?.data || []
    let seriesData = config.series || []
    
    if (isSingleRow && (!xAxisData.length || !seriesData.length)) {
      const row = data[0]
      if (columns.length >= 2) {
        xAxisData = [String(row[columns[0]] || '数据')]
        seriesData = [{
          name: columns[1] || '数值',
          type: 'line',
          data: [Number(row[columns[1]]) || 0],
          smooth: true,
          symbol: 'circle',
          symbolSize: 6
        }]
      } else if (columns.length === 1) {
        xAxisData = [columns[0] || '数据']
        seriesData = [{
          name: columns[0] || '数值',
          type: 'line',
          data: [Number(row[columns[0]]) || 0],
          smooth: true,
          symbol: 'circle',
          symbolSize: 6
        }]
      }
    } else {
      seriesData = (seriesData || []).map(s => ({
        ...s,
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6
      }))
    }
    
    option = {
      ...option,
      xAxis: {
        type: 'category',
        data: xAxisData,
        ...(config.xAxis || {})
      },
      yAxis: config.yAxis || {
        type: 'value'
      },
      series: seriesData
    }
  } else if (message.chart_type === 'pie') {
    // 饼图：处理单条数据的情况
    let seriesData = config.series || []
    
    if (isSingleRow && (!seriesData.length || !seriesData[0]?.data?.length)) {
      const row = data[0]
      const pieData = []
      
      if (columns.length >= 2) {
        // 两列：第一列作为名称，第二列作为数值
        pieData.push({
          name: String(row[columns[0]] || '数据'),
          value: Number(row[columns[1]]) || 0
        })
      } else if (columns.length === 1) {
        // 单列：使用列名作为名称，值作为数值
        pieData.push({
          name: columns[0] || '数据',
          value: Number(row[columns[0]]) || 0
        })
      }
      
      seriesData = [{
        type: 'pie',
        radius: '60%',
        data: pieData
      }]
    } else if (seriesData.length > 0 && seriesData[0].data) {
      // 确保series格式正确
      seriesData = seriesData.map(s => ({
        type: 'pie',
        radius: s.radius || '60%',
        data: s.data || []
      }))
    }
    
    option = {
      ...option,
      tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b}: {c} ({d}%)'
      },
      series: seriesData
    }
  } else if (message.chart_type === 'scatter') {
    // 散点图：处理单条数据的情况
    let seriesData = config.series || []
    
    if (isSingleRow && (!seriesData.length || !seriesData[0]?.data?.length)) {
      const row = data[0]
      if (columns.length >= 2) {
        seriesData = [{
          type: 'scatter',
          data: [[Number(row[columns[0]]) || 0, Number(row[columns[1]]) || 0]],
          symbolSize: 8
        }]
      } else if (columns.length === 1) {
        seriesData = [{
          type: 'scatter',
          data: [[0, Number(row[columns[0]]) || 0]],
          symbolSize: 8
        }]
      }
    } else {
      seriesData = (seriesData || []).map(s => ({
        ...s,
        type: 'scatter',
        symbolSize: s.symbolSize || 8
      }))
    }
    
    option = {
      ...option,
      xAxis: config.xAxis || {
        type: 'value'
      },
      yAxis: config.yAxis || {
        type: 'value'
      },
      series: seriesData
    }
  } else if (message.chart_type === 'area') {
    // 面积图：处理单条数据的情况
    let xAxisData = config.xAxis?.data || []
    let seriesData = config.series || []
    
    if (isSingleRow && (!xAxisData.length || !seriesData.length)) {
      const row = data[0]
      if (columns.length >= 2) {
        xAxisData = [String(row[columns[0]] || '数据')]
        seriesData = [{
          name: columns[1] || '数值',
          type: 'line',
          data: [Number(row[columns[1]]) || 0],
          areaStyle: {},
          smooth: true
        }]
      } else if (columns.length === 1) {
        xAxisData = [columns[0] || '数据']
        seriesData = [{
          name: columns[0] || '数值',
          type: 'line',
          data: [Number(row[columns[0]]) || 0],
          areaStyle: {},
          smooth: true
        }]
      }
    } else {
      seriesData = (seriesData || []).map(s => ({
        ...s,
        type: 'line',
        areaStyle: {},
        smooth: true
      }))
    }
    
    option = {
      ...option,
      xAxis: {
        type: 'category',
        data: xAxisData,
        ...(config.xAxis || {})
      },
      yAxis: config.yAxis || {
        type: 'value'
      },
      series: seriesData
    }
  }
  
  chart.setOption(option, true) // 使用true强制重新渲染
  chartInstances.value[chartId] = chart
  
  // 添加窗口resize监听器（如果还没有）
  if (!window.chartResizeHandler) {
    window.chartResizeHandler = () => {
      Object.values(chartInstances.value).forEach(chart => {
        try {
          if (chart && !chart.isDisposed()) {
            chart.resize()
          }
        } catch (error) {
          // 忽略已销毁的图表
        }
      })
    }
    window.addEventListener('resize', window.chartResizeHandler)
  }
  
  // 监听窗口大小变化，自动调整图表大小
  const resizeHandler = () => {
    if (chartInstances.value[chartId]) {
      chartInstances.value[chartId].resize()
    }
  }
  window.addEventListener('resize', resizeHandler)
  
  // 保存resize处理器，以便后续清理
  if (!message._resizeHandler) {
    message._resizeHandler = resizeHandler
  }
}

// 格式化时间
// 格式化解释文本（支持Markdown格式）
const formatExplanation = (text) => {
  if (!text) return ''
  
  // 将换行符转换为 <br>
  let formatted = text.replace(/\n/g, '<br>')
  
  // 处理 **粗体** 格式
  formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  
  // 处理标题（## 标题）
  formatted = formatted.replace(/^##\s+(.+)$/gm, '<h3 style="margin: 12px 0 8px 0; font-size: 16px; font-weight: 600; color: #303133;">$1</h3>')
  
  return formatted
}

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

// 清理资源
onUnmounted(() => {
  // 清理所有图表实例
  Object.keys(chartInstances.value).forEach(chartId => {
    try {
      if (chartInstances.value[chartId]) {
        chartInstances.value[chartId].dispose()
      }
    } catch (error) {
      console.warn(`清理图表实例失败: ${chartId}`, error)
    }
  })
  chartInstances.value = {}
  
  // 清理窗口resize监听器（如果有）
  if (window.chartResizeHandler) {
    window.removeEventListener('resize', window.chartResizeHandler)
    delete window.chartResizeHandler
  }
})

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

.table-description {
  margin-left: 4px;
  font-size: 11px;
  color: #f56c6c;
  font-weight: normal;
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
  padding: 16px;
  background: linear-gradient(135deg, #f0f9ff 0%, #e6f7ff 100%);
  border-left: 4px solid #1890ff;
  border-radius: 8px;
  margin-top: 16px;
  margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.1);
  line-height: 1.8;
  color: #303133;
  font-size: 14px;
}

.explanation-section :deep(strong) {
  color: #1890ff;
  font-weight: 600;
}

.explanation-section :deep(h3) {
  margin: 12px 0 8px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
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

/* 推荐问题样式（现在显示在AI回复下方） */
.recommended-questions-section {
  margin-top: 16px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.recommended-questions-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-weight: 600;
  color: #606266;
  font-size: 14px;
}

.recommended-questions-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.recommended-question-tag {
  cursor: pointer;
  transition: all 0.2s;
  padding: 6px 12px;
  font-size: 13px;
}

.recommended-question-tag:hover {
  background: #409eff;
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
}

.question-rewrite-info {
  margin-top: 8px;
  padding: 8px;
  background: #f0f9ff;
  border-left: 3px solid #409eff;
  border-radius: 4px;
}

.rewrite-details {
  padding: 8px 0;
}

.rewrite-item {
  margin-bottom: 8px;
  font-size: 13px;
}

.rewrite-item:last-child {
  margin-bottom: 0;
}

.rewrite-label {
  color: #606266;
  font-weight: 500;
  margin-right: 8px;
}

.rewrite-value {
  color: #303133;
}

.rewrite-value.rewritten {
  color: #409eff;
  font-weight: 500;
}

.rewrite-changes {
  margin: 4px 0 0 20px;
  padding: 0;
  color: #909399;
  font-size: 12px;
}

.rewrite-changes li {
  margin-bottom: 4px;
}

.error-actions {
  margin-top: 12px;
}

.error-description {
  margin-bottom: 12px;
  font-size: 13px;
  line-height: 1.6;
}

.error-description p {
  margin: 8px 0;
  color: #606266;
}

.error-sql {
  background: #282c34;
  color: #abb2bf;
  padding: 8px 12px;
  border-radius: 4px;
  overflow-x: auto;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  margin: 8px 0;
  max-height: 150px;
  overflow-y: auto;
}

.error-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.complex-sql-notice {
  margin-top: 12px;
}

.complex-sql-info {
  font-size: 13px;
  line-height: 1.6;
  color: #606266;
}

.complex-sql-info p {
  margin: 8px 0;
}

.complex-sql-info ul {
  margin: 8px 0 0 20px;
  padding: 0;
}

.complex-sql-info li {
  margin-bottom: 4px;
}

/* 表字段悬停提示样式 */
:deep(.table-fields-tooltip) {
  max-width: 500px !important;
}

:deep(.table-fields-tooltip .el-tooltip__inner) {
  background-color: #ffffff !important;
  color: #303133 !important;
  text-align: left;
  line-height: 1.6;
  white-space: normal;
  word-wrap: break-word;
  padding: 0 !important;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

/* 加载中消息样式 */
.loading-message {
  display: flex;
  align-items: center;
  padding: 12px;
  color: #909399;
  font-size: 14px;
}

.loading-message .el-icon {
  font-size: 16px;
}

</style>

