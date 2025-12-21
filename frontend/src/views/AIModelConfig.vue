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
      
      <!-- 模型表格 -->
      <el-table 
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
        <el-table-column prop="scene" label="场景" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.scene" type="info" size="small">
              {{ getSceneLabel(row.scene) }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
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
        <el-table-column label="操作" width="380" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button 
                v-if="row.is_active" 
                size="small" 
                type="success" 
                @click="handleTestConnection(row)"
                :loading="row.testing"
                class="btn-test"
              >
                <el-icon><Connection /></el-icon>
                测试
              </el-button>
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
      width="1200px"
      @close="resetForm"
      class="ai-model-dialog"
    >
      <!-- 步骤1: 选择供应商 -->
      <div v-if="currentStep === 0" class="step-content provider-selection">
        <div v-if="filteredProviders.length === 0" class="empty-providers">
          <el-empty description="正在加载供应商列表..." />
        </div>
        <div v-else class="provider-grid">
          <div
            v-for="provider in filteredProviders"
            :key="provider.provider"
            class="provider-card"
            :class="{ selected: form.provider === provider.provider }"
            @click="selectProvider(provider.provider)"
          >
            <div class="provider-logo-wrapper">
              <img 
                v-if="provider.provider && getProviderLogo(provider.provider)" 
                :key="`logo-${provider.provider}`"
                :src="getProviderLogo(provider.provider)" 
                :alt="provider.name || ''"
                class="provider-logo"
                @error="handleLogoError"
              />
              <div v-if="!provider.provider || !getProviderLogo(provider.provider)" class="provider-icon-fallback">
                <el-icon :size="48"><Cpu /></el-icon>
              </div>
            </div>
            <div class="provider-info">
              <div class="provider-name">{{ provider.name }}</div>
              <div class="provider-desc">{{ provider.description }}</div>
            </div>
            <div v-if="form.provider === provider.provider" class="provider-check">
              <el-icon :size="24"><Check /></el-icon>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 步骤2: 添加模型 -->
      <div v-if="currentStep === 1" class="step-content model-config">
        <div class="config-layout">
          <!-- 左侧边栏：供应商列表 -->
          <div class="sidebar">
            <div class="sidebar-header">添加模型</div>
            <el-input
              v-model="providerSearch"
              placeholder="搜索"
              class="sidebar-search"
              clearable
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <div class="provider-list">
              <div
                v-for="provider in filteredProviders"
                :key="provider.provider"
                class="provider-item"
                :class="{ active: form.provider === provider.provider }"
                @click="form.provider = provider.provider; handleProviderChange(provider.provider)"
              >
                <div class="provider-item-logo">
                  <img 
                    v-if="provider.provider && getProviderLogo(provider.provider)" 
                    :key="`item-logo-${provider.provider}`"
                    :src="getProviderLogo(provider.provider)" 
                    :alt="provider.name || ''"
                    class="provider-item-logo-img"
                    @error="handleLogoError"
                  />
                  <el-icon v-if="!provider.provider || !getProviderLogo(provider.provider)" :size="20"><Cpu /></el-icon>
                </div>
                <span class="provider-item-name">{{ provider.name }}</span>
              </div>
            </div>
          </div>
          
          <!-- 右侧主内容：表单 -->
          <div class="main-content">
            <div class="form-header">
              <div class="form-header-logo">
                <img 
                  v-if="selectedProviderInfo && selectedProviderInfo.provider && getProviderLogo(selectedProviderInfo.provider)" 
                  :key="`header-logo-${selectedProviderInfo.provider}`"
                  :src="getProviderLogo(selectedProviderInfo.provider)" 
                  :alt="selectedProviderInfo.name || ''"
                  class="form-header-logo-img"
                  @error="handleLogoError"
                />
                <el-icon v-if="!selectedProviderInfo || !selectedProviderInfo.provider || !getProviderLogo(selectedProviderInfo.provider)" :size="32"><Cpu /></el-icon>
              </div>
              <div class="form-header-info">
                <h3>{{ selectedProviderInfo?.name || '配置模型' }}</h3>
                <p class="form-header-desc">{{ selectedProviderInfo?.description || '' }}</p>
              </div>
            </div>
            
            <el-form
              ref="formRef"
              :model="form"
              :rules="rules"
              label-width="120px"
              class="model-form"
            >
              <el-form-item label="模型名称" prop="name">
                <el-input v-model="form.name" placeholder="请输入模型名称（自定义，用于标识此配置）" />
                <div class="field-hint">提示：为您的模型配置起一个易于识别的名称</div>
              </el-form-item>
              
              <el-form-item label="模型类型">
                <el-select 
                  v-model="form.model_type" 
                  placeholder="请选择模型类型" 
                  style="width: 100%;"
                  clearable
                >
                  <el-option 
                    v-if="selectedProviderInfo && selectedProviderInfo.model_types"
                    v-for="type in selectedProviderInfo.model_types" 
                    :key="type.value" 
                    :label="type.label"
                    :value="type.value"
                  />
                  <template v-else>
                    <el-option label="大语言模型" value="llm" />
                    <el-option label="多模态模型" value="multimodal" />
                    <el-option label="代码模型" value="code" />
                  </template>
                </el-select>
                <div class="field-hint">选择该提供商支持的模型类型</div>
              </el-form-item>
              
              <el-form-item label="基础模型" prop="model_name" v-if="selectedProviderInfo && selectedProviderInfo.models && selectedProviderInfo.models.length > 0">
                <div class="model-selector">
                  <el-select 
                    v-model="form.model_name" 
                    placeholder="请选择基础模型" 
                    style="width: 100%; margin-bottom: 12px;"
                    clearable
                    filterable
                  >
                    <el-option 
                      v-for="model in selectedProviderInfo.models" 
                      :key="model.value || model" 
                      :label="typeof model === 'string' ? model : (model.label || model.value || model)"
                      :value="typeof model === 'string' ? model : (model.value || model.label || model)"
                    >
                      <div class="model-option-content">
                        <div class="model-option-name">{{ typeof model === 'string' ? model : (model.label || model.value || model) }}</div>
                        <div v-if="typeof model === 'object' && model.description" class="model-option-desc">{{ model.description }}</div>
                      </div>
                    </el-option>
                  </el-select>
                  <div class="custom-model-input">
                    <el-input 
                      v-model="customModelName" 
                      placeholder="或输入自定义模型名称"
                      @keyup.enter="handleModelNameEnter"
                      clearable
                    >
                      <template #append>
                        <el-button @click="handleModelNameEnter">确认</el-button>
                      </template>
                    </el-input>
                  </div>
                </div>
                <div class="field-hint">从下拉列表中选择基础模型，或输入自定义模型名称</div>
              </el-form-item>
              <el-form-item label="基础模型" prop="model_name" v-else>
                <el-input 
                  v-model="form.model_name" 
                  placeholder="请输入基础模型名称"
                />
                <div class="field-hint">请输入基础模型名称</div>
              </el-form-item>
              
              <el-form-item label="API域名" prop="api_base_url">
                <el-input 
                  v-model="form.api_base_url" 
                  :placeholder="selectedProviderInfo?.api_url || '请输入API域名'"
                />
              </el-form-item>
              
              <el-form-item label="API Key" prop="api_key">
                <div style="display: flex; gap: 8px; width: 100%;">
                  <el-input 
                    v-model="form.api_key" 
                    :type="showApiKey ? 'text' : 'password'"
                    placeholder="请输入API密钥"
                    style="flex: 1;"
                  >
                    <template #suffix>
                      <el-icon @click="showApiKey = !showApiKey" style="cursor: pointer;">
                        <View v-if="!showApiKey" /><Hide v-else />
                      </el-icon>
                    </template>
                  </el-input>
                  <el-button @click="refreshApiKey" :icon="Refresh" circle />
                  <el-button 
                    v-if="selectedProviderInfo && selectedProviderInfo.api_key_url"
                    type="primary"
                    link
                    @click="openApiKeyUrl"
                  >
                    <el-icon><Link /></el-icon>
                    获取API密钥
                  </el-button>
                </div>
              </el-form-item>
              
              <!-- 高级设置 -->
              <el-collapse v-model="advancedSettingsExpanded" class="advanced-settings">
                <el-collapse-item name="advanced" title="高级设置（可选）">
                  <div class="field-hint">设置额外的模型参数，通常使用默认值即可</div>
                  <el-table :data="modelParams" style="width: 100%; margin-top: 12px;">
                    <el-table-column prop="param" label="参数" width="150" />
                    <el-table-column prop="display_name" label="显示名称" width="150" />
                    <el-table-column prop="value" label="参数值" />
                    <el-table-column label="操作" width="100">
                      <template #default="{ $index }">
                        <el-button type="danger" size="small" @click="removeParam($index)">删除</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                  <el-button type="primary" @click="showAddParamDialog = true" style="margin-top: 12px;">
                    + 添加
                  </el-button>
                </el-collapse-item>
              </el-collapse>
            </el-form>
          </div>
        </div>
      </div>
      
      <!-- 底部按钮 -->
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button v-if="currentStep === 1" @click="prevStep">上一步</el-button>
          <el-button 
            v-if="currentStep === 0" 
            type="primary" 
            @click="nextStep"
            :disabled="!form.provider"
          >
            下一步
          </el-button>
          <el-button 
            v-if="currentStep === 1" 
            type="primary" 
            @click="handleSubmit" 
            :loading="submitting"
          >
            保存
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Cpu, Plus, Refresh, Edit, Delete, Star, Connection, Link, Check, Search, View, Hide } from '@element-plus/icons-vue'
import * as aiModelAPI from '@/api/aiModels'

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('添加AI模型')
const models = ref([])
const providers = ref([])
const formRef = ref(null)
const currentStep = ref(0)
const providerSearch = ref('')
const showApiKey = ref(false)
const advancedSettingsExpanded = ref([]) // 默认不展开高级设置
const showModelSelector = ref(false)
const showAddParamDialog = ref(false)
const modelParams = ref([])
const customModelName = ref('') // 自定义模型名称

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
  model_type: 'llm',
  max_tokens: 2000,
  temperature: '0.7',
  scene: [],
  is_default: false
})

