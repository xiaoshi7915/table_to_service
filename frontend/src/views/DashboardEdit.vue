<template>
  <div class="dashboard-edit-container">
    <el-card class="main-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon class="title-icon"><DataBoard /></el-icon>
            <span class="title-text">{{ isEdit ? '编辑仪表板' : '新建仪表板' }}</span>
          </div>
          <div class="header-actions">
            <el-button @click="goBack">取消</el-button>
            <el-button type="primary" @click="saveDashboard">保存</el-button>
          </div>
        </div>
      </template>
      
      <div v-loading="loading" class="edit-content">
        <!-- 基本信息 -->
        <el-card class="info-card" shadow="never">
          <template #header>
            <span>基本信息</span>
          </template>
          <el-form :model="form" label-width="100px">
            <el-form-item label="仪表板名称" required>
              <el-input v-model="form.name" placeholder="请输入仪表板名称" maxlength="200" />
            </el-form-item>
            <el-form-item label="描述">
              <el-input
                v-model="form.description"
                type="textarea"
                :rows="3"
                placeholder="请输入描述"
                maxlength="500"
              />
            </el-form-item>
            <el-form-item label="公开">
              <el-switch v-model="form.is_public" />
            </el-form-item>
          </el-form>
        </el-card>
        
        <!-- 组件列表 -->
        <el-card class="widgets-card" shadow="never" style="margin-top: 20px">
          <template #header>
            <div class="widgets-header">
              <span>组件列表</span>
              <el-button type="primary" size="small" @click="showAddWidgetDialog">
                <el-icon><Plus /></el-icon>
                添加组件
              </el-button>
            </div>
          </template>
          
          <div v-if="widgets.length === 0" class="empty-widgets">
            <el-empty description="暂无组件，点击上方按钮添加" />
          </div>
          
          <div v-else class="widgets-list">
            <el-card
              v-for="(widget, index) in widgets"
              :key="widget.id || index"
              class="widget-item"
              shadow="hover"
            >
              <template #header>
                <div class="widget-item-header">
                  <span>{{ widget.title }}</span>
                  <div>
                    <el-button type="danger" size="small" text @click="removeWidget(index)">
                      <el-icon><Delete /></el-icon>
                      删除
                    </el-button>
                  </div>
                </div>
              </template>
              
              <el-form :model="widget" label-width="100px" size="small">
                <el-row :gutter="20">
                  <el-col :span="12">
                    <el-form-item label="组件类型">
                      <el-tag>{{ widget.widget_type }}</el-tag>
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="标题">
                      <el-input v-model="widget.title" />
                    </el-form-item>
                  </el-col>
                </el-row>
                <el-row :gutter="20">
                  <el-col :span="6">
                    <el-form-item label="X坐标">
                      <el-input-number v-model="widget.position_x" :min="0" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="6">
                    <el-form-item label="Y坐标">
                      <el-input-number v-model="widget.position_y" :min="0" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="6">
                    <el-form-item label="宽度">
                      <el-input-number v-model="widget.width" :min="100" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="6">
                    <el-form-item label="高度">
                      <el-input-number v-model="widget.height" :min="100" />
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-form>
            </el-card>
          </div>
        </el-card>
      </div>
    </el-card>
    
    <!-- 添加组件对话框 -->
    <el-dialog
      v-model="addWidgetDialogVisible"
      title="添加组件"
      width="600px"
    >
      <el-form :model="newWidget" label-width="100px">
        <el-form-item label="组件类型" required>
          <el-select v-model="newWidget.widget_type" placeholder="请选择组件类型">
            <el-option label="图表" value="chart" />
            <el-option label="表格" value="table" />
          </el-select>
        </el-form-item>
        <el-form-item label="标题" required>
          <el-input v-model="newWidget.title" placeholder="请输入组件标题" />
        </el-form-item>
        <el-form-item label="宽度">
          <el-input-number v-model="newWidget.width" :min="100" />
        </el-form-item>
        <el-form-item label="高度">
          <el-input-number v-model="newWidget.height" :min="100" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addWidgetDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addWidget">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  DataBoard,
  Plus,
  Delete
} from '@element-plus/icons-vue'
import dashboardApi from '@/api/dashboards'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const isEdit = computed(() => !!route.params.id)
const form = ref({
  name: '',
  description: '',
  is_public: false
})
const widgets = ref([])
const addWidgetDialogVisible = ref(false)
const newWidget = ref({
  widget_type: 'chart',
  title: '',
  config: {},
  position_x: 0,
  position_y: 0,
  width: 400,
  height: 300
})

