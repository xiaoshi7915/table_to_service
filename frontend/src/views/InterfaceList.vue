<template>
  <div class="interface-list">
    <el-card class="main-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon class="title-icon"><List /></el-icon>
            <span class="title-text">接口清单</span>
            <el-tag v-if="interfaces.length > 0" type="info" size="small" class="count-tag">
              {{ interfaces.length }}
            </el-tag>
          </div>
          <div class="header-actions">
            <el-button type="primary" @click="handleCreate" class="action-btn">
              <el-icon><Plus /></el-icon>
              新建接口
            </el-button>
            <el-button @click="loadInterfaces" :loading="loading" class="action-btn">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>
      
      <!-- 筛选条件 -->
      <el-card class="filter-card" shadow="never">
        <el-form :inline="true" class="filter-form">
          <el-form-item label="数据库" class="filter-item">
            <el-select 
              v-model="filters.database_id" 
              placeholder="全部"
              clearable
              class="filter-select"
              @change="loadInterfaces"
            >
              <el-option
                v-for="db in databases"
                :key="db.id"
                :label="db.name"
                :value="db.id"
              />
            </el-select>
          </el-form-item>
          
          <el-form-item label="状态" class="filter-item">
            <el-select 
              v-model="filters.status" 
              placeholder="全部"
              clearable
              class="filter-select"
              @change="loadInterfaces"
            >
              <el-option label="激活" value="active" />
              <el-option label="禁用" value="inactive" />
              <el-option label="草稿" value="draft" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="录入模式" class="filter-item">
            <el-select 
              v-model="filters.entry_mode" 
              placeholder="全部"
              clearable
              class="filter-select"
              @change="loadInterfaces"
            >
              <el-option label="专家模式" value="expert" />
              <el-option label="图形模式" value="graphical" />
            </el-select>
          </el-form-item>
        </el-form>
      </el-card>
      
      <!-- 接口列表 -->
      <el-table
        :data="interfaces"
        class="interface-table"
        v-loading="loading"
        stripe
        :header-cell-style="{ background: '#f5f7fa', color: '#606266', fontWeight: '600' }"
      >
        <el-table-column prop="interface_name" label="接口名称" min-width="200" />
        <el-table-column prop="database_name" label="数据库" width="150" />
        <el-table-column prop="entry_mode" label="录入模式" width="120">
          <template #default="{ row }">
            <el-tag :type="row.entry_mode === 'expert' ? 'success' : 'info'">
              {{ row.entry_mode === 'expert' ? '专家模式' : '图形模式' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="http_method" label="请求方式" width="100">
          <template #default="{ row }">
            <el-tag :type="getMethodType(row.http_method)">
              {{ row.http_method }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="proxy_path" label="接口路径" min-width="200" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">
              {{ row.status === 'active' ? '激活' : row.status === 'inactive' ? '禁用' : '草稿' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="460" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" @click="handleView(row)" class="btn-view">
                <el-icon><View /></el-icon>
                查看
              </el-button>
              <el-button size="small" type="primary" @click="handleExecute(row)" class="btn-execute">
                <el-icon><CaretRight /></el-icon>
                执行
              </el-button>
              <el-button size="small" type="warning" @click="handleEdit(row)" class="btn-edit">
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
              <el-button size="small" type="success" @click="handleViewApiDoc(row)" class="btn-doc">
                <el-icon><Document /></el-icon>
                文档
              </el-button>
              <el-button size="small" @click="handleCopyInterface(row)" class="btn-copy">
                <el-icon><CopyDocument /></el-icon>
                复制
              </el-button>
              <el-button size="small" type="danger" @click="handleDelete(row)" class="btn-delete">
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination-container">
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
    
    <!-- 接口详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="接口详情"
      width="85%"
      :close-on-click-modal="false"
      class="detail-dialog"
    >
      <div v-if="currentInterface">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="接口名称">{{ currentInterface.interface_name }}</el-descriptions-item>
          <el-descriptions-item label="数据库">{{ currentInterface.database_name }}</el-descriptions-item>
          <el-descriptions-item label="录入模式">
            <el-tag :type="currentInterface.entry_mode === 'expert' ? 'success' : 'info'">
              {{ currentInterface.entry_mode === 'expert' ? '专家模式' : '图形模式' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="currentInterface.status === 'active' ? 'success' : 'info'">
              {{ currentInterface.status === 'active' ? '激活' : currentInterface.status === 'inactive' ? '禁用' : '草稿' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="请求方式">
            <el-tag :type="getMethodType(currentInterface.http_method)">{{ currentInterface.http_method }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="接口路径">
            <code style="color: #409eff;">{{ currentInterface.proxy_path }}</code>
          </el-descriptions-item>
          <el-descriptions-item label="完整URL" :span="2">
            <el-text type="primary" copyable style="font-family: monospace; word-break: break-all;">
              {{ interfaceFullUrl || getInterfaceFullUrl(currentInterface) }}
            </el-text>
          </el-descriptions-item>
          <el-descriptions-item label="接口描述" :span="2">
            {{ currentInterface.interface_description || '无' }}
          </el-descriptions-item>
        </el-descriptions>
        
        <el-divider>SQL配置</el-divider>
        <el-card v-if="currentInterface.entry_mode === 'expert'">
          <pre style="background: #f5f5f5; padding: 15px; border-radius: 4px; overflow-x: auto;">{{ currentInterface.sql_statement }}</pre>
        </el-card>
        <el-card v-else>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="表名">{{ currentInterface.table_name }}</el-descriptions-item>
            <el-descriptions-item label="选择字段">
              {{ (currentInterface.selected_fields || []).join(', ') || '全部' }}
            </el-descriptions-item>
          </el-descriptions>
          <div v-if="currentInterface.where_conditions && currentInterface.where_conditions.length > 0" style="margin-top: 15px;">
            <strong>WHERE条件:</strong>
            <el-tag v-for="(cond, idx) in currentInterface.where_conditions" :key="idx" style="margin-left: 5px;">
              {{ formatCondition(cond) }}
            </el-tag>
          </div>
          <div v-if="currentInterface.order_by_fields && currentInterface.order_by_fields.length > 0" style="margin-top: 15px;">
            <strong>ORDER BY:</strong>
            <el-tag v-for="(order, idx) in currentInterface.order_by_fields" :key="idx" style="margin-left: 5px;">
              {{ order.field }} {{ order.direction }}
            </el-tag>
          </div>
        </el-card>
        
        <el-divider>入参出参样例</el-divider>
        <el-card>
          <el-tabs>
            <el-tab-pane label="请求参数">
              <el-table 
                v-if="currentInterface.request_parameters && currentInterface.request_parameters.length > 0"
                :data="currentInterface.request_parameters" 
                border
                style="width: 100%"
              >
                <el-table-column prop="name" label="参数名" width="150" />
                <el-table-column prop="type" label="类型" width="100" />
                <el-table-column prop="description" label="描述" />
                <el-table-column prop="constraint" label="约束" width="100" />
                <el-table-column prop="location" label="位置" width="100" />
              </el-table>
              <el-empty v-else description="无请求参数" />
              
              <div v-if="requestSample && Object.keys(requestSample).length > 0" style="margin-top: 20px;">
                <strong>请求样例:</strong>
                <pre style="background: #f5f5f5; padding: 15px; border-radius: 4px; overflow-x: auto; margin-top: 10px;">{{ JSON.stringify(requestSample, null, 2) }}</pre>
              </div>
            </el-tab-pane>
            <el-tab-pane label="响应样例">
              <div v-if="responseSample" style="position: relative;">
                <div style="margin-bottom: 10px; text-align: right;">
                  <el-button size="small" type="primary" @click="copyToClipboard(JSON.stringify(responseSample, null, 2))">
                    <el-icon><DocumentCopy /></el-icon>
                    复制
                  </el-button>
                </div>
                <pre class="code-block-light">{{ JSON.stringify(responseSample, null, 2) }}</pre>
              </div>
              <el-empty v-else description="暂无响应样例" />
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </div>
    </el-dialog>
    
    <!-- API文档对话框 -->
    <el-dialog
      v-model="apiDocDialogVisible"
      title="API接口文档"
      width="90%"
      :close-on-click-modal="false"
      class="api-doc-dialog"
      :show-close="true"
    >
      <div v-if="apiDoc" class="api-doc-content">
        <el-card class="api-info-card" shadow="never">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="接口名称">
              <el-text type="primary" size="large">{{ apiDoc.title }}</el-text>
            </el-descriptions-item>
            <el-descriptions-item label="请求方式">
              <el-tag :type="getMethodType(apiDoc.method)" size="large">{{ apiDoc.method }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="接口路径" :span="2">
              <el-text type="primary" copyable style="font-family: monospace;">{{ apiDoc.full_url }}</el-text>
            </el-descriptions-item>
            <el-descriptions-item label="接口描述" :span="2">
              {{ apiDoc.description || '无描述' }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
        
        <el-divider>
          <el-icon><Document /></el-icon>
          <span style="margin-left: 8px;">请求参数</span>
        </el-divider>
        <el-table 
          v-if="apiDoc.request.parameters && apiDoc.request.parameters.length > 0"
          :data="apiDoc.request.parameters" 
          border
          style="width: 100%"
        >
          <el-table-column prop="name" label="参数名" width="150" />
          <el-table-column prop="type" label="类型" width="100" />
          <el-table-column prop="description" label="描述" />
          <el-table-column prop="constraint" label="约束" width="100" />
          <el-table-column prop="location" label="位置" width="100" />
        </el-table>
        <el-empty v-else description="无请求参数" />
        
        <el-divider>
          <el-icon><Edit /></el-icon>
          <span style="margin-left: 8px;">请求示例</span>
          <el-button size="small" type="primary" @click="copyRequestExample(apiDoc)" style="margin-left: 10px;">
            <el-icon><DocumentCopy /></el-icon>
            复制
          </el-button>
        </el-divider>
        <el-card class="example-card" shadow="hover">
          <el-tabs type="border-card">
            <el-tab-pane :label="apiDoc.method === 'GET' ? 'Query参数' : '请求体'">
              <div style="position: relative;">
                <pre class="code-block-light">{{ JSON.stringify(apiDoc.request.sample, null, 2) }}</pre>
              </div>
            </el-tab-pane>
            <el-tab-pane label="cURL示例">
              <div style="position: relative;">
                <pre class="code-block-light">{{ generateCurlExample(apiDoc) }}</pre>
              </div>
            </el-tab-pane>
          </el-tabs>
        </el-card>
        
        <el-divider>
          <el-icon><SuccessFilled /></el-icon>
          <span style="margin-left: 8px;">响应示例</span>
          <el-button size="small" type="primary" @click="copyToClipboard(JSON.stringify(apiDoc.response.sample, null, 2))" style="margin-left: 10px;">
            <el-icon><DocumentCopy /></el-icon>
            复制
          </el-button>
        </el-divider>
        <el-card class="example-card" shadow="hover">
          <pre class="code-block-light">{{ JSON.stringify(apiDoc.response.sample, null, 2) }}</pre>
        </el-card>
        
        <el-divider>
          <el-icon><InfoFilled /></el-icon>
          <span style="margin-left: 8px;">其他信息</span>
        </el-divider>
        <el-card class="api-info-card" shadow="never">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="分页">
              <el-tag :type="apiDoc.pagination.enabled ? 'success' : 'info'">
                {{ apiDoc.pagination.enabled ? '启用' : '禁用' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="认证">
              <el-tag :type="apiDoc.authentication.required ? 'warning' : 'success'">
                {{ apiDoc.authentication.required ? apiDoc.authentication.type : '无需认证' }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </div>
    </el-dialog>
    
    <!-- 接口执行对话框 -->
    <el-dialog
      v-model="executeDialogVisible"
      title="执行接口测试"
      width="85%"
      :close-on-click-modal="false"
      class="execute-dialog"
      :show-close="true"
    >
      <div v-if="currentInterface">
        <!-- 接口元数据信息 -->
        <el-card class="metadata-card" shadow="never">
          <template #header>
            <div class="metadata-header">
              <el-icon :size="20" style="margin-right: 8px;"><InfoFilled /></el-icon>
              <span>接口元数据信息</span>
            </div>
          </template>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="接口名称">
              <el-text type="primary" strong>{{ currentInterface.interface_name }}</el-text>
            </el-descriptions-item>
            <el-descriptions-item label="接口路径">
              <el-text copyable>{{ currentInterface.proxy_path }}</el-text>
            </el-descriptions-item>
            <el-descriptions-item label="请求方式">
              <el-tag :type="getMethodType(currentInterface.http_method)" size="small">
                {{ currentInterface.http_method }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="数据库">
              {{ currentInterface.database_name || '未知' }}
            </el-descriptions-item>
            <el-descriptions-item label="录入模式">
              <el-tag :type="currentInterface.entry_mode === 'expert' ? 'success' : 'info'" size="small">
                {{ currentInterface.entry_mode === 'expert' ? '专家模式' : '图形模式' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="currentInterface.status === 'active' ? 'success' : 'info'" size="small">
                {{ currentInterface.status === 'active' ? '激活' : currentInterface.status === 'inactive' ? '禁用' : '草稿' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="分页" v-if="currentInterface.enable_pagination">
              <el-tag type="success" size="small">已启用</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="最大查询数" v-if="currentInterface.max_query_count">
              {{ currentInterface.max_query_count }}
            </el-descriptions-item>
            <el-descriptions-item label="接口描述" :span="2" v-if="currentInterface.interface_description">
              {{ currentInterface.interface_description }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
        
        <!-- 参数输入 -->
        <el-form :model="executeParams" label-width="120px" v-if="requestParameters.length > 0">
          <el-form-item
            v-for="param in requestParameters"
            :key="param.name"
            :label="param.name"
            :required="param.constraint === 'required'"
          >
            <el-input
              v-model="executeParams[param.name]"
              :placeholder="param.description || `请输入${param.name}`"
              style="width: 100%;"
            />
            <div style="font-size: 12px; color: #999; margin-top: 5px;">
              类型: {{ param.type }} | 位置: {{ param.location }}
            </div>
          </el-form-item>
        </el-form>
        <el-empty v-else description="该接口无需参数" :image-size="100" />
        
        <!-- 分页参数 -->
        <el-divider v-if="currentInterface.enable_pagination">分页参数</el-divider>
        <el-form :model="executeParams" label-width="120px" v-if="currentInterface.enable_pagination">
          <el-form-item label="页码">
            <el-input-number v-model="executeParams.page" :min="1" />
          </el-form-item>
          <el-form-item label="每页数量">
            <el-input-number v-model="executeParams.page_size" :min="1" :max="100" />
          </el-form-item>
        </el-form>
        
        <!-- 执行按钮 -->
        <div style="margin-top: 20px; text-align: right;">
          <el-button @click="executeDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="doExecute" :loading="executing">
            <el-icon><CaretRight /></el-icon>
            执行查询
          </el-button>
        </div>
        
        <!-- 执行结果 -->
        <el-divider v-if="executeResult">
          <el-icon><List /></el-icon>
          <span style="margin-left: 8px;">执行结果</span>
        </el-divider>
        <el-card v-if="executeResult" class="result-card" shadow="hover">
          <!-- 执行状态信息 -->
          <el-alert
            :type="executeResult.success ? 'success' : 'error'"
            :title="executeResult.success ? '执行成功' : '执行失败'"
            :description="executeResult.message"
            :closable="false"
            show-icon
            style="margin-bottom: 20px;"
          />
          
          <!-- 分页信息 -->
          <el-descriptions 
            v-if="executeResult.data && (executeResult.data.total !== undefined || executeResult.data.count !== undefined)"
            :column="2" 
            border
            class="pagination-info"
          >
            <el-descriptions-item label="数据总数" v-if="executeResult.data.total !== undefined">
              <el-tag type="info">{{ executeResult.data.total }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="返回条数" v-if="executeResult.data.count !== undefined">
              <el-tag type="success">{{ executeResult.data.count }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="当前页码" v-if="executeResult.data.pageNumber !== undefined">
              <el-tag>{{ executeResult.data.pageNumber }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="每页数量" v-if="executeResult.data.pageSize !== undefined">
              <el-tag>{{ executeResult.data.pageSize }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="页码" v-if="executeResult.data.page !== undefined">
              <el-tag>{{ executeResult.data.page }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="每页大小" v-if="executeResult.data.page_size !== undefined">
              <el-tag>{{ executeResult.data.page_size }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
          
          <el-divider>
            <el-icon><Document /></el-icon>
            <span style="margin-left: 8px;">返回数据</span>
          </el-divider>
          
          <!-- 数据格式转换工具栏 -->
          <div class="data-format-toolbar" v-if="executeResult.data?.data && executeResult.data.data.length > 0">
            <div class="format-label">数据格式：</div>
            <el-radio-group v-model="dataFormat" size="small">
              <el-radio-button label="table">表格</el-radio-button>
              <el-radio-button label="json">JSON</el-radio-button>
              <el-radio-button label="xml">XML</el-radio-button>
              <el-radio-button label="csv">CSV</el-radio-button>
            </el-radio-group>
            <el-button 
              size="small" 
              type="primary" 
              @click="copyFormattedData"
              class="copy-data-btn"
            >
              <el-icon><CopyDocument /></el-icon>
              复制数据
            </el-button>
            <el-button 
              size="small" 
              @click="downloadFormattedData"
              class="download-data-btn"
            >
              <el-icon><Download /></el-icon>
              下载数据
            </el-button>
          </div>
          
          <!-- 表格视图 -->
          <el-table
            v-if="dataFormat === 'table'"
            :data="executeResult.data?.data || []"
            style="width: 100%"
            max-height="400"
            border
          >
            <el-table-column
              v-for="col in getTableColumns(executeResult.data?.data || [])"
              :key="col"
              :prop="col"
              :label="col"
            />
          </el-table>
          
          <!-- JSON视图 - 显示完整响应数据 -->
          <div v-if="dataFormat === 'json'" class="data-viewer">
            <pre class="code-block">{{ formatAsJSON(executeResult.data || {}) }}</pre>
          </div>
          
          <!-- XML视图 -->
          <div v-if="dataFormat === 'xml'" class="data-viewer">
            <pre class="code-block">{{ formatAsXML(executeResult.data?.data || []) }}</pre>
          </div>
          
          <!-- CSV视图 -->
          <div v-if="dataFormat === 'csv'" class="data-viewer">
            <pre class="code-block">{{ formatAsCSV(executeResult.data?.data || []) }}</pre>
          </div>
        </el-card>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, CaretRight, View, Edit, Delete, Document, List, CopyDocument, Download, InfoFilled, SuccessFilled } from '@element-plus/icons-vue'
import api from '../api'

const router = useRouter()

const loading = ref(false)
const interfaces = ref([])
const databases = ref([])
const detailDialogVisible = ref(false)
const executeDialogVisible = ref(false)
const apiDocDialogVisible = ref(false)
const currentInterface = ref(null)
const requestParameters = ref([])
const executeParams = reactive({})
const executeResult = ref(null)
const executing = ref(false)
const requestSample = ref({})
const responseSample = ref(null)
const apiDoc = ref(null)
const dataFormat = ref('table')

const filters = reactive({
  database_id: null,
  status: null,
  entry_mode: null
})

const pagination = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0
})

onMounted(() => {
  loadDatabases()
  loadInterfaces()
})

const loadDatabases = async () => {
  try {
    const res = await api.get('/database-configs')
    if (res.data.success) {
      databases.value = res.data.data || []
    }
  } catch (error) {
    console.error('加载数据库列表失败:', error)
  }
}

const loadInterfaces = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize
    }
    if (filters.database_id) params.database_id = filters.database_id
    if (filters.status) params.status = filters.status
    if (filters.entry_mode) params.entry_mode = filters.entry_mode
    
    const res = await api.get('/interface-configs', { params })
    if (res.data.success) {
      interfaces.value = res.data.data || []
      // 如果后端返回分页信息
      if (res.data.pagination) {
        pagination.total = res.data.pagination.total || 0
      } else {
        // 如果没有分页信息，使用数据长度
        pagination.total = interfaces.value.length
      }
    }
  } catch (error) {
    ElMessage.error('加载接口列表失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const handleSizeChange = (val) => {
  pagination.pageSize = val
  pagination.currentPage = 1
  loadInterfaces()
}

const handleCurrentChange = (val) => {
  pagination.currentPage = val
  loadInterfaces()
}

const handleCreate = () => {
  router.push('/interface-config')
}

const interfaceFullUrl = ref('')

const handleView = async (row) => {
  try {
    const res = await api.get(`/interface-configs/${row.id}`)
    if (res.data.success) {
      currentInterface.value = res.data.data
      
      // 获取完整URL（从API文档接口）
      try {
        const apiDocRes = await api.get(`/interface-configs/${row.id}/api-doc`)
        if (apiDocRes.data.success && apiDocRes.data.data.full_url) {
          interfaceFullUrl.value = apiDocRes.data.data.full_url
        }
      } catch (e) {
        console.warn('获取完整URL失败，使用默认构建:', e)
        interfaceFullUrl.value = getInterfaceFullUrl(currentInterface.value)
      }
      
      // 加载样例数据
      try {
        const samplesRes = await api.get(`/interface-configs/${row.id}/samples`)
        if (samplesRes.data.success) {
          requestSample.value = samplesRes.data.data.request_sample || {}
          responseSample.value = samplesRes.data.data.response_sample || null
        }
      } catch (e) {
        console.error('加载样例数据失败:', e)
        requestSample.value = {}
        responseSample.value = null
      }
      
      // 尝试获取实际响应数据作为示例
      try {
        const executeRes = await api.get(`/interfaces/${row.id}/execute`, {
          params: { pageNumber: 1, pageSize: 1 }
        })
        if (executeRes.data.success && executeRes.data.data) {
          // 使用实际响应数据更新示例
          responseSample.value = {
            success: executeRes.data.success,
            message: executeRes.data.message,
            data: executeRes.data.data
          }
        }
      } catch (e) {
        // 如果获取实际数据失败，使用默认示例
        console.warn('获取实际响应数据失败，使用默认示例:', e)
      }
      
      detailDialogVisible.value = true
    }
  } catch (error) {
    ElMessage.error('加载接口详情失败: ' + (error.response?.data?.detail || error.message))
  }
}

// 获取接口完整URL（备用方法）
const getInterfaceFullUrl = (interfaceConfig) => {
  if (!interfaceConfig) return ''
  
  // 从API文档获取完整URL，或者构建URL
  try {
    // 尝试从环境变量或配置获取服务器地址
    const apiServerHost = import.meta.env.VITE_API_SERVER_HOST || '121.36.205.70'
    const apiServerPort = import.meta.env.VITE_API_SERVER_PORT || '50052'
    const scheme = interfaceConfig.proxy_schemes || 'http'
    
    // 构建完整URL
    let proxyPath = interfaceConfig.proxy_path || ''
    if (!proxyPath.startsWith('/')) {
      proxyPath = '/' + proxyPath
    }
    if (!proxyPath.startsWith('/api')) {
      proxyPath = '/api' + proxyPath
    }
    
    return `${scheme}://${apiServerHost}:${apiServerPort}${proxyPath}`
  } catch (e) {
    console.error('构建完整URL失败:', e)
    return interfaceConfig.proxy_path || ''
  }
}

const handleViewApiDoc = async (row) => {
  try {
    const res = await api.get(`/interface-configs/${row.id}/api-doc`)
    if (res.data.success) {
      apiDoc.value = res.data.data
      
      // 尝试获取实际响应数据作为示例
      try {
        const executeRes = await api.get(`/interfaces/${row.id}/execute`, {
          params: { pageNumber: 1, pageSize: 1 }
        })
        if (executeRes.data.success && executeRes.data.data) {
          // 使用实际响应数据更新示例
          apiDoc.value.response.sample = {
            success: executeRes.data.success,
            message: executeRes.data.message,
            data: executeRes.data.data
          }
        }
      } catch (e) {
        // 如果获取实际数据失败，使用默认示例
        console.warn('获取实际响应数据失败，使用默认示例:', e)
      }
      
      apiDocDialogVisible.value = true
    }
  } catch (error) {
    ElMessage.error('加载API文档失败: ' + (error.response?.data?.detail || error.message))
  }
}

const generateCurlExample = (doc) => {
  if (!doc) return ''
  
  let curl = `curl -X ${doc.method} "${doc.full_url}"`
  
  if (doc.request.headers) {
    Object.entries(doc.request.headers).forEach(([key, value]) => {
      curl += ` \\\n  -H "${key}: ${value}"`
    })
  }
  
  if (doc.method === 'POST' && Object.keys(doc.request.sample).length > 0) {
    curl += ` \\\n  -d '${JSON.stringify(doc.request.sample)}'`
  } else if (doc.method === 'GET' && Object.keys(doc.request.sample).length > 0) {
    const params = new URLSearchParams(doc.request.sample).toString()
    curl = `curl -X ${doc.method} "${doc.full_url}?${params}"`
  }
  
  return curl
}

const handleEdit = (row) => {
  router.push({ path: '/interface-config', query: { id: row.id } })
}

const handleExecute = async (row) => {
  try {
    const res = await api.get(`/interface-configs/${row.id}`)
    if (res.data.success) {
      currentInterface.value = res.data.data
      
      // 加载请求参数
      if (currentInterface.value.entry_mode === 'expert') {
        // 专家模式：从SQL中解析参数
        try {
          const parseRes = await api.post('/interface-configs/parse-sql', {
            sql: currentInterface.value.sql_statement
          })
          if (parseRes.data.success) {
            requestParameters.value = parseRes.data.data.request_parameters || []
          }
        } catch (e) {
          requestParameters.value = []
        }
      } else {
        // 图形模式：从配置中获取参数
        requestParameters.value = []
        if (currentInterface.value.where_conditions) {
          currentInterface.value.where_conditions.forEach((cond, idx) => {
            if (cond.value_type === 'variable' && cond.variable_name) {
              requestParameters.value.push({
                name: cond.variable_name,
                type: 'string',
                description: cond.description || '',
                constraint: 'required',
                location: 'query'
              })
            }
          })
        }
      }
      
      // 初始化执行参数
      Object.keys(executeParams).forEach(key => delete executeParams[key])
      requestParameters.value.forEach(param => {
        executeParams[param.name] = ''
      })
      if (currentInterface.value.enable_pagination) {
        executeParams.page = 1
        executeParams.page_size = 10
      }
      
      executeResult.value = null
      dataFormat.value = 'table' // 重置数据格式为表格
      executeDialogVisible.value = true
    }
  } catch (error) {
    ElMessage.error('加载接口详情失败: ' + (error.response?.data?.detail || error.message))
  }
}

const doExecute = async () => {
  if (!currentInterface.value) return
  
  executing.value = true
  try {
    const params = { ...executeParams }
    // 移除空值
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null || params[key] === undefined) {
        delete params[key]
      }
    })
    
    let res
    if (currentInterface.value.http_method === 'POST') {
      res = await api.post(`/interfaces/${currentInterface.value.id}/execute`, params)
    } else {
      const queryString = new URLSearchParams(params).toString()
      res = await api.get(`/interfaces/${currentInterface.value.id}/execute?${queryString}`)
    }
    
    executeResult.value = res.data
    if (res.data.success) {
      ElMessage.success('执行成功')
    } else {
      ElMessage.error(res.data.message || '执行失败')
    }
  } catch (error) {
    executeResult.value = {
      success: false,
      message: error.response?.data?.detail || error.message || '执行失败'
    }
    ElMessage.error('执行失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    executing.value = false
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除接口 "${row.interface_name}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const res = await api.delete(`/interface-configs/${row.id}`)
    if (res.data.success) {
      ElMessage.success('删除成功')
      loadInterfaces()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

const getMethodType = (method) => {
  const types = {
    'GET': 'success',
    'POST': 'primary',
    'PUT': 'warning',
    'DELETE': 'danger'
  }
  return types[method] || 'info'
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

const formatCondition = (cond) => {
  if (!cond.field) return ''
  const operators = {
    'equal': '=',
    'not_equal': '!=',
    'greater': '>',
    'greater_equal': '>=',
    'less': '<',
    'less_equal': '<=',
    'like': 'LIKE',
    'not_like': 'NOT LIKE',
    'in': 'IN',
    'not_in': 'NOT IN',
    'is_null': 'IS NULL',
    'is_not_null': 'IS NOT NULL'
  }
  const op = operators[cond.operator] || '='
  const value = cond.value_type === 'constant' ? cond.value : `:${cond.variable_name}`
  return `${cond.field} ${op} ${value}`
}

const getFullUrl = (interfaceConfig) => {
  const baseUrl = window.location.origin
  return `${baseUrl}/api/v1/interfaces/${interfaceConfig.id}/execute`
}

const getRequestExample = (interfaceConfig) => {
  if (interfaceConfig.http_method === 'POST') {
    return `POST ${getFullUrl(interfaceConfig)}\nContent-Type: application/json\n\n${JSON.stringify({ param1: 'value1' }, null, 2)}`
  } else {
    return `GET ${getFullUrl(interfaceConfig)}?param1=value1&param2=value2`
  }
}

const getTableColumns = (data) => {
  if (!data || data.length === 0) return []
  const columns = new Set()
  data.forEach(row => {
    Object.keys(row).forEach(key => columns.add(key))
  })
  return Array.from(columns)
}

// 数据格式转换函数
const formatAsJSON = (data) => {
  return JSON.stringify(data, null, 2)
}

const formatAsXML = (data) => {
  if (!data || data.length === 0) return '<?xml version="1.0" encoding="UTF-8"?>\n<data></data>'
  
  let xml = '<?xml version="1.0" encoding="UTF-8"?>\n<data>\n'
  data.forEach((item, index) => {
    xml += `  <item index="${index}">\n`
    Object.keys(item).forEach(key => {
      const value = item[key] === null || item[key] === undefined ? '' : String(item[key])
      xml += `    <${key}><![CDATA[${value}]]></${key}>\n`
    })
    xml += '  </item>\n'
  })
  xml += '</data>'
  return xml
}

const formatAsCSV = (data) => {
  if (!data || data.length === 0) return ''
  
  const columns = getTableColumns(data)
  let csv = columns.join(',') + '\n'
  
  data.forEach(row => {
    const values = columns.map(col => {
      const value = row[col]
      if (value === null || value === undefined) return ''
      // 如果值包含逗号、引号或换行符，需要用引号包裹并转义
      const str = String(value)
      if (str.includes(',') || str.includes('"') || str.includes('\n')) {
        return `"${str.replace(/"/g, '""')}"`
      }
      return str
    })
    csv += values.join(',') + '\n'
  })
  
  return csv
}

// 复制到剪贴板通用函数
const copyToClipboard = async (text) => {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
      ElMessage.success('已复制到剪贴板')
    } else {
      // 降级方案：使用传统方法
      const textArea = document.createElement('textarea')
      textArea.value = text
      textArea.style.position = 'fixed'
      textArea.style.left = '-999999px'
      document.body.appendChild(textArea)
      textArea.select()
      try {
        document.execCommand('copy')
        ElMessage.success('已复制到剪贴板')
      } catch (err) {
        ElMessage.error('复制失败，请手动复制')
      }
      document.body.removeChild(textArea)
    }
  } catch (error) {
    ElMessage.error('复制失败: ' + error.message)
  }
}

// 复制请求示例（根据当前tab复制不同的内容）
const copyRequestExample = (apiDoc) => {
  // 这里可以根据当前选中的tab来决定复制什么
  // 暂时复制JSON格式的请求示例
  const text = JSON.stringify(apiDoc.request.sample, null, 2)
  copyToClipboard(text)
}

// 复制格式化数据
const copyFormattedData = async () => {
  if (!executeResult.value?.data) return
  
  let text = ''
  switch (dataFormat.value) {
    case 'json':
      // JSON格式显示完整响应数据（包括分页信息）
      text = formatAsJSON(executeResult.value.data)
      break
    case 'xml':
      text = formatAsXML(executeResult.value.data.data || [])
      break
    case 'csv':
      text = formatAsCSV(executeResult.value.data.data || [])
      break
    default:
      // 默认显示完整响应数据
      text = formatAsJSON(executeResult.value.data)
  }
  
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('数据已复制到剪贴板')
  } catch (error) {
    // 降级方案
    const textarea = document.createElement('textarea')
    textarea.value = text
    document.body.appendChild(textarea)
    textarea.select()
    try {
      document.execCommand('copy')
      ElMessage.success('数据已复制到剪贴板')
    } catch (e) {
      ElMessage.error('复制失败，请手动复制')
    }
    document.body.removeChild(textarea)
  }
}

// 下载格式化数据
const downloadFormattedData = () => {
  if (!executeResult.value?.data?.data) return
  
  let text = ''
  let filename = `${currentInterface.value?.interface_name || 'data'}.`
  let mimeType = ''
  
  switch (dataFormat.value) {
    case 'json':
      text = formatAsJSON(executeResult.value.data.data)
      filename += 'json'
      mimeType = 'application/json'
      break
    case 'xml':
      text = formatAsXML(executeResult.value.data.data)
      filename += 'xml'
      mimeType = 'application/xml'
      break
    case 'csv':
      text = formatAsCSV(executeResult.value.data.data)
      filename += 'csv'
      mimeType = 'text/csv'
      break
    default:
      text = formatAsJSON(executeResult.value.data.data)
      filename += 'json'
      mimeType = 'application/json'
  }
  
  const blob = new Blob([text], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  ElMessage.success('数据下载成功')
}

// 复制接口配置
const handleCopyInterface = async (row) => {
  try {
    const res = await api.get(`/interface-configs/${row.id}`)
    if (res.data.success) {
      const configData = { ...res.data.data }
      // 移除id和创建时间等字段，准备创建新接口
      delete configData.id
      delete configData.created_at
      delete configData.updated_at
      configData.interface_name = `${configData.interface_name}_副本`
      configData.status = 'draft'
      
      // 创建新接口
      const createRes = await api.post('/interface-configs', configData)
      if (createRes.data.success) {
        ElMessage.success('接口复制成功')
        loadInterfaces()
      }
    }
  } catch (error) {
    ElMessage.error('复制接口失败: ' + (error.response?.data?.detail || error.message))
  }
}
</script>

<style scoped>
.interface-list {
  padding: 24px;
  min-height: calc(100vh - 120px);
}

.main-card {
  border-radius: 12px;
  overflow: hidden;
}

.main-card :deep(.el-card__header) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-bottom: none;
  padding: 20px 24px;
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
  margin-left: 8px;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.action-btn {
  border-radius: 8px;
  padding: 10px 20px;
  font-weight: 500;
  transition: all 0.3s;
}

.action-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.filter-card {
  margin: 20px 0;
  border-radius: 8px;
  background: #fafbfc;
  border: 1px solid #e4e7ed;
}

.filter-form {
  padding: 16px 0;
  margin: 0;
}

.filter-item {
  margin-bottom: 0;
}

.filter-item :deep(.el-form-item__label) {
  font-weight: 500;
  color: #606266;
}

.filter-select {
  width: 200px;
  border-radius: 6px;
}

.interface-table {
  margin-top: 20px;
  border-radius: 8px;
  overflow: hidden;
}

.interface-table :deep(.el-table__row) {
  transition: all 0.3s;
}

.interface-table :deep(.el-table__row:hover) {
  background-color: #f5f7fa;
  transform: scale(1.01);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.action-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.action-buttons .el-button {
  border-radius: 6px;
  padding: 8px 12px;
  transition: all 0.3s;
}

.action-buttons .el-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.12);
}

.btn-view {
  background: #409eff;
  border: none;
  color: white;
}

.btn-view:hover {
  background: #66b1ff;
}

.btn-execute {
  background: #67c23a;
  border: none;
  color: white;
}

.btn-execute:hover {
  background: #85ce61;
}

.btn-edit {
  background: #e6a23c;
  border: none;
  color: white;
}

.btn-edit:hover {
  background: #ebb563;
}

.btn-doc {
  background: #909399;
  border: none;
  color: white;
}

.btn-doc:hover {
  background: #a6a9ad;
}

.btn-copy {
  background: #606266;
  border: none;
  color: white;
}

.btn-copy:hover {
  background: #72767a;
}

.btn-delete {
  background: #f56c6c;
  border: none;
  color: white;
}

.btn-delete:hover {
  background: #f78989;
}

/* 对话框样式 */
.detail-dialog :deep(.el-dialog__header) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px 24px;
  border-radius: 8px 8px 0 0;
}

.detail-dialog :deep(.el-dialog__title) {
  color: white;
  font-weight: 600;
  font-size: 18px;
}

.detail-dialog :deep(.el-dialog__headerbtn .el-dialog__close) {
  color: white;
  font-size: 20px;
}

.detail-dialog :deep(.el-dialog__body) {
  padding: 24px;
  background: #fafbfc;
}

.api-doc-dialog :deep(.el-dialog__header) {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  color: white;
  padding: 20px 24px;
  border-radius: 8px 8px 0 0;
}

.api-doc-dialog :deep(.el-dialog__title) {
  color: white;
  font-weight: 600;
  font-size: 18px;
}

.api-doc-dialog :deep(.el-dialog__headerbtn .el-dialog__close) {
  color: white;
  font-size: 20px;
}

.api-doc-dialog :deep(.el-dialog__body) {
  padding: 24px;
  background: #fafbfc;
}

.execute-dialog :deep(.el-dialog__header) {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
  padding: 20px 24px;
  border-radius: 8px 8px 0 0;
}

.execute-dialog :deep(.el-dialog__title) {
  color: white;
  font-weight: 600;
  font-size: 18px;
}

.execute-dialog :deep(.el-dialog__headerbtn .el-dialog__close) {
  color: white;
  font-size: 20px;
}

.execute-dialog :deep(.el-dialog__body) {
  padding: 24px;
  background: #fafbfc;
}

/* 卡片样式 */
.detail-dialog :deep(.el-card),
.api-doc-dialog :deep(.el-card),
.execute-dialog :deep(.el-card) {
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  margin-bottom: 16px;
  transition: all 0.3s;
}

.detail-dialog :deep(.el-card:hover),
.api-doc-dialog :deep(.el-card:hover),
.execute-dialog :deep(.el-card:hover) {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

/* 代码块样式 */
pre {
  margin: 0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  background: #282c34;
  color: #abb2bf;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  border: 1px solid #3e4451;
}

/* 标签页样式 */
:deep(.el-tabs__item) {
  font-weight: 500;
  font-size: 14px;
}

:deep(.el-tabs__item.is-active) {
  color: #667eea;
  font-weight: 600;
}

:deep(.el-tabs__active-bar) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* 表格样式优化 */
:deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
}

:deep(.el-table th) {
  background: #f5f7fa;
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td) {
  background: #fafbfc;
}

/* 描述列表样式 */
:deep(.el-descriptions__label) {
  font-weight: 600;
  color: #606266;
}

:deep(.el-descriptions__content) {
  color: #303133;
}

/* 分割线样式 */
:deep(.el-divider__text) {
  background: #fafbfc;
  font-weight: 600;
  color: #606266;
}

/* 空状态样式 */
:deep(.el-empty__description) {
  color: #909399;
}

/* 接口元数据卡片 */
.metadata-card {
  margin-bottom: 24px;
  border-radius: 8px;
}

.metadata-header {
  display: flex;
  align-items: center;
  font-weight: 600;
  color: #303133;
}

.metadata-card :deep(.el-descriptions__label) {
  font-weight: 600;
  color: #606266;
  width: 120px;
}

.metadata-card :deep(.el-descriptions__content) {
  color: #303133;
}

/* 数据格式转换工具栏 */
.data-format-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
  flex-wrap: wrap;
}

.format-label {
  font-weight: 600;
  color: #606266;
  font-size: 14px;
}

.copy-data-btn,
.download-data-btn {
  margin-left: auto;
}

/* 数据查看器 */
.data-viewer {
  max-height: 500px;
  overflow: auto;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}

.code-block {
  margin: 0;
  padding: 16px;
  background: #282c34;
  color: #abb2bf;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  border-radius: 8px;
  overflow-x: auto;
}

.pagination-container {
  margin-top: 20px;
  text-align: right;
  padding: 10px 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .interface-list {
    padding: 16px;
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  .action-buttons .el-button {
    width: 100%;
  }
  
  .filter-form {
    flex-direction: column;
  }
  
  .filter-select {
    width: 100%;
  }
  
  .data-format-toolbar {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .copy-data-btn,
  .download-data-btn {
    margin-left: 0;
    width: 100%;
  }
}

/* API文档弹框样式美化 */
.api-doc-dialog {
  .api-doc-content {
    max-height: 80vh;
    overflow-y: auto;
  }
  
  .api-info-card {
    margin-bottom: 20px;
    border: 1px solid #e4e7ed;
    border-radius: 8px;
  }
  
  .example-card {
    margin-bottom: 20px;
    border: 1px solid #e4e7ed;
    border-radius: 8px;
  }
  
  .code-block-light {
    margin: 0;
    padding: 16px;
    background: #f5f7fa;
    color: #303133;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.6;
    border-radius: 4px;
    overflow-x: auto;
    border: 1px solid #e4e7ed;
  }
}

/* 执行测试弹框样式美化 */
.execute-dialog {
  .result-card {
    margin-top: 20px;
    border: 1px solid #e4e7ed;
    border-radius: 8px;
  }
  
  .pagination-info {
    margin: 20px 0;
  }
  
  .metadata-card {
    margin-bottom: 20px;
    border: 1px solid #e4e7ed;
    border-radius: 8px;
  }
  
  .metadata-header {
    display: flex;
    align-items: center;
    font-weight: 600;
    color: #409eff;
  }
}
</style>

