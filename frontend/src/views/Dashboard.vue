<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #409eff;">
              <el-icon><Grid /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalInterfaces }}</div>
              <div class="stat-label">总接口数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #67c23a;">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.activeInterfaces }}</div>
              <div class="stat-label">已激活接口</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #e6a23c;">
              <el-icon><Connection /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.databases }}</div>
              <div class="stat-label">数据库连接</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #f56c6c;">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.apiEndpoints }}</div>
              <div class="stat-label">API端点</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>最近配置的接口</span>
          </template>
          <el-table :data="recentInterfaces" style="width: 100%" v-loading="loading">
            <el-table-column prop="interface_name" label="接口名称" min-width="150" />
            <el-table-column prop="database_name" label="数据库" width="120" />
            <el-table-column prop="http_method" label="请求方式" width="100">
              <template #default="{ row }">
                <el-tag :type="getMethodType(row.http_method)" size="small">
                  {{ row.http_method }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="proxy_path" label="接口路径" min-width="150" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'active' ? 'success' : row.status === 'draft' ? 'info' : 'danger'" size="small">
                  {{ row.status === 'active' ? '激活' : row.status === 'draft' ? '草稿' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="160">
              <template #default="{ row }">
                {{ row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '-' }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>系统状态</span>
          </template>
          <div class="system-status">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="数据库连接">
                <el-tag type="success">正常</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="API服务">
                <el-tag type="success">运行中</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="服务版本">
                v1.0.0
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'

const stats = ref({
  totalInterfaces: 0,
  activeInterfaces: 0,
  databases: 0,
  apiEndpoints: 0
})

const recentInterfaces = ref([])
const loading = ref(false)

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

const loadDashboardData = async () => {
  loading.value = true
  try {
    // 获取数据库配置数量
    const dbConfigsRes = await api.get('/database-configs')
    if (dbConfigsRes.data.success) {
      stats.value.databases = dbConfigsRes.data.data?.length || 0
    }
    
    // 获取接口配置列表
    const interfacesRes = await api.get('/interface-configs')
    if (interfacesRes.data.success) {
      const allInterfaces = interfacesRes.data.data || []
      stats.value.totalInterfaces = allInterfaces.length
      stats.value.activeInterfaces = allInterfaces.filter(i => i.status === 'active').length
      stats.value.apiEndpoints = stats.value.activeInterfaces
      
      // 获取最近配置的接口（按创建时间倒序，取前5条）
      const recent = allInterfaces
        .sort((a, b) => {
          const timeA = a.created_at ? new Date(a.created_at).getTime() : 0
          const timeB = b.created_at ? new Date(b.created_at).getTime() : 0
          return timeB - timeA
        })
        .slice(0, 5)
      
      // 获取数据库名称
      for (const item of recent) {
        if (item.database_config_id) {
          try {
            const dbRes = await api.get(`/database-configs/${item.database_config_id}`)
            if (dbRes.data.success) {
              item.database_name = dbRes.data.data.name || '未知数据库'
            }
          } catch (e) {
            item.database_name = '未知数据库'
          }
        }
      }
      
      recentInterfaces.value = recent
    }
  } catch (error) {
    console.error('加载仪表盘数据失败:', error)
    ElMessage.error('加载仪表盘数据失败: ' + (error.response?.data?.detail || error.message))
    stats.value.totalInterfaces = 0
    stats.value.activeInterfaces = 0
    stats.value.databases = 0
    stats.value.apiEndpoints = 0
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadDashboardData()
})
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

.stat-card {
  margin-bottom: 20px;
}

.stat-content {
  display: flex;
  align-items: center;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 24px;
  margin-right: 15px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 5px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.system-status {
  padding: 10px 0;
}
</style>

