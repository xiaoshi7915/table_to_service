<template>
  <div class="knowledge-config">
    <el-card class="main-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon class="title-icon"><Reading /></el-icon>
            <span class="title-text">业务知识库</span>
            <el-tag v-if="knowledgeList.length > 0" type="info" size="small" class="count-tag">
              {{ pagination.total }}
            </el-tag>
          </div>
          <div class="header-actions">
            <el-button type="primary" @click="handleAdd" class="action-btn">
              <el-icon><Plus /></el-icon>
              添加知识
            </el-button>
            <el-button @click="loadKnowledge" :loading="loading" class="action-btn">
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
              placeholder="搜索标题或内容"
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
          
          <el-form-item label="分类" class="filter-item">
            <el-select
              v-model="searchForm.category"
              placeholder="全部"
              clearable
              class="filter-select"
              @change="handleSearch"
            >
              <el-option
                v-for="cat in categories"
                :key="cat"
                :label="cat"
                :value="cat"
              />
            </el-select>
          </el-form-item>
          
          <el-form-item label="标签" class="filter-item">
            <el-select
              v-model="searchForm.tag"
              placeholder="全部"
              clearable
              class="filter-select"
              @change="handleSearch"
            >
              <el-option
                v-for="tag in tags"
                :key="tag"
                :label="tag"
                :value="tag"
              />
            </el-select>
          </el-form-item>
        </el-form>
      </el-card>
      
      <!-- 知识列表 -->
      <el-table 
        :data="knowledgeList" 
        class="config-table"
        v-loading="loading"
        stripe
        :header-cell-style="{ background: '#f5f7fa', color: '#606266', fontWeight: '600', textAlign: 'center' }"
      >
        <el-table-column prop="title" label="标题" min-width="200" align="center" show-overflow-tooltip />
        <el-table-column prop="category" label="分类" width="150" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.category" size="small">{{ row.category }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="tags" label="标签" min-width="200" align="center">
          <template #default="{ row }">
            <el-tag
              v-for="tag in row.tags"
              :key="tag"
              size="small"
              style="margin-right: 5px"
            >
              {{ tag }}
            </el-tag>
            <span v-if="!row.tags || row.tags.length === 0">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="content" label="内容" min-width="300" align="center" show-overflow-tooltip />
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
      <div v-if="knowledgeList.length > 0 || pagination.total > 0" style="margin-top: 20px; display: flex; justify-content: flex-end;">
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
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" placeholder="知识标题" />
        </el-form-item>
        
        <el-form-item label="内容" prop="content">
          <el-input 
            v-model="form.content" 
            type="textarea"
            :rows="8"
            placeholder="请输入知识内容"
          />
        </el-form-item>
        
        <el-form-item label="分类" prop="category">
          <el-input 
            v-model="form.category" 
            placeholder="可选，如：业务规则"
          />
        </el-form-item>
        
        <el-form-item label="标签" prop="tags">
          <el-input 
            v-model="form.tags" 
            placeholder="多个标签用逗号分隔，如：销售,规则,重要"
          />
          <div style="color: #909399; font-size: 12px; margin-top: 5px">
            多个标签用逗号分隔
          </div>
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
      title="查看知识条目"
      width="800px"
    >
      <el-descriptions :column="2" border>
        <el-descriptions-item label="标题">{{ viewData.title }}</el-descriptions-item>
        <el-descriptions-item label="分类">
          <el-tag v-if="viewData.category">{{ viewData.category }}</el-tag>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="标签" :span="2">
          <el-tag
            v-for="tag in viewData.tags"
            :key="tag"
            size="small"
            style="margin-right: 5px"
          >
            {{ tag }}
          </el-tag>
          <span v-if="!viewData.tags || viewData.tags.length === 0">-</span>
        </el-descriptions-item>
        <el-descriptions-item label="内容" :span="2">
          <div class="content-preview">{{ viewData.content }}</div>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Reading, Plus, Refresh, Search, View, Edit, Delete } from '@element-plus/icons-vue'
import * as knowledgeAPI from '@/api/knowledge'

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const viewDialogVisible = ref(false)
const dialogTitle = ref('添加知识')
const knowledgeList = ref([])
const categories = ref([])
const tags = ref([])
const viewData = ref({})
const formRef = ref(null)

const searchForm = reactive({
  keyword: '',
  category: '',
  tag: ''
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const form = reactive({
  title: '',
  content: '',
  category: '',
  tags: ''
})

const rules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入内容', trigger: 'blur' }]
}

// 加载知识列表
const loadKnowledge = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size,
      ...searchForm
    }
    const res = await knowledgeAPI.searchKnowledge(params)
    if (res.data.success) {
      knowledgeList.value = res.data.data || []
      pagination.total = res.data.pagination?.total || 0
    }
  } catch (error) {
    console.error('加载知识列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 加载分类列表
const loadCategories = async () => {
  try {
    const res = await knowledgeAPI.getKnowledgeCategories()
    if (res.data.success) {
      categories.value = res.data.data || []
    }
  } catch (error) {
    console.error('加载分类列表失败:', error)
  }
}

// 加载标签列表
const loadTags = async () => {
  try {
    const res = await knowledgeAPI.getKnowledgeTags()
    if (res.data.success) {
      tags.value = res.data.data || []
    }
  } catch (error) {
    console.error('加载标签列表失败:', error)
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  loadKnowledge()
}

// 分页变化
const handleSizeChange = () => {
  loadKnowledge()
}

const handleCurrentChange = () => {
  loadKnowledge()
}

// 查看
const handleView = (row) => {
  viewData.value = { ...row }
  viewDialogVisible.value = true
}

// 添加
const handleAdd = () => {
  dialogTitle.value = '添加知识'
  resetForm()
  dialogVisible.value = true
}

// 编辑
const handleEdit = (row) => {
  dialogTitle.value = '编辑知识'
  Object.assign(form, {
    id: row.id,
    title: row.title,
    content: row.content,
    category: row.category || '',
    tags: row.tags ? row.tags.join(',') : ''
  })
  dialogVisible.value = true
}

// 删除
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除知识"${row.title}"吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await knowledgeAPI.deleteKnowledge(row.id)
    ElMessage.success('删除成功')
    loadKnowledge()
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
      title: form.title,
      content: form.content,
      category: form.category || null,
      tags: form.tags || null
    }
    
    if (form.id) {
      await knowledgeAPI.updateKnowledge(form.id, data)
      ElMessage.success('更新成功')
    } else {
      await knowledgeAPI.createKnowledge(data)
      ElMessage.success('创建成功')
    }
    
    dialogVisible.value = false
    loadKnowledge()
    loadCategories()
    loadTags()
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
    title: '',
    content: '',
    category: '',
    tags: ''
  })
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
  loadKnowledge()
  loadCategories()
  loadTags()
})
</script>

<style scoped>
.knowledge-config {
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

.content-preview {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>