// 过滤后的供应商列表
const filteredProviders = computed(() => {
  if (!providerSearch.value) return providers.value
  const search = providerSearch.value.toLowerCase()
  return providers.value.filter(p => 
    p.name.toLowerCase().includes(search) || 
    p.description.toLowerCase().includes(search)
  )
})

// 计算当前选择的提供商信息
const selectedProviderInfo = computed(() => {
  if (!form.provider) return null
  return providers.value.find(p => p.provider === form.provider)
})

// 获取可用的场景选项（根据提供商支持的场景）
const getAvailableScenes = () => {
  if (!selectedProviderInfo.value || !selectedProviderInfo.value.scenes) {
    return sceneOptions
  }
  return sceneOptions.filter(scene => 
    selectedProviderInfo.value.scenes.includes(scene.value)
  )
}

// 打开API密钥获取链接
const openApiKeyUrl = () => {
  if (selectedProviderInfo.value && selectedProviderInfo.value.api_key_url) {
    window.open(selectedProviderInfo.value.api_key_url, '_blank')
  }
}

// 场景选项
const sceneOptions = [
  { value: 'general', label: '通用', description: '通用场景，适用于大多数任务' },
  { value: 'multimodal', label: '多模态', description: '支持图像、视频等多模态输入' },
  { value: 'code', label: '代码', description: '代码生成、代码理解、代码补全' },
  { value: 'math', label: '数学', description: '数学问题求解、公式推导' },
  { value: 'agent', label: 'Agent', description: '智能体、工具调用、任务规划' },
  { value: 'long_context', label: '长上下文', description: '需要处理长文本的场景' },
  { value: 'low_cost', label: '低成本', description: '追求成本效益的场景' },
  { value: 'enterprise', label: '企业', description: '企业级应用、ToB场景' },
  { value: 'education', label: '教育', description: '教育、培训、学习辅助' },
  { value: 'medical', label: '医疗', description: '医疗咨询、健康管理' },
  { value: 'legal', label: '司法', description: '法律咨询、法条检索' },
  { value: 'finance', label: '金融', description: '金融分析、风险评估' },
  { value: 'government', label: '政务', description: '政务服务、政务咨询' },
  { value: 'industry', label: '工业', description: '工业场景、制造业' },
  { value: 'social', label: '社交', description: '社交对话、聊天机器人' },
  { value: 'roleplay', label: '角色扮演', description: '角色扮演、游戏对话' }
]

