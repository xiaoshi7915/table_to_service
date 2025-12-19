<template>
  <div class="dashboard">
    <!-- 表转服务统计 -->
    <div class="stats-section">
      <h3 class="section-title">表转服务统计</h3>
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
    </div>
    
    <!-- 智能问数统计 -->
    <div class="stats-section" style="margin-top: 30px;">
      <h3 class="section-title">智能问数统计</h3>
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-icon" style="background: #9c27b0;">
                <el-icon><ChatLineRound /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.totalSessions }}</div>
                <div class="stat-label">对话总数</div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-icon" style="background: #00bcd4;">
                <el-icon><Message /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.totalMessages }}</div>
                <div class="stat-label">消息总数</div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-icon" style="background: #ff9800;">
                <el-icon><DataBoard /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.totalDashboards }}</div>
                <div class="stat-label">仪表板数</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
    
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
            <span>最近创建的对话</span>
          </template>
          <el-table :data="recentSessions" style="width: 100%" v-loading="loading">
            <el-table-column prop="title" label="对话标题" min-width="150" show-overflow-tooltip />
            <el-table-column prop="data_source_name" label="数据源" width="120" />
            <el-table-column prop="message_count" label="消息数" width="80" align="center">
              <template #default="{ row }">
                <el-tag size="small">{{ row.message_count || 0 }}</el-tag>
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
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'
import { ChatLineRound, Message, DataBoard } from '@element-plus/icons-vue'
import chatApi from '@/api/chat'
import dashboardsApi from '@/api/dashboards'

const stats = ref({
  totalInterfaces: 0,
  activeInterfaces: 0,
  databases: 0,
  apiEndpoints: 0,
  totalSessions: 0,
  totalMessages: 0,
  totalDashboards: 0
})

const recentInterfaces = ref([])
const recentSessions = ref([])
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
    
    // 获取接口配置列表（使用分页，但设置较大的page_size以获取全部数据用于统计）
    const interfacesRes = await api.get('/interface-configs', {
      params: { page: 1, page_size: 1000 }
    })
    if (interfacesRes.data.success) {
      const allInterfaces = interfacesRes.data.data || []
      // 如果返回了分页信息，使用total
      if (interfacesRes.data.pagination && interfacesRes.data.pagination.total) {
        stats.value.totalInterfaces = interfacesRes.data.pagination.total
      } else {
        stats.value.totalInterfaces = allInterfaces.length
      }
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
    
    // 获取智能问数统计数据
    try {
      const sessionsRes = await chatApi.getSessions({ page: 1, page_size: 1 })
      if (sessionsRes.code === 200 || sessionsRes.success) {
        if (sessionsRes.pagination) {
          stats.value.totalSessions = sessionsRes.pagination.total || 0
        } else {
          stats.value.totalSessions = sessionsRes.data?.length || 0
        }
        
        // 获取最近5个对话
        const allSessionsRes = await chatApi.getSessions({ page: 1, page_size: 5 })
        if (allSessionsRes.code === 200 || allSessionsRes.success) {
          recentSessions.value = (allSessionsRes.data || []).slice(0, 5)
        }
        
        // 统计消息总数（从所有会话的消息数累加）
        if (sessionsRes.pagination && sessionsRes.pagination.total > 0) {
          const allSessionsForCount = await chatApi.getSessions({ page: 1, page_size: sessionsRes.pagination.total })
          if (allSessionsForCount.code === 200 || allSessionsForCount.success) {
            const allSessions = allSessionsForCount.data || []
            stats.value.totalMessages = allSessions.reduce((sum, session) => {
              return sum + (session.message_count || 0)
            }, 0)
          }
        }
      }
    } catch (error) {
      console.error('加载智能问数统计数据失败:', error)
    }
    
    // 获取仪表板统计数据
    try {
      const dashboardsRes = await dashboardsApi.getDashboards({ page: 1, page_size: 1 })
      if (dashboardsRes.code === 200 || dashboardsRes.success) {
        if (dashboardsRes.pagination) {
          stats.value.totalDashboards = dashboardsRes.pagination.total || 0
        } else if (Array.isArray(dashboardsRes.data)) {
          stats.value.totalDashboards = dashboardsRes.data.length
        } else if (dashboardsRes.data?.data) {
          stats.value.totalDashboards = dashboardsRes.data.data.length
        }
      }
    } catch (error) {
      console.error('加载仪表板统计数据失败:', error)
    }
  } catch (error) {
    console.error('加载仪表盘数据失败:', error)
    ElMessage.error('加载仪表盘数据失败: ' + (error.response?.data?.detail || error.message))
    stats.value.totalInterfaces = 0
    stats.value.activeInterfaces = 0
    stats.value.databases = 0
    stats.value.apiEndpoints = 0
    stats.value.totalSessions = 0
    stats.value.totalMessages = 0
    stats.value.totalDashboards = 0
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

