<template>
  <div class="cocoindex-config">
    <el-card class="main-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon class="title-icon"><Setting /></el-icon>
            <span class="title-text">CocoIndex 配置</span>
          </div>
          <div class="header-actions">
            <el-button @click="loadStatus" :loading="loading" class="action-btn">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button type="primary" @click="handleSyncAll" :loading="syncingAll" class="action-btn">
              <el-icon><RefreshRight /></el-icon>
              同步所有数据源
            </el-button>
          </div>
        </div>
      </template>
      
      <!-- 状态统计 -->
      <el-row :gutter="20" v-if="status">
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="stat-item">
              <div class="stat-label">文档总数</div>
              <div class="stat-value">{{ status.documents?.total || 0 }}</div>
              <div class="stat-detail">
                <el-tag size="small" type="success">{{ status.documents?.completed || 0 }} 已完成</el-tag>
                <el-tag size="small" type="warning" style="margin-left: 5px;">{{ status.documents?.processing || 0 }} 处理中</el-tag>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="stat-item">
              <div class="stat-label">分块总数</div>
              <div class="stat-value">{{ status.chunks?.total || 0 }}</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="stat-item">
              <div class="stat-label">数据源总数</div>
              <div class="stat-value">{{ status.data_sources?.total || 0 }}</div>
              <div class="stat-detail">
                <el-tag size="small" type="success">{{ status.data_sources?.enabled || 0 }} 已启用</el-tag>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="stat-item">
              <div class="stat-label">集合数量</div>
              <div class="stat-value">{{ status.collections?.length || 0 }}</div>
            </div>
          </el-card>
        </el-col>
      </el-row>
      
      <!-- 同步状态 -->
      <el-card class="sync-status-card" shadow="never" style="margin-top: 20px;">
        <template #header>
          <span>同步状态</span>
        </template>
        <el-table :data="syncStatusList" stripe>
          <el-table-column prop="source_name" label="数据源" width="200" align="center" />
          <el-table-column prop="source_type" label="类型" width="120" align="center" />
          <el-table-column prop="status" label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.status === 'completed' ? 'success' : 'info'" size="small">
                {{ row.status === 'completed' ? '已完成' : '待同步' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="last_sync" label="最后同步时间" width="180" align="center">
            <template #default="{ row }">
              {{ row.last_sync ? formatDateTime(row.last_sync) : '-' }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Setting, Refresh, RefreshRight } from '@element-plus/icons-vue'
import axios from 'axios'

const loading = ref(false)
const syncingAll = ref(false)
const status = ref(null)
const syncStatusList = ref([])

// 加载状态
const loadStatus = async () => {
  loading.value = true
  try {
    const response = await axios.get('/api/v1/cocoindex/status')
    if (response.data.code === 200) {
      status.value = response.data.data
      
      // 加载同步状态
      const syncResponse = await axios.get('/api/v1/cocoindex/sync-status')
      if (syncResponse.data.code === 200) {
        const syncData = syncResponse.data.data
        if (syncData.tasks) {
          syncStatusList.value = Object.entries(syncData.tasks).map(([key, task]) => ({
            source_name: key.split(':')[1],
            source_type: key.split(':')[0],
            status: task.status,
            last_sync: task.last_sync
          }))
        }
      }
    }
  } catch (error) {
    console.error('加载状态失败:', error)
    ElMessage.error('加载状态失败')
  } finally {
    loading.value = false
  }
}

// 同步所有数据源
const handleSyncAll = async () => {
  syncingAll.value = true
  try {
    const response = await axios.post('/api/v1/cocoindex/sync-all')
    if (response.data.code === 200) {
      ElMessage.success(`同步完成：${response.data.data.success}/${response.data.data.total} 个数据源同步成功`)
      loadStatus()
    }
  } catch (error) {
    console.error('同步失败:', error)
    ElMessage.error('同步失败')
  } finally {
    syncingAll.value = false
  }
}

// 格式化日期时间
const formatDateTime = (dateTime) => {
  if (!dateTime) return '-'
  return new Date(dateTime).toLocaleString('zh-CN')
}

onMounted(() => {
  loadStatus()
})
</script>

<style scoped>
.cocoindex-config {
  padding: 20px;
}

.main-card {
  min-height: calc(100vh - 100px);
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
}

.title-text {
  font-size: 18px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.stat-item {
  text-align: center;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 10px;
}

.stat-value {
  font-size: 32px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
}

.stat-detail {
  margin-top: 10px;
}

.sync-status-card {
  margin-top: 20px;
}
</style>