const rules = {
  name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  provider: [{ required: true, message: '请选择提供商', trigger: 'change' }],
  api_key: [{ required: true, message: '请输入API密钥', trigger: 'blur' }],
  model_name: [{ required: true, message: '请选择模型标识', trigger: 'change' }],
  max_tokens: [{ required: true, message: '请输入最大Token数', trigger: 'blur' }],
  temperature: [{ required: true, message: '请输入温度参数', trigger: 'blur' }]
}

// 加载模型列表
const loadModels = async () => {
  loading.value = true
  try {
    const res = await aiModelAPI.getAIModels()
    console.log('API响应:', res)
    // 兼容不同的响应格式
    if (res && res.success !== undefined) {
      // 新格式：res.success
      if (res.success) {
        models.value = res.data || []
        pagination.total = models.value.length
        console.log('加载的模型列表:', models.value)
      } else {
        console.error('获取模型列表失败:', res.message)
        ElMessage.error(res.message || '获取模型列表失败')
      }
    } else if (res && res.data) {
      // 旧格式：res.data.success
      if (res.data.success) {
        models.value = res.data.data || []
        pagination.total = models.value.length
        console.log('加载的模型列表:', models.value)
      } else {
        console.error('获取模型列表失败:', res.data.message)
        ElMessage.error(res.data.message || '获取模型列表失败')
      }
    } else {
      console.error('API响应格式错误:', res)
      ElMessage.error('API响应格式错误')
    }
  } catch (error) {
    console.error('加载模型列表失败:', error)
    const errorMsg = error.response?.data?.message || error.message || '加载模型列表失败'
    ElMessage.error(errorMsg)
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
    console.log('API响应完整对象:', res)
    console.log('API响应data:', res?.data)
    
    // 根据 request.js 的响应拦截器，成功响应会被转换为 { code, success, message, data }
    // 所以 res 本身就是转换后的对象，而不是 res.data
    if (res && res.success !== undefined) {
      if (res.success) {
        providers.value = res.data || []
        console.log('加载的供应商列表:', providers.value)
        if (providers.value.length === 0) {
          console.warn('供应商列表为空')
        }
      } else {
        const errorMsg = res.message || res.detail || '未知错误'
        console.error('获取供应商列表失败:', errorMsg)
        ElMessage.error(`获取供应商列表失败: ${errorMsg}`)
      }
    } else if (res && res.data) {
      // 兼容旧格式：res.data
      if (res.data.success) {
        providers.value = res.data.data || []
        console.log('加载的供应商列表:', providers.value)
      } else {
        const errorMsg = res.data.message || res.data.detail || '未知错误'
        console.error('获取供应商列表失败:', errorMsg)
        ElMessage.error(`获取供应商列表失败: ${errorMsg}`)
      }
    } else {
      console.error('API响应格式错误:', res)
      ElMessage.error('API响应格式错误，请检查网络连接')
    }
  } catch (error) {
    console.error('加载提供商列表失败 - 完整错误:', error)
    console.error('错误响应:', error.response)
    const errorMsg = error.response?.data?.message || 
                    error.response?.data?.detail || 
                    error.message || 
                    '未知错误'
    console.error('错误信息:', errorMsg)
    ElMessage.error(`加载供应商列表失败: ${errorMsg}`)
  }
}