// 加载仪表板数据
const loadDashboard = async () => {
  if (!isEdit.value) return
  
  loading.value = true
  try {
    const dashboardId = parseInt(route.params.id)
    const response = await dashboardApi.getDashboard(dashboardId)
    
    if (response.code === 200) {
      const data = response.data
      form.value = {
        name: data.name,
        description: data.description || '',
        is_public: data.is_public || false
      }
      widgets.value = data.widgets || []
    }
  } catch (error) {
    ElMessage.error('加载仪表板失败')
  } finally {
    loading.value = false
  }
}

// 保存仪表板
const saveDashboard = async () => {
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入仪表板名称')
    return
  }
  
  loading.value = true
  try {
    if (isEdit.value) {
      // 更新
      await dashboardApi.updateDashboard(parseInt(route.params.id), {
        name: form.value.name,
        description: form.value.description,
        is_public: form.value.is_public
      })
      ElMessage.success('更新成功')
    } else {
      // 创建
      const response = await dashboardApi.createDashboard({
        name: form.value.name,
        description: form.value.description,
        is_public: form.value.is_public
      })
      
      if (response.code === 200) {
        ElMessage.success('创建成功')
        // 如果有组件，需要创建仪表板后再添加组件
        if (widgets.value.length > 0) {
          router.push(`/dashboard-edit/${response.data.id}`)
        } else {
          router.push('/dashboard-list')
        }
        return
      }
    }
    
    // 保存组件（简化版，实际应该逐个保存）
    router.push('/dashboard-list')
  } catch (error) {
    ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
  } finally {
    loading.value = false
  }
}

// 显示添加组件对话框
const showAddWidgetDialog = () => {
  newWidget.value = {
    widget_type: 'chart',
    title: '',
    config: {},
    position_x: 0,
    position_y: widgets.value.length * 50,
    width: 400,
    height: 300
  }
  addWidgetDialogVisible.value = true
}

// 添加组件
const addWidget = () => {
  if (!newWidget.value.title.trim()) {
    ElMessage.warning('请输入组件标题')
    return
  }
  
  widgets.value.push({
    ...newWidget.value,
    config: newWidget.value.widget_type === 'chart' ? {
      title: { text: newWidget.value.title },
      xAxis: { type: 'category', data: [] },
      yAxis: { type: 'value' },
      series: []
    } : {}
  })
  
  addWidgetDialogVisible.value = false
  ElMessage.success('添加组件成功')
}

// 删除组件
const removeWidget = (index) => {
  widgets.value.splice(index, 1)
  ElMessage.success('删除组件成功')
}

// 返回
const goBack = () => {
  router.push('/dashboard-list')
}

onMounted(() => {
  loadDashboard()
})
</script>

<style scoped>
.dashboard-edit-container {
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 100px);
}

.main-card {
  background: white;
  border-radius: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-icon {
  font-size: 20px;
  color: #409eff;
}

.title-text {
  font-size: 18px;
  font-weight: 600;
}

.edit-content {
  padding: 20px 0;
}

.info-card,
.widgets-card {
  background: white;
}

.widgets-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.empty-widgets {
  padding: 40px 0;
}

.widgets-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.widget-item {
  background: #fafafa;
}

.widget-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

