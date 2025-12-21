<template>
  <div class="prompt-config">
    <el-card class="main-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon class="title-icon"><EditPen /></el-icon>
            <span class="title-text">自定义提示词</span>
            <el-tag v-if="prompts.length > 0" type="info" size="small" class="count-tag">
              {{ pagination.total }}
            </el-tag>
          </div>
          <div class="header-actions">
            <el-button type="primary" @click="handleAdd" class="action-btn">
              <el-icon><Plus /></el-icon>
              添加提示词
            </el-button>
            <el-button @click="handleBatchImport" class="action-btn">
              <el-icon><Upload /></el-icon>
              批量导入
            </el-button>
            <el-button @click="handleDownloadTemplate" class="action-btn">
              <el-icon><Download /></el-icon>
              下载模板
            </el-button>
            <el-button @click="loadPrompts" :loading="loading" class="action-btn">
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
              placeholder="搜索名称或内容"
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
          
          <el-form-item label="类型" class="filter-item">
            <el-select
              v-model="searchForm.prompt_type"
              placeholder="全部"
              clearable
              class="filter-select"
              @change="handleSearch"
            >
              <el-option
                v-for="type in promptTypes"
                :key="type.type"
                :label="type.name"
                :value="type.type"
              />
            </el-select>
          </el-form-item>
          
          <el-form-item label="状态" class="filter-item">
            <el-select
              v-model="searchForm.is_active"
              placeholder="全部"
              clearable
              class="filter-select"
              @change="handleSearch"
            >
              <el-option label="启用" :value="true" />
              <el-option label="禁用" :value="false" />
            </el-select>
          </el-form-item>
        </el-form>
      </el-card>
      
      <!-- 提示词表格 -->
      <el-table 
        :data="prompts" 
        class="config-table"
        v-loading="loading"
        stripe
        :header-cell-style="{ background: '#f5f7fa', color: '#606266', fontWeight: '600', textAlign: 'center' }"
      >
        <el-table-column prop="name" label="名称" min-width="200" align="center" show-overflow-tooltip />
        <el-table-column prop="prompt_type" label="类型" width="150" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ getPromptTypeName(row.prompt_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="100" align="center" sortable />
        <el-table-column prop="content" label="内容" min-width="300" align="center" show-overflow-tooltip />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" align="center" sortable>
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="160" align="center" sortable>
          <template #default="{ row }">
            {{ formatDateTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons" style="display: flex; gap: 4px; justify-content: center; flex-wrap: nowrap;">
              <el-button size="small" @click="handleView(row)" class="btn-view">
                <el-icon><View /></el-icon>
                查看
              </el-button>
              <el-button size="small" type="primary" @click="handleEdit(row)" class="btn-edit">
                <el-icon><Edit /></el-icon>
                编辑
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
      <div v-if="prompts.length > 0 || pagination.total > 0" style="margin-top: 20px; display: flex; justify-content: flex-end;">
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
    
    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="800px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
      >
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="提示词名称" />
        </el-form-item>
        
        <el-form-item label="类型" prop="prompt_type">
          <el-select v-model="form.prompt_type" placeholder="请选择类型" style="width: 100%">
            <el-option
              v-for="type in promptTypes"
              :key="type.type"
              :label="type.name"
              :value="type.type"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="内容" prop="content">
          <el-input 
            v-model="form.content" 
            type="textarea"
            :rows="10"
            placeholder="请输入提示词内容，支持Markdown格式"
            class="prompt-editor"
          />
        </el-form-item>
        
        <el-form-item label="优先级" prop="priority">
          <el-input-number 
            v-model="form.priority" 
            :min="0"
            :max="100"
            style="width: 100%"
          />
          <div style="color: #909399; font-size: 12px; margin-top: 5px">
            数字越大优先级越高，相同类型按优先级排序
          </div>
        </el-form-item>
        
        <el-form-item label="启用状态">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>
    
    <!-- 查看对话框 -->
    <el-dialog
      v-model="viewDialogVisible"
      title="查看提示词"
      width="800px"
    >
      <el-descriptions :column="2" border>
        <el-descriptions-item label="名称">{{ viewData.name }}</el-descriptions-item>
        <el-descriptions-item label="类型">
          <el-tag>{{ getPromptTypeName(viewData.prompt_type) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="优先级">{{ viewData.priority }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="viewData.is_active ? 'success' : 'info'">
            {{ viewData.is_active ? '启用' : '禁用' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="内容" :span="2">
          <pre class="prompt-preview">{{ viewData.content }}</pre>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
    
    <!-- 批量导入对话框 -->
    <el-dialog
      v-model="batchDialogVisible"
      title="批量导入提示词"
      width="600px"
    >
      <el-alert
        title="导入格式说明"
        type="info"
        :closable="false"
        style="margin-bottom: 20px"
      >
        <template #default>
          <div>支持Excel(.xlsx/.xls)或JSON(.json)格式文件</div>
          <div style="margin-top: 10px; color: #909399; font-size: 12px">
            Excel格式：必须包含列：名称、类型、内容（可选：优先级、是否启用）
          </div>
          <div style="margin-top: 5px; color: #909399; font-size: 12px">
            JSON格式：数组格式，每个对象包含name、prompt_type、content等字段
          </div>
        </template>
      </el-alert>
      
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :on-change="handleFileChange"
        :limit="1"
        accept=".xlsx,.xls,.json"
        drag
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          将文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            只能上传Excel或JSON文件
          </div>
        </template>
      </el-upload>
      
      <template #footer>
        <el-button @click="batchDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleBatchSubmit" :loading="submitting" :disabled="!selectedFile">
          导入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { EditPen, Plus, Refresh, Upload, Download, Search, View, Edit, Delete, UploadFilled } from '@element-plus/icons-vue'
import * as promptAPI from '@/api/prompts'

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const viewDialogVisible = ref(false)
const batchDialogVisible = ref(false)
const dialogTitle = ref('添加提示词')
const prompts = ref([])
const promptTypes = ref([])
const viewData = ref({})
const formRef = ref(null)
const uploadRef = ref(null)
const selectedFile = ref(null)

const searchForm = reactive({
  keyword: '',
  prompt_type: '',
  is_active: null
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const form = reactive({
  name: '',
  prompt_type: '',
  content: '',
  priority: 0,
  is_active: true
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  prompt_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  content: [{ required: true, message: '请输入内容', trigger: 'blur' }]
}

// 获取提示词类型名称
const getPromptTypeName = (type) => {
  const typeInfo = promptTypes.value.find(t => t.type === type)
  return typeInfo ? typeInfo.name : type
}

// 加载提示词列表
const loadPrompts = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size,
      ...searchForm
    }
    const res = await promptAPI.getPrompts(params)
    if (res.data.success) {
      prompts.value = res.data.data || []
      pagination.total = res.data.pagination?.total || 0
    }
  } catch (error) {
    console.error('加载提示词列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 加载提示词类型列表
const loadPromptTypes = async () => {
  try {
    const res = await promptAPI.getPromptTypes()
    if (res.data.success) {
      promptTypes.value = res.data.data || []
    }
  } catch (error) {
    console.error('加载提示词类型列表失败:', error)
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  loadPrompts()
}

// 分页变化
const handleSizeChange = () => {
  loadPrompts()
}

const handleCurrentChange = () => {
  loadPrompts()
}

// 查看
const handleView = (row) => {
  viewData.value = { ...row }
  viewDialogVisible.value = true
}

// 添加
const handleAdd = () => {
  dialogTitle.value = '添加提示词'
  resetForm()
  dialogVisible.value = true
}

// 编辑
const handleEdit = (row) => {
  dialogTitle.value = '编辑提示词'
  Object.assign(form, {
    id: row.id,
    name: row.name,
    prompt_type: row.prompt_type,
    content: row.content,
    priority: row.priority,
    is_active: row.is_active
  })
  dialogVisible.value = true
}

// 删除
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除提示词"${row.name}"吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await promptAPI.deletePrompt(row.id)
    ElMessage.success('删除成功')
    loadPrompts()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    submitting.value = true
    
    const data = {
      name: form.name,
      prompt_type: form.prompt_type,
      content: form.content,
      priority: form.priority,
      is_active: form.is_active
    }
    
    if (form.id) {
      await promptAPI.updatePrompt(form.id, data)
      ElMessage.success('更新成功')
    } else {
      await promptAPI.createPrompt(data)
      ElMessage.success('创建成功')
    }
    
    dialogVisible.value = false
    loadPrompts()
  } catch (error) {
    if (error !== false) {
      console.error('提交失败:', error)
    }
  } finally {
    submitting.value = false
  }
}

// 重置表单
const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  Object.assign(form, {
    id: null,
    name: '',
    prompt_type: '',
    content: '',
    priority: 0,
    is_active: true
  })
}

// 批量导入
const handleBatchImport = () => {
  selectedFile.value = null
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
  batchDialogVisible.value = true
}

// 文件选择变化
const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

// 批量提交
const handleBatchSubmit = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请选择要导入的文件')
    return
  }
  
  submitting.value = true
  try {
    const res = await promptAPI.batchCreatePrompts(selectedFile.value)
    if (res.data.success) {
      const data = res.data.data
      let message = `导入完成：成功${data.created_count}个`
      if (data.skipped_count > 0) {
        message += `，跳过${data.skipped_count}个`
      }
      if (data.errors && data.errors.length > 0) {
        message += `，失败${data.errors.length}个`
        console.warn('导入错误:', data.errors)
      }
      ElMessage.success(message)
      batchDialogVisible.value = false
      loadPrompts()
    }
  } catch (error) {
    console.error('批量导入失败:', error)
    ElMessage.error('批量导入失败，请检查文件格式')
  } finally {
    submitting.value = false
  }
}

// 下载模板
const handleDownloadTemplate = async () => {
  try {
    const res = await promptAPI.downloadPromptTemplate()
    // 创建blob对象并下载
    const blob = new Blob([res.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `提示词导入模板_${new Date().toISOString().split('T')[0]}.xlsx`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('模板下载成功')
  } catch (error) {
    console.error('下载模板失败:', error)
    ElMessage.error('下载模板失败')
  }
}

// 格式化日期时间
const formatDateTime = (dateTimeStr) => {
  if (!dateTimeStr) return '-'
  try {
    const date = new Date(dateTimeStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  } catch (error) {
    return dateTimeStr
  }
}

onMounted(() => {
  loadPrompts()
  loadPromptTypes()
})
</script>

<style scoped>
.prompt-config {
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

.filter-input {
  width: 300px;
}

.filter-select {
  width: 200px;
}

.config-table {
  width: 100%;
  margin-top: 20px;
}

.config-table :deep(.el-table__row:hover) {
  background-color: #f5f7fa;
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

.pagination-container {
  margin-top: 20px;
  text-align: right;
  padding: 10px 0;
}

.prompt-editor {
  font-family: 'Courier New', monospace;
}

.prompt-preview {
  background: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>