// 提供商变化时设置默认值
const handleProviderChange = (provider) => {
  const providerInfo = providers.value.find(p => p.provider === provider)
  if (providerInfo) {
    // 自动设置默认API地址
    form.api_base_url = providerInfo.api_url || ''
    // 自动选择默认模型
    if (providerInfo.default_model) {
      form.model_name = providerInfo.default_model
    } else if (providerInfo.models && providerInfo.models.length > 0) {
      // 兼容字符串数组和对象数组
      const firstModel = providerInfo.models[0]
      form.model_name = typeof firstModel === 'string' ? firstModel : (firstModel.value || firstModel.label || '')
    } else {
      form.model_name = ''
    }
    // 自动选择推荐的场景
    if (providerInfo.scenes && providerInfo.scenes.length > 0) {
      form.scene = [...providerInfo.scenes]
    } else {
      form.scene = []
    }
    // 重置自定义模型名称
    customModelName.value = ''
  }
}

// 获取提供商标签类型
const getProviderTagType = (provider) => {
  const types = {
    deepseek: 'success',
    qwen: 'warning',
    kimi: 'info',
    ernie: 'danger',
    hunyuan: 'success',
    doubao: 'info',
    pangu: 'warning',
    glm: 'success',
    sensetime: 'info',
    spark: 'warning',
    minimax: 'success',
    yi: 'info',
    skywork: 'warning'
  }
  return types[provider] || ''
}

