<template>
  <div class="sql-example-config">
    <el-card class="main-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon class="title-icon"><DocumentCopy /></el-icon>
            <span class="title-text">SQL示例配置</span>
            <el-tag v-if="examples.length > 0" type="info" size="small" class="count-tag">
              {{ pagination.total }}
            </el-tag>
          </div>
          <div class="header-actions">
            <el-button type="primary" @click="handleAdd" class="action-btn">
              <el-icon><Plus /></el-icon>
              添加示例
            </el-button>
            <el-button @click="loadExamples" :loading="loading" class="action-btn">
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
              placeholder="搜索标题或问题"
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
          
          <el-form-item label="数据库类型" class="filter-item">
            <el-select
              v-model="searchForm.db_type"
              placeholder="全部"
              clearable
              class="filter-select"
              @change="handleSearch"
            >
              <el-option label="MySQL" value="mysql" />
              <el-option label="PostgreSQL" value="postgresql" />
              <el-option label="SQLite" value="sqlite" />
              <el-option label="SQL Server" value="sqlserver" />
              <el-option label="Oracle" value="oracle" />
            </el-select>
          </el-form-item>
        </el-form>
      </el-card>
      
      <!-- 示例表格 -->
      <el-table 
        :data="examples" 
        class="config-table"
        v-loading="loading"
        stripe
        :header-cell-style="{ background: '#f5f7fa', color: '#606266', fontWeight: '600' }"
      >
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column prop="question" label="问题" min-width="250" show-overflow-tooltip />
        <el-table-column prop="db_type" label="数据库类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.db_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="table_name" label="涉及表" width="150" />
        <el-table-column prop="chart_type" label="图表类型" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.chart_type" type="success" size="small">{{ row.chart_type }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
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
          <el-input v-model="form.title" placeholder="示例标题" />
        </el-form-item>
        
        <el-form-item label="问题（自然语言）" prop="question">
          <el-input 
            v-model="form.question" 
            type="textarea"
            :rows="2"
            placeholder="如：查询各区域的销售量总和"
          />
        </el-form-item>
        
        <el-form-item label="SQL语句" prop="sql_statement">
          <el-input 
            v-model="form.sql_statement" 
            type="textarea"
            :rows="8"
            placeholder="请输入SQL语句"
            class="sql-editor"
          />
        </el-form-item>
        
        <el-form-item label="数据库类型" prop="db_type">
          <el-select v-model="form.db_type" placeholder="请选择数据库类型" style="width: 100%">
            <el-option label="MySQL" value="mysql" />
            <el-option label="PostgreSQL" value="postgresql" />
            <el-option label="SQLite" value="sqlite" />
            <el-option label="SQL Server" value="sqlserver" />
            <el-option label="Oracle" value="oracle" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="涉及表名" prop="table_name">
          <el-input v-model="form.table_name" placeholder="可选" />
        </el-form-item>
        
        <el-form-item label="推荐图表类型" prop="chart_type">
          <el-select v-model="form.chart_type" placeholder="可选" style="width: 100%">
            <el-option label="柱状图" value="bar" />
            <el-option label="折线图" value="line" />
            <el-option label="饼图" value="pie" />
            <el-option label="表格" value="table" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="说明" prop="description">
          <el-input 
            v-model="form.description" 
            type="textarea"
            :rows="2"
            placeholder="示例说明（可选）"
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
    
    <!-- 查看对话框 -->
    <el-dialog
      v-model="viewDialogVisible"
      title="查看SQL示例"
      width="800px"
    >
      <el-descriptions :column="2" border>
        <el-descriptions-item label="标题">{{ viewData.title }}</el-descriptions-item>
        <el-descriptions-item label="数据库类型">
          <el-tag>{{ viewData.db_type }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="问题" :span="2">{{ viewData.question }}</el-descriptions-item>
        <el-descriptions-item label="涉及表">{{ viewData.table_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="图表类型">
          <el-tag v-if="viewData.chart_type" type="success">{{ viewData.chart_type }}</el-tag>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="SQL语句" :span="2">
          <pre class="sql-preview">{{ viewData.sql_statement }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="说明" :span="2">{{ viewData.description || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DocumentCopy, Plus, Refresh, Search, View, Edit, Delete } from '@element-plus/icons-vue'
import * as sqlExampleAPI from '@/api/sqlExamples'

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const viewDialogVisible = ref(false)
const dialogTitle = ref('添加SQL示例')
const examples = ref([])
const viewData = ref({})
const formRef = ref(null)

const searchForm = reactive({
  keyword: '',
  db_type: ''
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const form = reactive({
  title: '',
  question: '',
  sql_statement: '',
  db_type: '',
  table_name: '',
  chart_type: '',
  description: ''
})

const rules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  question: [{ required: true, message: '请输入问题', trigger: 'blur' }],
  sql_statement: [{ required: true, message: '请输入SQL语句', trigger: 'blur' }],
  db_type: [{ required: true, message: '请选择数据库类型', trigger: 'change' }]
}

// 加载示例列表
const loadExamples = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size,
      ...searchForm
    }
    const res = await sqlExampleAPI.getSQLExamples(params)
    if (res.data.success) {
      examples.value = res.data.data || []
      pagination.total = res.data.pagination?.total || 0
    }
  } catch (error) {
    console.error('加载示例列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  loadExamples()
}

// 分页变化
const handleSizeChange = () => {
  loadExamples()
}

const handleCurrentChange = () => {
  loadExamples()
}

// 查看
const handleView = (row) => {
  viewData.value = { ...row }
  viewDialogVisible.value = true
}

// 添加
const handleAdd = () => {
  dialogTitle.value = '添加SQL示例'
  resetForm()
  dialogVisible.value = true
}

// 编辑
const handleEdit = (row) => {
  dialogTitle.value = '编辑SQL示例'
  Object.assign(form, {
    id: row.id,
    title: row.title,
    question: row.question,
    sql_statement: row.sql_statement,
    db_type: row.db_type,
    table_name: row.table_name || '',
    chart_type: row.chart_type || '',
    description: row.description || ''
  })
  dialogVisible.value = true
}

// 删除
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除示例"${row.title}"吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await sqlExampleAPI.deleteSQLExample(row.id)
    ElMessage.success('删除成功')
    loadExamples()
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
      question: form.question,
      sql_statement: form.sql_statement,
      db_type: form.db_type,
      table_name: form.table_name || null,
      chart_type: form.chart_type || null,
      description: form.description || null
    }
    
    if (form.id) {
      await sqlExampleAPI.updateSQLExample(form.id, data)
      ElMessage.success('更新成功')
    } else {
      await sqlExampleAPI.createSQLExample(data)
      ElMessage.success('创建成功')
    }
    
    dialogVisible.value = false
    loadExamples()
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
    question: '',
    sql_statement: '',
    db_type: '',
    table_name: '',
    chart_type: '',
    description: ''
  })
}

onMounted(() => {
  loadExamples()
})
</script>

<style scoped>
.sql-example-config {
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

.sql-editor {
  font-family: 'Courier New', monospace;
}

.sql-preview {
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

