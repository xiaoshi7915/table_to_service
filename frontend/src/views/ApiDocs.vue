<template>
  <div class="api-docs">
    <el-card class="main-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon class="title-icon"><Document /></el-icon>
            <span class="title-text">API接口文档</span>
            <el-tag v-if="interfaceList.length > 0" type="info" size="small" class="count-tag">
              {{ interfaceList.length }}
            </el-tag>
          </div>
          <div class="header-actions">
            <el-button type="primary" @click="handleGenerateAll" :loading="generating">
              <el-icon><DocumentCopy /></el-icon>
              生成全部文档
            </el-button>
            <el-button type="success" @click="exportMarkdown" style="margin-left: 10px;">
              <el-icon><Download /></el-icon>
              导出Markdown
            </el-button>
            <el-button type="success" @click="exportHtml" style="margin-left: 10px;">
              <el-icon><Download /></el-icon>
              导出HTML
            </el-button>
            <el-button type="success" @click="exportOpenApi" class="action-btn">
              <el-icon><Download /></el-icon>
              导出OpenAPI
            </el-button>
          </div>
        </div>
      </template>
      
      <!-- 接口列表 -->
      <el-table 
        :data="interfaceList" 
        class="interface-table"
        border 
        stripe 
        :header-cell-style="{ background: '#f5f7fa', color: '#606266', fontWeight: '600' }"
      >
        <el-table-column prop="interface_name" label="接口名称" width="200" />
        <el-table-column prop="database_name" label="数据库" width="150" />
        <el-table-column prop="http_method" label="请求方式" width="100">
          <template #default="{ row }">
            <el-tag :type="getMethodType(row.http_method)">
              {{ row.http_method }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="proxy_path" label="接口路径" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : row.status === 'draft' ? 'info' : 'danger'">
              {{ row.status === 'active' ? '激活' : row.status === 'draft' ? '草稿' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="entry_mode" label="录入模式" width="100">
          <template #default="{ row }">
            <el-tag :type="row.entry_mode === 'expert' ? 'warning' : 'success'">
              {{ row.entry_mode === 'expert' ? '专家模式' : '图形模式' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="修改时间" width="180">
          <template #default="{ row }">
            {{ row.updated_at ? new Date(row.updated_at).toLocaleString('zh-CN') : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="viewDoc(row.id)">
              <el-icon><View /></el-icon>
              查看文档
            </el-button>
            <el-button size="small" type="success" @click="exportSingleDoc(row.id, 'markdown')">
              <el-icon><Download /></el-icon>
              导出
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination-container" style="margin-top: 20px; text-align: right;">
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
      
      <!-- 文档详情对话框 -->
      <el-dialog
        v-model="docDialogVisible"
        :title="currentDoc?.interface_name || '接口文档'"
        width="80%"
        :close-on-click-modal="false"
      >
        <div v-if="currentDoc" class="doc-detail">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="接口名称">{{ currentDoc.interface_name }}</el-descriptions-item>
            <el-descriptions-item label="数据库">{{ currentDoc.database_name }}</el-descriptions-item>
            <el-descriptions-item label="请求方式">
              <el-tag :type="getMethodType(currentDoc.http_method)">{{ currentDoc.http_method }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="接口路径">
              <code>{{ currentDoc.proxy_path }}</code>
            </el-descriptions-item>
            <el-descriptions-item label="完整URL" :span="2">
              <code style="color: #409eff; word-break: break-all;">{{ currentDoc.full_url }}</code>
              <el-button size="small" type="primary" @click="copyToClipboard(currentDoc.full_url)" style="margin-left: 10px;">
                <el-icon><DocumentCopy /></el-icon>
                复制
              </el-button>
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="currentDoc.status === 'active' ? 'success' : 'info'">
                {{ currentDoc.status === 'active' ? '激活' : '草稿' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="录入模式">
              <el-tag :type="currentDoc.entry_mode === 'expert' ? 'warning' : 'success'">
                {{ currentDoc.entry_mode === 'expert' ? '专家模式' : '图形模式' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="分页" v-if="currentDoc.enable_pagination">
              启用 (最大查询数量: {{ currentDoc.max_query_count }})
            </el-descriptions-item>
            <el-descriptions-item label="认证方式" v-if="currentDoc.proxy_auth && currentDoc.proxy_auth !== 'no_auth'">
              {{ currentDoc.proxy_auth === 'bearer' ? 'Bearer Token' : currentDoc.proxy_auth === 'basic' ? 'Basic Auth' : currentDoc.proxy_auth }}
            </el-descriptions-item>
            <el-descriptions-item label="接口描述" :span="2">
              {{ currentDoc.interface_description || '无描述' }}
            </el-descriptions-item>
            <el-descriptions-item label="使用说明" :span="2" v-if="currentDoc.usage_instructions">
              {{ currentDoc.usage_instructions }}
            </el-descriptions-item>
          </el-descriptions>
          
          <el-divider>
            <span>cURL示例</span>
            <el-button size="small" type="primary" @click="copyToClipboard(currentDoc.curl_example || '')" style="margin-left: 10px;">
              <el-icon><DocumentCopy /></el-icon>
              复制
            </el-button>
          </el-divider>
          <pre class="code-block">{{ currentDoc.curl_example || '暂无' }}</pre>
          
          <el-divider>请求参数</el-divider>
          <el-table :data="currentDoc.request_parameters || []" border style="margin-top: 20px;">
            <el-table-column prop="name" label="参数名" />
            <el-table-column prop="type" label="类型" />
            <el-table-column prop="constraint" label="约束">
              <template #default="{ row }">
                <el-tag :type="row.constraint === 'required' ? 'danger' : 'info'">
                  {{ row.constraint === 'required' ? '必填' : '可选' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="location" label="位置" />
            <el-table-column prop="description" label="描述" />
          </el-table>
          
          <el-divider>
            <span>请求示例</span>
            <el-button size="small" type="primary" @click="copyToClipboard(JSON.stringify(currentDoc.request_sample || {}, null, 2))" style="margin-left: 10px;">
              <el-icon><DocumentCopy /></el-icon>
              复制
            </el-button>
          </el-divider>
          <pre class="code-block">{{ JSON.stringify(currentDoc.request_sample || {}, null, 2) }}</pre>
          
          <el-divider>响应参数</el-divider>
          <el-table :data="currentDoc.response_parameters || []" border style="margin-top: 20px;">
            <el-table-column prop="name" label="参数名" />
            <el-table-column prop="type" label="类型" />
            <el-table-column prop="constraint" label="约束">
              <template #default="{ row }">
                <el-tag :type="row.constraint === 'required' ? 'danger' : 'info'">
                  {{ row.constraint === 'required' ? '必填' : '可选' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" />
          </el-table>
          
          <el-divider>
            <span>响应示例</span>
            <el-button size="small" type="primary" @click="copyToClipboard(JSON.stringify(currentDoc.response_sample || {}, null, 2))" style="margin-left: 10px;">
              <el-icon><DocumentCopy /></el-icon>
              复制
            </el-button>
          </el-divider>
          <pre class="code-block">{{ JSON.stringify(currentDoc.response_sample || {}, null, 2) }}</pre>
        </div>
        
        <template #footer>
          <el-button @click="docDialogVisible = false">关闭</el-button>
          <el-button type="primary" @click="exportSingleDoc(currentDoc?.id, 'markdown')">
            导出Markdown
          </el-button>
          <el-button type="success" @click="exportSingleDoc(currentDoc?.id, 'html')">
            导出HTML
          </el-button>
          <el-button type="warning" @click="exportSingleDoc(currentDoc?.id, 'openapi')">
            导出OpenAPI
          </el-button>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { DocumentCopy, Download, View, Document } from '@element-plus/icons-vue'
import api from '@/api'

const interfaceList = ref([])
const generating = ref(false)
const docDialogVisible = ref(false)
const currentDoc = ref(null)

const pagination = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0
})

const loadInterfaceList = async () => {
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize
    }
    const res = await api.get('/api-docs/interfaces', { params })
    if (res.data.success) {
      interfaceList.value = res.data.data || []
      // 如果后端返回分页信息
      if (res.data.pagination) {
        pagination.total = res.data.pagination.total || 0
      } else {
        // 如果没有分页信息，使用数据长度
        pagination.total = interfaceList.value.length
      }
    }
  } catch (error) {
    ElMessage.error('加载接口列表失败: ' + (error.response?.data?.detail || error.message))
  }
}

const handleSizeChange = (val) => {
  pagination.pageSize = val
  pagination.currentPage = 1
  loadInterfaceList()
}

const handleCurrentChange = (val) => {
  pagination.currentPage = val
  loadInterfaceList()
}

const handleGenerateAll = async () => {
  generating.value = true
  try {
    const res = await api.post('/api-docs/generate-all')
    if (res.data.success) {
      ElMessage.success(res.data.message || '文档生成成功')
      loadInterfaceList()
    }
  } catch (error) {
    ElMessage.error('文档生成失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    generating.value = false
  }
}

const viewDoc = async (interfaceId) => {
  try {
    const res = await api.get(`/api-docs/interfaces/${interfaceId}`)
    if (res.data.success) {
      currentDoc.value = res.data.data
      docDialogVisible.value = true
    }
  } catch (error) {
    ElMessage.error('加载文档失败: ' + (error.response?.data?.detail || error.message))
  }
}

const exportMarkdown = async () => {
  try {
    const res = await api.get('/api-docs/export/markdown', {
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `api-docs-${new Date().toISOString().split('T')[0]}.md`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败: ' + (error.response?.data?.detail || error.message))
  }
}

const exportHtml = async () => {
  try {
    const res = await api.get('/api-docs/export/html', {
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `api-docs-${new Date().toISOString().split('T')[0]}.html`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败: ' + (error.response?.data?.detail || error.message))
  }
}

const exportOpenApi = async () => {
  try {
    const res = await api.get('/api-docs/export/openapi', {
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `openapi-${new Date().toISOString().split('T')[0]}.json`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败: ' + (error.response?.data?.detail || error.message))
  }
}

const exportSingleDoc = async (interfaceId, format) => {
  if (!interfaceId) return
  
  try {
    const url = `/api-docs/export/${format}?interface_id=${interfaceId}`
    const res = await api.get(url, {
      responseType: 'blob'
    })
    const url_obj = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url_obj
    const ext = format === 'openapi' ? 'json' : format
    link.setAttribute('download', `api-doc-${interfaceId}-${new Date().toISOString().split('T')[0]}.${ext}`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败: ' + (error.response?.data?.detail || error.message))
  }
}

const getMethodType = (method) => {
  const types = {
    GET: 'success',
    POST: 'primary',
    PUT: 'warning',
    DELETE: 'danger',
    PATCH: 'info'
  }
  return types[method] || 'info'
}

// 复制到剪贴板功能
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

onMounted(() => {
  loadInterfaceList()
})
</script>

<style scoped>
.api-docs {
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
  margin-left: 10px;
}

.interface-table {
  width: 100%;
}

.interface-table :deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}

.code-block {
  background: #282c34;
  color: #abb2bf;
  padding: 15px;
  border-radius: 4px;
  overflow-x: auto;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.5;
}

.doc-detail {
  max-height: 70vh;
  overflow-y: auto;
}

:deep(.el-descriptions__label) {
  font-weight: 600;
}
</style>