// 获取提供商标签
const getProviderLabel = (provider) => {
  const labels = {
    deepseek: 'DeepSeek',
    qwen: '通义千问',
    kimi: 'Kimi',
    ernie: '百度文心',
    hunyuan: '腾讯混元',
    doubao: '字节豆包',
    pangu: '华为盘古',
    glm: '智谱GLM',
    sensetime: '商汤日日新',
    spark: '科大讯飞星火',
    minimax: 'MiniMax',
    yi: '零一万物Yi',
    skywork: '昆仑万维Skywork'
  }
  return labels[provider] || provider
}

// 获取场景标签
const getSceneLabel = (scene) => {
  const sceneMap = {
    general: '通用',
    multimodal: '多模态',
    code: '代码',
    math: '数学',
    agent: 'Agent',
    long_context: '长上下文',
    low_cost: '低成本',
    enterprise: '企业',
    education: '教育',
    medical: '医疗',
    legal: '司法',
    finance: '金融',
    government: '政务',
    industry: '工业',
    social: '社交',
    roleplay: '角色扮演'
  }
  return sceneMap[scene] || scene
}

// 添加
const handleAdd = () => {
  dialogTitle.value = '添加AI模型'
  resetForm()
  currentStep.value = 0
  // 确保供应商列表已加载
  if (providers.value.length === 0) {
    loadProviders()
  }
  dialogVisible.value = true
}

// 选择供应商
const selectProvider = (provider) => {
  form.provider = provider
  handleProviderChange(provider)
  nextStep()
}

// 下一步
const nextStep = () => {
  if (currentStep.value === 0 && !form.provider) {
    ElMessage.warning('请先选择供应商')
    return
  }
  if (currentStep.value < 1) {
    currentStep.value++
  }
}

// 上一步
const prevStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

// 处理模型名称回车或确认
const handleModelNameEnter = () => {
  if (customModelName.value && customModelName.value.trim()) {
    form.model_name = customModelName.value.trim()
    customModelName.value = ''
    ElMessage.success('已设置自定义模型名称')
  }
}

// 刷新API Key
const refreshApiKey = () => {
  ElMessage.info('刷新功能待实现')
}

// 添加参数
const addParam = (param) => {
  modelParams.value.push({
    param: param.param || '',
    display_name: param.display_name || '',
    value: param.value || ''
  })
}

// 删除参数
const removeParam = (index) => {
  modelParams.value.splice(index, 1)
}

// 获取供应商Logo路径
const getProviderLogo = (provider) => {
  // Logo文件命名规则：使用provider名称，支持png、jpg、svg格式
  // 文件路径：/images/logos/{provider}.png
  // 例如：/images/logos/deepseek.png, /images/logos/qwen.png
  if (!provider || typeof provider !== 'string') return ''
  try {
    return `/images/logos/${provider}.png`
  } catch (error) {
    console.warn('获取Logo路径失败:', error)
    return ''
  }
}

// Logo加载错误处理
const handleLogoError = (event) => {
  // Logo加载失败时隐藏图片，显示默认图标
  try {
    if (event && event.target) {
      event.target.style.display = 'none'
    }
  } catch (error) {
    console.warn('处理Logo错误失败:', error)
  }
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
    model_name: row.model_name || '',
    max_tokens: row.max_tokens,
    temperature: row.temperature,
    scene: row.scene ? (Array.isArray(row.scene) ? row.scene : [row.scene]) : [],
    is_default: row.is_default
  })
  dialogVisible.value = true
}

