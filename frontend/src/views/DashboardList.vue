<template>
  <div class="dashboard-list-container">
    <el-card class="main-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon class="title-icon"><DataBoard /></el-icon>
            <span class="title-text">仪表板管理</span>
            <el-tag v-if="total > 0" type="info" size="small" class="count-tag">
              {{ total }}
            </el-tag>
          </div>
          <div class="header-actions">
            <el-button type="primary" @click="createDashboard">
              <el-icon><Plus /></el-icon>
              新建仪表板
            </el-button>
          </div>
        </div>
      </template>
      
      <!-- 搜索 -->
      <div class="filter-bar">
        <el-input
          v-model="keyword"
          placeholder="搜索仪表板名称"
          style="width: 300px"
          clearable
          @clear="loadDashboards"
          @keyup.enter="loadDashboards"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" style="margin-left: 10px" @click="loadDashboards">
          <el-icon><Search /></el-icon>
          搜索
        </el-button>
      </div>
      
      <!-- 仪表板列表 -->
      <div class="dashboard-grid" v-loading="loading">
        <el-card
          v-for="dashboard in dashboards"
          :key="dashboard.id"
          class="dashboard-card"
          shadow="hover"
          @click="viewDashboard(dashboard.id)"
        >
          <template #header>
            <div class="dashboard-header">
              <h3>{{ dashboard.name }}</h3>
              <el-dropdown @command="handleCommand($event, dashboard)">
                <el-icon class="more-icon"><MoreFilled /></el-icon>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="view">查看</el-dropdown-item>
                    <el-dropdown-item command="edit">编辑</el-dropdown-item>
                    <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
          
          <div class="dashboard-content">
            <p class="dashboard-description">{{ dashboard.description || '暂无描述' }}</p>
            <div class="dashboard-meta">
              <el-tag size="small">{{ dashboard.widget_count || 0 }} 个组件</el-tag>
              <span class="dashboard-time">{{ formatTime(dashboard.updated_at) }}</span>
            </div>
          </div>
        </el-card>
        
        <el-empty v-if="!loading && dashboards.length === 0" description="暂无仪表板" />
      </div>
      
      <!-- 分页 -->
      <div class="pagination-container" v-if="total > 0">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="total"
          :page-sizes="[12, 24, 48]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadDashboards"
          @current-change="loadDashboards"
        />
      </div>
    </el-card>
    
    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
    >
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
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmSave">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  DataBoard,
  Plus,
  Search,
  MoreFilled
} from '@element-plus/icons-vue'
import dashboardApi from '@/api/dashboards'

const router = useRouter()

const dashboards = ref([])
const total = ref(0)
const loading = ref(false)
const keyword = ref('')
const pagination = ref({
  page: 1,
  page_size: 12
})
const dialogVisible = ref(false)
const dialogTitle = ref('新建仪表板')
const form = ref({
  id: null,
  name: '',
  description: '',
  is_public: false
})

// 加载仪表板列表
const loadDashboards = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      page_size: pagination.value.page_size,
      keyword: keyword.value || undefined
    }
    
    const response = await dashboardApi.getDashboards(params)
    if (response.code === 200) {
      dashboards.value = response.data || []
      total.value = response.pagination?.total || 0
    }
  } catch (error) {
    ElMessage.error('加载仪表板列表失败')
  } finally {
    loading.value = false
  }
}

// 创建仪表板
const createDashboard = () => {
  form.value = {
    id: null,
    name: '',
    description: '',
    is_public: false
  }
  dialogTitle.value = '新建仪表板'
  dialogVisible.value = true
}

// 确认保存
const confirmSave = async () => {
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入仪表板名称')
    return
  }
  
  try {
    if (form.value.id) {
      await dashboardApi.updateDashboard(form.value.id, {
        name: form.value.name,
        description: form.value.description,
        is_public: form.value.is_public
      })
      ElMessage.success('更新成功')
    } else {
      const response = await dashboardApi.createDashboard({
        name: form.value.name,
        description: form.value.description,
        is_public: form.value.is_public
      })
      if (response.code === 200) {
        ElMessage.success('创建成功')
        dialogVisible.value = false
        router.push(`/dashboard-edit/${response.data.id}`)
      }
    }
    await loadDashboards()
  } catch (error) {
    ElMessage.error(form.value.id ? '更新失败' : '创建失败')
  }
}

// 查看仪表板
const viewDashboard = (id) => {
  router.push(`/dashboard-view/${id}`)
}

// 处理命令
const handleCommand = async (command, dashboard) => {
  if (command === 'view') {
    viewDashboard(dashboard.id)
  } else if (command === 'edit') {
    router.push(`/dashboard-edit/${dashboard.id}`)
  } else if (command === 'delete') {
    try {
      await ElMessageBox.confirm('确定要删除这个仪表板吗？', '确认删除', {
        type: 'warning'
      })
      await dashboardApi.deleteDashboard(dashboard.id)
      ElMessage.success('删除成功')
      await loadDashboards()
    } catch (error) {
      if (error !== 'cancel') {
        ElMessage.error('删除失败')
      }
    }
  }
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return ''
  const date = new Date(time)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  loadDashboards()
})
</script>

<style scoped>
.dashboard-list-container {
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

.filter-bar {
  margin-bottom: 20px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.dashboard-card {
  cursor: pointer;
  transition: transform 0.2s;
}

.dashboard-card:hover {
  transform: translateY(-4px);
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dashboard-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.more-icon {
  cursor: pointer;
  font-size: 18px;
}

.dashboard-content {
  padding: 10px 0;
}

.dashboard-description {
  color: #909399;
  font-size: 14px;
  margin-bottom: 10px;
  min-height: 40px;
}

.dashboard-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
}

.dashboard-time {
  font-size: 12px;
  color: #909399;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>

