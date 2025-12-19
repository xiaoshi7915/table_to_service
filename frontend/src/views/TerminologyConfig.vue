<template>
  <div class="terminology-config">
    <el-card class="main-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon class="title-icon"><Collection /></el-icon>
            <span class="title-text">术语配置</span>
            <el-tag v-if="terminologies.length > 0" type="info" size="small" class="count-tag">
              {{ pagination.total }}
            </el-tag>
          </div>
          <div class="header-actions">
            <el-button type="primary" @click="handleAdd" class="action-btn">
              <el-icon><Plus /></el-icon>
              添加术语
            </el-button>
            <el-button @click="handleBatchImport" class="action-btn">
              <el-icon><Upload /></el-icon>
              批量导入
            </el-button>
            <el-button @click="loadTerminologies" :loading="loading" class="action-btn">
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
              placeholder="搜索业务术语或数据库字段"
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
          
          <el-form-item label="表名" class="filter-item">
            <el-select
              v-model="searchForm.table_name"
              placeholder="全部"
              clearable
              class="filter-select"
              @change="handleSearch"
            >
              <el-option
                v-for="table in tableNames"
                :key="table"
                :label="table"
                :value="table"
              />
            </el-select>
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
        </el-form>
      </el-card>
      
      <!-- 术语表格 -->
      <el-table 
        :data="terminologies" 
        class="config-table"
        v-loading="loading"
        stripe
        :header-cell-style="{ background: '#f5f7fa', color: '#606266', fontWeight: '600' }"
      >
        <el-table-column prop="business_term" label="业务术语" min-width="180" />
        <el-table-column prop="db_field" label="数据库字段" min-width="180" />
        <el-table-column prop="table_name" label="所属表" width="150" />
        <el-table-column prop="category" label="分类" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.category" size="small">{{ row.category }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
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
      <div v-if="pagination.total > 0" class="pagination-container">
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
      width="600px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
      >
        <el-form-item label="业务术语" prop="business_term">
          <el-input v-model="form.business_term" placeholder="如：销售量" />
        </el-form-item>
        
        <el-form-item label="数据库字段" prop="db_field">
          <el-input v-model="form.db_field" placeholder="如：sales_amount" />
        </el-form-item>
        
        <el-form-item label="所属表名" prop="table_name">
          <el-input v-model="form.table_name" placeholder="可选，如：sales" />
        </el-form-item>
        
        <el-form-item label="分类" prop="category">
          <el-input v-model="form.category" placeholder="可选，如：销售类" />
        </el-form-item>
        
        <el-form-item label="说明" prop="description">
          <el-input 
            v-model="form.description" 
            type="textarea"
            :rows="3"
            placeholder="术语说明（可选）"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>
    
    <!-- 批量导入对话框 -->
    <el-dialog
      v-model="batchDialogVisible"
      title="批量导入术语"
      width="600px"
    >
      <el-alert
        title="导入格式说明"
        type="info"
        :closable="false"
        style="margin-bottom: 20px"
      >
        <template #default>
          <div>每行一个术语，格式：业务术语,数据库字段,表名,分类,说明</div>
          <div style="margin-top: 10px; color: #909399; font-size: 12px">
            示例：销售量,sales_amount,sales,销售类,销售金额
          </div>
        </template>
      </el-alert>
      
      <el-input
        v-model="batchText"
        type="textarea"
        :rows="10"
        placeholder="请输入术语数据，每行一个"
      />
      
      <template #footer>
        <el-button @click="batchDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleBatchSubmit" :loading="submitting">
          导入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Collection, Plus, Refresh, Upload, Search, Edit, Delete } from '@element-plus/icons-vue'
import * as terminologyAPI from '@/api/terminologies'

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const batchDialogVisible = ref(false)
const dialogTitle = ref('添加术语')
const terminologies = ref([])
const categories = ref([])
const tableNames = ref([])
const batchText = ref('')
const formRef = ref(null)

const searchForm = reactive({
  keyword: '',
  table_name: '',
  category: ''
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const form = reactive({
  business_term: '',
  db_field: '',
  table_name: '',
  category: '',
  description: ''
})

const rules = {
  business_term: [{ required: true, message: '请输入业务术语', trigger: 'blur' }],
  db_field: [{ required: true, message: '请输入数据库字段', trigger: 'blur' }]
}

// 加载术语列表
const loadTerminologies = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size,
      ...searchForm
    }
    const res = await terminologyAPI.getTerminologies(params)
    if (res.data.success) {
      terminologies.value = res.data.data || []
      pagination.total = res.data.pagination?.total || 0
    }
  } catch (error) {
    console.error('加载术语列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 加载分类列表
const loadCategories = async () => {
  try {
    const res = await terminologyAPI.getCategories()
    if (res.data.success) {
      categories.value = res.data.data || []
    }
  } catch (error) {
    console.error('加载分类列表失败:', error)
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  loadTerminologies()
}

// 分页变化
const handleSizeChange = () => {
  loadTerminologies()
}

const handleCurrentChange = () => {
  loadTerminologies()
}

// 添加
const handleAdd = () => {
  dialogTitle.value = '添加术语'
  resetForm()
  dialogVisible.value = true
}

// 编辑
const handleEdit = (row) => {
  dialogTitle.value = '编辑术语'
  Object.assign(form, {
    id: row.id,
    business_term: row.business_term,
    db_field: row.db_field,
    table_name: row.table_name || '',
    category: row.category || '',
    description: row.description || ''
  })
  dialogVisible.value = true
}

// 删除
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除术语"${row.business_term}"吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await terminologyAPI.deleteTerminology(row.id)
    ElMessage.success('删除成功')
    loadTerminologies()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}

// 批量导入
const handleBatchImport = () => {
  batchText.value = ''
  batchDialogVisible.value = true
}

// 批量提交
const handleBatchSubmit = async () => {
  if (!batchText.value.trim()) {
    ElMessage.warning('请输入要导入的数据')
    return
  }
  
  submitting.value = true
  try {
    const lines = batchText.value.trim().split('\n').filter(line => line.trim())
    const terminologies = lines.map(line => {
      const parts = line.split(',').map(p => p.trim())
      return {
        business_term: parts[0] || '',
        db_field: parts[1] || '',
        table_name: parts[2] || null,
        category: parts[3] || null,
        description: parts[4] || null
      }
    })
    
    const res = await terminologyAPI.batchCreateTerminologies({ terminologies })
    if (res.data.success) {
      ElMessage.success(`导入完成：成功${res.data.data.created_count}个，跳过${res.data.data.skipped_count}个`)
      batchDialogVisible.value = false
      loadTerminologies()
    }
  } catch (error) {
    console.error('批量导入失败:', error)
  } finally {
    submitting.value = false
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    submitting.value = true
    
    const data = {
      business_term: form.business_term,
      db_field: form.db_field,
      table_name: form.table_name || null,
      category: form.category || null,
      description: form.description || null
    }
    
    if (form.id) {
      await terminologyAPI.updateTerminology(form.id, data)
      ElMessage.success('更新成功')
    } else {
      await terminologyAPI.createTerminology(data)
      ElMessage.success('创建成功')
    }
    
    dialogVisible.value = false
    loadTerminologies()
    loadCategories()
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
    business_term: '',
    db_field: '',
    table_name: '',
    category: '',
    description: ''
  })
}

onMounted(() => {
  loadTerminologies()
  loadCategories()
})
</script>

<style scoped>
.terminology-config {
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
</style>