// 测试连接
const handleTestConnection = async (row) => {
  // 设置测试状态
  row.testing = true
  
  try {
    const res = await aiModelAPI.testModelConnection(row.id)
    console.log('测试连接响应:', res)
    
    // 兼容不同的响应格式
    let responseData = null
    let success = false
    
    if (res && res.success !== undefined) {
      // 新格式：res.success
      success = res.success
      responseData = res.data
    } else if (res && res.data) {
      // 旧格式：res.data.success
      if (res.data.success !== undefined) {
        success = res.data.success
        responseData = res.data.data || res.data
      } else {
        // 直接是数据
        responseData = res.data
        success = true
      }
    } else {
      throw new Error('响应格式错误')
    }
    
    if (success && responseData) {
      // 检查响应数据中的success字段
      const testSuccess = responseData.success !== undefined ? responseData.success : success
      if (testSuccess) {
        const responseTime = responseData.response_time || responseData.responseTime || 'N/A'
        ElMessage.success({
          message: `连接测试成功！响应时间: ${responseTime}秒`,
          duration: 5000
        })
      } else {
        const error = responseData.error || responseData.message || '连接测试失败'
        ElMessage.error({
          message: `连接测试失败: ${error}`,
          duration: 5000
        })
      }
    } else {
      const error = responseData?.error || responseData?.message || '连接测试失败'
      ElMessage.error({
        message: `连接测试失败: ${error}`,
        duration: 5000
      })
    }
  } catch (error) {
    console.error('测试连接失败:', error)
    const errorMsg = error.response?.data?.message || 
                    error.response?.data?.detail || 
                    error.message || 
                    '未知错误'
    ElMessage.error({
      message: `测试连接失败: ${errorMsg}`,
      duration: 5000
    })
  } finally {
    row.testing = false
  }
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
    await aiModelAPI.setDefaultModel(row.id)
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
    
    // 处理场景（如果是数组，取第一个或转换为字符串）
    const sceneValue = Array.isArray(form.scene) 
      ? (form.scene.length > 0 ? form.scene[0] : null) 
      : (form.scene || null)
    
    const data = {
      name: form.name,
      provider: form.provider,
      api_key: form.api_key,
      api_base_url: form.api_base_url || null,
      model_name: form.model_name,
      max_tokens: form.max_tokens,
      temperature: form.temperature,
      scene: sceneValue,
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
  currentStep.value = 0
  providerSearch.value = ''
  showApiKey.value = false
  modelParams.value = []
  customModelName.value = ''
  advancedSettingsExpanded.value = [] // 重置时不展开高级设置
  Object.assign(form, {
    id: null,
    name: '',
    provider: '',
    api_key: '',
    api_base_url: '',
    model_name: '',
    model_type: 'llm',
    max_tokens: 2000,
    temperature: '0.7',
    scene: [],
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

/* ==================== 供应商选择网格 ==================== */
.provider-selection {
  padding: 30px 0;
  min-height: 500px;
}

.provider-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 24px;
  padding: 20px 0;
}

.provider-card {
  position: relative;
  border: 2px solid #e4e7ed;
  border-radius: 16px;
  padding: 24px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: #ffffff;
  overflow: hidden;
}

.provider-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transform: scaleX(0);
  transition: transform 0.3s;
}

.provider-card:hover {
  border-color: #667eea;
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.15);
  transform: translateY(-4px);
}

.provider-card:hover::before {
  transform: scaleX(1);
}

.provider-card.selected {
  border-color: #667eea;
  background: linear-gradient(135deg, #f5f7ff 0%, #ecf5ff 100%);
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.2);
}

.provider-card.selected::before {
  transform: scaleX(1);
}

.provider-logo-wrapper {
  width: 80px;
  height: 80px;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #e9ecef 100%);
  border-radius: 16px;
  overflow: hidden;
  position: relative;
}

.provider-logo {
  width: 100%;
  height: 100%;
  object-fit: contain;
  padding: 12px;
  transition: transform 0.3s;
}

.provider-card:hover .provider-logo {
  transform: scale(1.1);
}

.provider-icon-fallback {
  color: #667eea;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.provider-info {
  margin-bottom: 8px;
}

.provider-name {
  font-weight: 600;
  font-size: 16px;
  margin-bottom: 6px;
  color: #303133;
  line-height: 1.4;
}

.provider-desc {
  font-size: 13px;
  color: #909399;
  line-height: 1.4;
}

.provider-check {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 28px;
  height: 28px;
  background: #67c23a;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 2px 8px rgba(103, 194, 58, 0.3);
  animation: checkIn 0.3s ease-out;
}

@keyframes checkIn {
  from {
    transform: scale(0);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

/* ==================== 左侧边栏 ==================== */
.sidebar {
  width: 280px;
  border-right: 1px solid #e4e7ed;
  padding-right: 24px;
  background: #fafbfc;
  border-radius: 0 12px 12px 0;
  padding: 20px 24px 20px 0;
}

.sidebar-header {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 2px solid #e4e7ed;
  color: #303133;
}

.sidebar-search {
  margin-bottom: 20px;
}

.sidebar-search :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.provider-list {
  max-height: 600px;
  overflow-y: auto;
  padding-right: 8px;
}

.provider-list::-webkit-scrollbar {
  width: 6px;
}

.provider-list::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.provider-list::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.provider-list::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

.provider-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  margin-bottom: 6px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  border: 2px solid transparent;
}

.provider-item:hover {
  background: #f0f4ff;
  border-color: #e0e7ff;
  transform: translateX(4px);
}

.provider-item.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-weight: 600;
  border-color: #667eea;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.provider-item-logo {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  flex-shrink: 0;
}

.provider-item.active .provider-item-logo {
  background: rgba(255, 255, 255, 0.25);
}

.provider-item-logo-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  padding: 4px;
  border-radius: 6px;
}

