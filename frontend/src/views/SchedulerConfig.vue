<template>
  <div class="scheduler-config">
    <el-card class="main-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon class="title-icon"><Clock /></el-icon>
            <span class="title-text">定时任务配置</span>
          </div>
          <div class="header-actions">
            <el-button @click="loadJobs" :loading="loading" class="action-btn">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>
      
      <!-- 统计信息 -->
      <el-row :gutter="20" v-if="jobStats">
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="stat-item">
              <div class="stat-label">任务总数</div>
              <div class="stat-value">{{ jobStats.total || 0 }}</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="stat-item">
              <div class="stat-label">已启用</div>
              <div class="stat-value" style="color: #67C23A;">{{ jobStats.enabled || 0 }}</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="stat-item">
              <div class="stat-label">已禁用</div>
              <div class="stat-value" style="color: #909399;">{{ jobStats.disabled || 0 }}</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="stat-item">
              <div class="stat-label">调度器状态</div>
              <div class="stat-value">
                <el-tag :type="jobStats.scheduler_running ? 'success' : 'warning'" size="small">
                  {{ jobStats.scheduler_running ? '运行中' : '未运行' }}
                </el-tag>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
      
      <!-- 定时任务列表 -->
      <el-card class="jobs-card" shadow="never" style="margin-top: 20px;">
        <template #header>
          <span>定时任务列表</span>
        </template>
        <el-table :data="jobs" stripe v-loading="loading">
          <el-table-column prop="name" label="任务名称" width="200" align="center" />
          <el-table-column prop="source_type" label="数据源类型" width="120" align="center">
            <template #default="{ row }">
              <el-tag size="small">{{ row.source_type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="sync_enabled" label="启用状态" width="100" align="center">
            <template #default="{ row }">
              <el-switch
                v-model="row.sync_enabled"
                @change="handleToggleJob(row)"
                :loading="row.updating"
              />
            </template>
          </el-table-column>
          <el-table-column prop="sync_frequency" label="同步频率" width="150" align="center">
            <template #default="{ row }">
              <el-input-number
                v-model="row.sync_frequency"
                :min="60"
                :max="86400"
                :step="60"
                :disabled="!row.sync_enabled"
                @change="handleUpdateFrequency(row)"
                style="width: 100%"
              />
              <div style="font-size: 12px; color: #909399; margin-top: 5px;">
                {{ formatFrequency(row.sync_frequency) }}
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="last_sync_at" label="最后同步时间" width="180" align="center">
            <template #default="{ row }">
              {{ row.last_sync_at ? formatDateTime(row.last_sync_at) : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="next_run_time" label="下次执行时间" width="180" align="center">
            <template #default="{ row }">
              {{ row.next_run_time ? formatDateTime(row.next_run_time) : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.status === 'enabled' ? 'success' : 'info'" size="small">
                {{ row.status === 'enabled' ? '已启用' : '已禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" align="center" fixed="right">
            <template #default="{ row }">
              <el-button
                type="primary"
                size="small"
                @click="handleSyncNow(row)"
                :loading="row.syncing"
              >
                立即同步
              </el-button>
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
import { Clock, Refresh } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const jobs = ref([])
const jobStats = ref(null)

// 加载定时任务列表
const loadJobs = async () => {
  loading.value = true
  try {
    const response = await request.get('/cocoindex/scheduled-jobs')
    if (response.data.code === 200) {
      jobs.value = response.data.data.jobs || []
      jobStats.value = {
        total: response.data.data.total || 0,
        enabled: response.data.data.enabled || 0,
        disabled: response.data.data.disabled || 0,
        scheduler_running: response.data.data.scheduler_running || false
      }
    }
  } catch (error) {
    console.error('加载定时任务列表失败:', error)
    ElMessage.error('加载定时任务列表失败')
  } finally {
    loading.value = false
  }
}

// 切换任务启用状态
const handleToggleJob = async (row) => {
  row.updating = true
  try {
    const response = await request.put(`/cocoindex/scheduled-jobs/${row.id}`, null, {
      params: {
        sync_enabled: row.sync_enabled,
        sync_frequency: row.sync_frequency
      }
    })
    if (response.data.code === 200) {
      ElMessage.success('更新成功')
      row.status = row.sync_enabled ? 'enabled' : 'disabled'
      // 重新加载以获取最新的下次执行时间
      await loadJobs()
    }
  } catch (error) {
    console.error('更新任务状态失败:', error)
    ElMessage.error('更新任务状态失败')
    // 恢复原状态
    row.sync_enabled = !row.sync_enabled
  } finally {
    row.updating = false
  }
}

// 更新同步频率
const handleUpdateFrequency = async (row) => {
  if (!row.sync_frequency || row.sync_frequency < 60) {
    ElMessage.warning('同步频率不能小于60秒')
    return
  }
  
  row.updating = true
  try {
    const response = await request.put(`/cocoindex/scheduled-jobs/${row.id}`, null, {
      params: {
        sync_enabled: row.sync_enabled,
        sync_frequency: row.sync_frequency
      }
    })
    if (response.data.code === 200) {
      ElMessage.success('更新成功')
      // 重新加载以获取最新的下次执行时间
      await loadJobs()
    }
  } catch (error) {
    console.error('更新同步频率失败:', error)
    ElMessage.error('更新同步频率失败')
  } finally {
    row.updating = false
  }
}

// 立即同步
const handleSyncNow = async (row) => {
  row.syncing = true
  try {
    const response = await request.post('/cocoindex/sync-all')
    if (response.data.code === 200) {
      ElMessage.success('同步任务已启动')
      // 重新加载以获取最新的同步时间
      setTimeout(() => {
        loadJobs()
      }, 2000)
    }
  } catch (error) {
    console.error('启动同步失败:', error)
    ElMessage.error('启动同步失败')
  } finally {
    row.syncing = false
  }
}

// 格式化频率
const formatFrequency = (seconds) => {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}小时`
  return `${Math.floor(seconds / 86400)}天`
}

// 格式化日期时间
const formatDateTime = (dateTime) => {
  if (!dateTime) return '-'
  return new Date(dateTime).toLocaleString('zh-CN')
}

onMounted(() => {
  loadJobs()
})
</script>

<style scoped>
.scheduler-config {
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

.jobs-card {
  margin-top: 20px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 5px;
}
</style>

