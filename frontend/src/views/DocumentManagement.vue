<template>
  <div class="document-management">
    <el-card class="main-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon class="title-icon"><Document /></el-icon>
            <span class="title-text">文档管理</span>
            <el-tag v-if="documents.length > 0" type="info" size="small" class="count-tag">
              {{ pagination.total }}
            </el-tag>
          </div>
          <div class="header-actions">
            <el-upload
              :action="uploadUrl"
              :headers="uploadHeaders"
              :on-success="handleUploadSuccess"
              :on-error="handleUploadError"
              :before-upload="beforeUpload"
              :show-file-list="false"
              :data="uploadData"
              multiple
            >
              <el-button type="primary" class="action-btn">
                <el-icon><Upload /></el-icon>
                上传文档
              </el-button>
            </el-upload>
            <el-button @click="loadDocuments" :loading="loading" class="action-btn">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>
      
      <!-- 筛选条件 -->
      <el-card class="filter-card" shadow="never">
        <el-form :inline="true" class="filter-form">
          <el-form-item label="关键词" class="filter-item">
            <el-input
              v-model="searchForm.keyword"
              placeholder="搜索文件名或标题"
              clearable
              class="filter-input"
              @clear="handleSearch"
              @keyup.enter="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          
          <el-form-item label="文件类型" class="filter-item">
            <el-select
              v-model="searchForm.file_type"
              placeholder="全部"
              clearable
              class="filter-select"
              @change="handleSearch"
            >
              <el-option label="PDF" value="pdf" />
              <el-option label="Word" value="doc" />
              <el-option label="Markdown" value="md" />
              <el-option label="HTML" value="html" />
              <el-option label="文本" value="txt" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="状态" class="filter-item">
            <el-select
              v-model="searchForm.status"
              placeholder="全部"
              clearable
              class="filter-select"
              @change="handleSearch"
            >
              <el-option label="待处理" value="pending" />
              <el-option label="处理中" value="processing" />
              <el-option label="已完成" value="completed" />
              <el-option label="失败" value="failed" />
            </el-select>
          </el-form-item>
        </el-form>
      </el-card>
      
      <!-- 文档列表 -->
      <el-table 
        :data="documents" 
        class="config-table"
        v-loading="loading"
        stripe
        :header-cell-style="{ background: '#f5f7fa', color: '#606266', fontWeight: '600', textAlign: 'center' }"
      >
        <el-table-column prop="filename" label="文件名" min-width="200" align="center" show-overflow-tooltip />
        <el-table-column prop="file_type" label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.file_type" size="small">{{ row.file_type.toUpperCase() }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="file_size" label="大小" width="120" align="center">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="200" align="center" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" align="center">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons" style="display: flex; gap: 4px; justify-content: center; flex-wrap: nowrap;">
              <el-button size="small" @click="handleView(row)">
                <el-icon><View /></el-icon>
                查看
              </el-button>
              <el-button size="small" type="danger" @click="handleDelete(row)">
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div v-if="documents.length > 0 || pagination.total > 0" style="margin-top: 20px; display: flex; justify-content: flex-end;">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
    
    <!-- 文档详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="文档详情"
      width="800px"
    >
      <div v-if="selectedDocument">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="文件名">{{ selectedDocument.filename }}</el-descriptions-item>
          <el-descriptions-item label="文件类型">{{ selectedDocument.file_type }}</el-descriptions-item>
          <el-descriptions-item label="文件大小">{{ formatFileSize(selectedDocument.file_size) }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(selectedDocument.status)">
              {{ getStatusLabel(selectedDocument.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="标题" :span="2">{{ selectedDocument.title || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间" :span="2">{{ formatDateTime(selectedDocument.created_at) }}</el-descriptions-item>
        </el-descriptions>
        
        <div v-if="selectedDocument.chunks_count > 0" style="margin-top: 20px;">
          <h4>分块信息</h4>
          <el-tag>共 {{ selectedDocument.chunks_count }} 个分块</el-tag>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Upload, Refresh, Search, View, Delete } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import request from '@/utils/request'

const authStore = useAuthStore()
const loading = ref(false)
const documents = ref([])
const selectedDocument = ref(null)
const detailDialogVisible = ref(false)

const searchForm = reactive({
  keyword: '',
  file_type: '',
  status: ''
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

// 使用相对路径，通过 vite 代理转发到后端
const uploadUrl = '/api/v1/documents/upload'
const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${authStore.token}`
}))
const uploadData = computed(() => ({
  // 可以添加额外的上传参数
}))

// 加载文档列表
const loadDocuments = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size
    }
    
    if (searchForm.keyword) {
      params.keyword = searchForm.keyword
    }
    if (searchForm.file_type) {
      params.file_type = searchForm.file_type
    }
    if (searchForm.status) {
      params.status = searchForm.status
    }
    
    const response = await request.get('/documents', { params })
    console.log('文档列表响应:', response)
    
    // 处理响应数据（request.js 已经转换了格式）
    // request.js 会将 ResponseModel {success: true, data: {...}} 转换为 {code: 200, data: {...}}
    if (response && response.data) {
      // 情况1：response.data 已经是转换后的格式（有 code 字段）
      if (response.data.code === 200 && response.data.data) {
        documents.value = response.data.data.documents || []
        pagination.total = response.data.data.total || 0
      } 
      // 情况2：response.data 是原始 ResponseModel 格式（有 success 字段）
      else if (response.data.success && response.data.data) {
        documents.value = response.data.data.documents || []
        pagination.total = response.data.data.total || 0
      }
      // 情况3：response.data 直接包含 documents（可能是嵌套结构）
      else if (response.data.documents) {
        documents.value = response.data.documents || []
        pagination.total = response.data.total || 0
      }
      // 情况4：response 本身就是 data（双重嵌套）
      else if (response.documents) {
        documents.value = response.documents || []
        pagination.total = response.total || 0
      }
      else {
        console.warn('文档列表响应格式异常:', JSON.stringify(response, null, 2))
        documents.value = []
        pagination.total = 0
      }
    } else {
      console.warn('文档列表响应为空:', response)
      documents.value = []
      pagination.total = 0
    }
  } catch (error) {
    console.error('加载文档列表失败:', error)
    ElMessage.error('加载文档列表失败')
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  loadDocuments()
}

// 上传前检查
const beforeUpload = (file) => {
  const allowedTypes = ['.pdf', '.doc', '.docx', '.md', '.html', '.htm', '.txt']
  const fileExt = '.' + file.name.split('.').pop().toLowerCase()
  
  if (!allowedTypes.includes(fileExt)) {
    ElMessage.error('不支持的文件类型')
    return false
  }
  
  const maxSize = 100 * 1024 * 1024 // 100MB
  if (file.size > maxSize) {
    ElMessage.error('文件大小不能超过 100MB')
    return false
  }
  
  return true
}

// 上传成功
const handleUploadSuccess = (response) => {
  console.log('上传响应:', response)
  // Element Plus 的 upload 组件返回的 response 可能是 response.data
  const result = response?.data || response
  if (result?.success || result?.code === 200) {
    ElMessage.success(result?.message || '文档上传成功，正在处理中')
    loadDocuments()
  } else {
    ElMessage.error(result?.message || result?.detail || '上传失败')
  }
}

// 上传失败
const handleUploadError = (error, file, fileList) => {
  console.error('上传失败:', error, file, fileList)
  const errorMsg = error?.response?.data?.detail || 
                   error?.response?.data?.message || 
                   error?.message || 
                   '文档上传失败'
  ElMessage.error(errorMsg)
}

// 查看详情
const handleView = async (row) => {
  try {
    const response = await request.get(`/documents/${row.id}`)
    if (response.data.code === 200) {
      selectedDocument.value = response.data.data
      detailDialogVisible.value = true
    }
  } catch (error) {
    console.error('获取文档详情失败:', error)
    ElMessage.error('获取文档详情失败')
  }
}

// 删除文档
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该文档吗？', '提示', {
      type: 'warning'
    })
    
    const response = await request.delete(`/documents/${row.id}`)
    if (response.data.code === 200) {
      ElMessage.success('删除成功')
      loadDocuments()
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除文档失败:', error)
      ElMessage.error('删除文档失败')
    }
  }
}

// 分页
const handleSizeChange = () => {
  loadDocuments()
}

const handleCurrentChange = () => {
  loadDocuments()
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

// 格式化日期时间
const formatDateTime = (dateTime) => {
  if (!dateTime) return '-'
  return new Date(dateTime).toLocaleString('zh-CN')
}

// 获取状态类型
const getStatusType = (status) => {
  const statusMap = {
    pending: 'info',
    processing: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return statusMap[status] || 'info'
}

// 获取状态标签
const getStatusLabel = (status) => {
  const labelMap = {
    pending: '待处理',
    processing: '处理中',
    completed: '已完成',
    failed: '失败'
  }
  return labelMap[status] || status
}

onMounted(() => {
  loadDocuments()
})
</script>

<style scoped>
.document-management {
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 60px);
}

.main-card {
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.main-card :deep(.el-card__header) {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
  padding: 20px;
  border-radius: 8px 8px 0 0;
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
  margin-left: 10px;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.action-btn {
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
}

.filter-card {
  margin-bottom: 20px;
  border-radius: 6px;
  background: #fff;
}

.filter-card :deep(.el-card__body) {
  padding: 16px 20px;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
}

.filter-item {
  margin-bottom: 0;
}

.filter-item :deep(.el-form-item__label) {
  font-weight: 500;
  color: #606266;
}

.filter-input {
  width: 240px;
}

.filter-input :deep(.el-input__inner) {
  border-radius: 4px;
}

.filter-select {
  width: 160px;
}

.filter-select :deep(.el-input__inner) {
  border-radius: 4px;
}

.config-table {
  margin-top: 20px;
}

.config-table :deep(.el-table__header) {
  background: #fafafa;
}

.config-table :deep(.el-table__row:hover) {
  background: #f0f9ff;
}

.action-buttons {
  display: flex;
  gap: 4px;
  justify-content: center;
  flex-wrap: nowrap;
}

.action-buttons .el-button {
  margin: 0;
}

/* 空状态样式 */
:deep(.el-empty) {
  padding: 60px 0;
}

/* 对话框样式优化 */
:deep(.el-dialog__header) {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
  padding: 20px;
  margin: 0;
  border-radius: 8px 8px 0 0;
}

:deep(.el-dialog__title) {
  color: white;
  font-weight: 600;
}

:deep(.el-dialog__headerbtn .el-dialog__close) {
  color: white;
}

:deep(.el-dialog__headerbtn:hover .el-dialog__close) {
  color: #f0f0f0;
}

/* 描述列表样式 */
:deep(.el-descriptions__label) {
  font-weight: 500;
  color: #606266;
}

:deep(.el-descriptions__content) {
  color: #303133;
}

/* 文件类型标签样式 */
:deep(.el-tag) {
  border-radius: 4px;
  font-weight: 500;
}

/* 状态标签样式 */
:deep(.el-tag--success) {
  background: #f0f9ff;
  border-color: #67c23a;
  color: #67c23a;
}

:deep(.el-tag--warning) {
  background: #fef0e6;
  border-color: #e6a23c;
  color: #e6a23c;
}

:deep(.el-tag--danger) {
  background: #fef0f0;
  border-color: #f56c6c;
  color: #f56c6c;
}

:deep(.el-tag--info) {
  background: #f4f4f5;
  border-color: #909399;
  color: #909399;
}
</style>