.provider-item-name {
  flex: 1;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ==================== 主内容区 ==================== */
.main-content {
  flex: 1;
  padding-left: 32px;
  background: #ffffff;
  border-radius: 12px 0 0 12px;
  padding: 24px 32px;
}

.form-header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 2px solid #f0f2f5;
}

.form-header-logo {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #e9ecef 100%);
  border-radius: 16px;
  flex-shrink: 0;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.form-header-logo-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  padding: 12px;
}

.form-header-info {
  flex: 1;
}

.form-header h3 {
  margin: 0 0 6px 0;
  font-size: 24px;
  font-weight: 700;
  color: #303133;
  line-height: 1.3;
}

.form-header-desc {
  margin: 0;
  font-size: 14px;
  color: #909399;
  line-height: 1.5;
}

/* ==================== 表单样式 ==================== */
.model-form {
  max-width: 900px;
}

.model-form :deep(.el-form-item) {
  margin-bottom: 24px;
}

.model-form :deep(.el-form-item__label) {
  font-weight: 600;
  color: #606266;
  font-size: 14px;
}

.model-form :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  transition: all 0.3s;
}

.model-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.model-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.model-form :deep(.el-select) {
  width: 100%;
}

.model-form :deep(.el-select .el-input__wrapper) {
  border-radius: 8px;
}

.field-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 6px;
  border-left: 3px solid #667eea;
  line-height: 1.5;
}

/* ==================== 模型选择器 ==================== */
.model-selector {
  width: 100%;
}

.model-option-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 4px 0;
}

.model-option-name {
  font-weight: 500;
  font-size: 14px;
  color: #303133;
  line-height: 1.4;
}

.model-option-desc {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}

.custom-model-input {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #e4e7ed;
}

/* 移除下拉框选项的悬停效果 */
.model-selector :deep(.el-select-dropdown__item) {
  padding: 10px 20px;
}

.model-selector :deep(.el-select-dropdown__item:hover) {
  background-color: #f5f7fa;
}

.model-selector :deep(.el-select-dropdown__item.is-selected) {
  background-color: #ecf5ff;
  color: #667eea;
  font-weight: 500;
}

/* ==================== 高级设置 ==================== */
.advanced-settings {
  margin-top: 32px;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  overflow: hidden;
  background: #fafbfc;
}

.advanced-settings :deep(.el-collapse-item__header) {
  padding: 16px 20px;
  font-weight: 600;
  background: #fafbfc;
  border-bottom: 1px solid #e4e7ed;
}

.advanced-settings :deep(.el-collapse-item__content) {
  padding: 20px;
  background: #ffffff;
}

.advanced-settings :deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
}

.advanced-settings :deep(.el-table th) {
  background: #f5f7fa;
  font-weight: 600;
  color: #606266;
}

/* ==================== 对话框底部 ==================== */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 20px;
  border-top: 1px solid #e4e7ed;
  margin-top: 20px;
}

.dialog-footer .el-button {
  border-radius: 8px;
  padding: 10px 24px;
  font-weight: 500;
  transition: all 0.3s;
}

.dialog-footer .el-button--primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.dialog-footer .el-button--primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
}

/* ==================== 空状态 ==================== */
.empty-providers {
  padding: 60px 20px;
  text-align: center;
}

/* ==================== 配置布局 ==================== */
.config-layout {
  display: flex;
  gap: 24px;
  min-height: 500px;
}
</style>

