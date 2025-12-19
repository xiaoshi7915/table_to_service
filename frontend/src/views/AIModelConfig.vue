<template>
  <div class="ai-model-config">
    <el-card class="main-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon class="title-icon"><Cpu /></el-icon>
            <span class="title-text">AI模型配置</span>
            <el-tag v-if="models.length > 0" type="info" size="small" class="count-tag">
              {{ models.length }}
            </el-tag>
          </div>
          <div class="header-actions">
            <el-button type="primary" @click="handleAdd" class="action-btn">
              <el-icon><Plus /></el-icon>
              添加模型
            </el-button>
            <el-button @click="loadModels" :loading="loading" class="action-btn">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>
      
      <!-- 空状态 -->
      <el-empty v-if="models.length === 0 && !loading" description="暂无AI模型配置">
        <el-button type="primary" @click="handleAdd">添加模型</el-button>
      </el-empty>
      
      <!-- 模型表格 -->
      <el-table 
        v-else
        :data="models" 
        class="config-table"
        v-loading="loading"
        stripe
        :header-cell-style="{ background: '#f5f7fa', color: '#606266', fontWeight: '600' }"
      >
        <el-table-column prop="name" label="模型名称" min-width="180" />
        <el-table-column prop="provider" label="提供商" width="120">
          <template #default="{ row }">
            <el-tag :type="getProviderTagType(row.provider)">
              {{ getProviderLabel(row.provider) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="model_name" label="模型标识" min-width="200" />
        <el-table-column prop="max_tokens" label="最大Token" width="120" />
        <el-table-column prop="temperature" label="温度参数" width="120" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="默认" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="warning" size="small">默认</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button 
                v-if="!row.is_default && row.is_active" 
                size="small" 
                type="warning" 
                @click="handleSetDefault(row)"
                class="btn-default"
              >
                <el-icon><Star /></el-icon>
                设默认
              </el-button>
              <el-button size="small" type="primary" @click="handleEdit(row)" class="btn-edit">
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
              <el-button 
                size="small" 
                type="danger" 
                @click="handleDelete(row)"
                :disabled="row.is_default"
                class="btn-delete"
              >
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div v-if="models.length > 0 || pagination.total > 0" class="pagination-container">
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
        <el-form-item label="模型名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入模型名称" />
        </el-form-item>
        
        <el-form-item label="提供商" prop="provider">
          <el-select 
            v-model="form.provider" 
            placeholder="请选择提供商"
            style="width: 100%"
            @change="handleProviderChange"
          >
            <el-option
              v-for="provider in providers"
              :key="provider.provider"
              :label="provider.name"
              :value="provider.provider"
            >
              <span>{{ provider.name }}</span>
              <span style="color: #8492a6; font-size: 13px; margin-left: 10px">
                {{ provider.description }}
              </span>
            </el-option>
          </el-select>
        </el-form-item>
        
        <el-form-item label="API密钥" prop="api_key">
          <el-input 
            v-model="form.api_key" 
            type="password"
            placeholder="请输入API密钥"
            show-password
          />
        </el-form-item>
        
        <el-form-item label="API地址" prop="api_base_url">
          <el-input 
            v-model="form.api_base_url" 
            placeholder="留空使用默认地址"
          />
        </el-form-item>
        
        <el-form-item label="模型标识" prop="model_name">
          <el-input 
            v-model="form.model_name" 
            placeholder="请输入模型标识，如：deepseek-chat"
          />
        </el-form-item>
        
        <el-form-item label="最大Token" prop="max_tokens">
          <el-input-number 
            v-model="form.max_tokens" 
            :min="100"
            :max="100000"
            style="width: 100%"
          />
        </el-form-item>
        
        <el-form-item label="温度参数" prop="temperature">
          <el-input 
            v-model="form.temperature" 
            placeholder="0.0-2.0，默认0.7"
          />
        </el-form-item>
        
        <el-form-item label="设为默认">
          <el-switch v-model="form.is_default" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Cpu, Plus, Refresh, Edit, Delete, Star } from '@element-plus/icons-vue'
import * as aiModelAPI from '@/api/aiModels'

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('添加AI模型')
const models = ref([])
const providers = ref([])
const formRef = ref(null)

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const form = reactive({
  name: '',
  provider: '',
  api_key: '',
  api_base_url: '',
  model_name: '',
  max_tokens: 2000,
  temperature: '0.7',
  is_default: false
})

const rules = {
  name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  provider: [{ required: true, message: '请选择提供商', trigger: 'change' }],
  api_key: [{ required: true, message: '请输入API密钥', trigger: 'blur' }],
  model_name: [{ required: true, message: '请输入模型标识', trigger: 'blur' }],
  max_tokens: [{ required: true, message: '请输入最大Token数', trigger: 'blur' }],
  temperature: [{ required: true, message: '请输入温度参数', trigger: 'blur' }]
}

// 加载模型列表
const loadModels = async () => {
  loading.value = true
  try {
    const res = await aiModelAPI.getAIModels()
    if (res.data.success) {
      models.value = res.data.data || []
      pagination.total = models.value.length
    }
  } catch (error) {
    console.error('加载模型列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 分页变化
const handleSizeChange = () => {
  loadModels()
}

const handleCurrentChange = () => {
  loadModels()
}

// 加载提供商列表
const loadProviders = async () => {
  try {
    const res = await aiModelAPI.getProviders()
    if (res.data.success) {
      providers.value = res.data.data || []
    }
  } catch (error) {
    console.error('加载提供商列表失败:', error)
  }
}

// 提供商变化时设置默认值
const handleProviderChange = (provider) => {
  const providerInfo = providers.value.find(p => p.provider === provider)
  if (providerInfo) {
    if (!form.api_base_url) {
      form.api_base_url = providerInfo.api_url || ''
    }
    if (!form.model_name) {
      form.model_name = providerInfo.default_model || ''
    }
  }
}

// 获取提供商标签类型
const getProviderTagType = (provider) => {
  const types = {
    deepseek: 'success',
    qwen: 'warning',
    kimi: 'info'
  }
  return types[provider] || ''
}

// 获取提供商标签
const getProviderLabel = (provider) => {
  const labels = {
    deepseek: 'DeepSeek',
    qwen: '通义千问',
    kimi: 'Kimi'
  }
  return labels[provider] || provider
}

// 添加
const handleAdd = () => {
  dialogTitle.value = '添加AI模型'
  resetForm()
  dialogVisible.value = true
}

// 编辑
const handleEdit = (row) => {
  dialogTitle.value = '编辑AI模型'
  Object.assign(form, {
    id: row.id,
    name: row.name,
    provider: row.provider,
    api_key: '', // 不显示密钥
    api_base_url: row.api_base_url || '',
    model_name: row.model_name,
    max_tokens: row.max_tokens,
    temperature: row.temperature,
    is_default: row.is_default
  })
  dialogVisible.value = true
}

// 删除
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除模型"${row.name}"吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await aiModelAPI.deleteAIModel(row.id)
    ElMessage.success('删除成功')
    loadModels()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}

// 设置默认
const handleSetDefault = async (row) => {
  try {
    await aiModelAPI.setDefaultAIModel(row.id)
    ElMessage.success('设置成功')
    loadModels()
  } catch (error) {
    console.error('设置默认失败:', error)
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
      provider: form.provider,
      api_key: form.api_key,
      api_base_url: form.api_base_url || null,
      model_name: form.model_name,
      max_tokens: form.max_tokens,
      temperature: form.temperature,
      is_default: form.is_default
    }
    
    if (form.id) {
      await aiModelAPI.updateAIModel(form.id, data)
      ElMessage.success('更新成功')
    } else {
      await aiModelAPI.createAIModel(data)
      ElMessage.success('创建成功')
    }
    
    dialogVisible.value = false
    loadModels()
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
    provider: '',
    api_key: '',
    api_base_url: '',
    model_name: '',
    max_tokens: 2000,
    temperature: '0.7',
    is_default: false
  })
}

onMounted(() => {
  loadModels()
  loadProviders()
})
</script>

<style scoped>
.ai-model-config {
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

