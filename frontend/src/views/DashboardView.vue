<template>
  <div class="dashboard-view-container">
    <el-card class="main-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon class="title-icon"><DataBoard /></el-icon>
            <span class="title-text">{{ dashboard.name || '仪表板' }}</span>
          </div>
          <div class="header-actions">
            <el-button @click="goBack">
              返回
            </el-button>
            <el-button type="primary" @click="goToEdit">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
          </div>
        </div>
      </template>
      
      <div v-loading="loading" class="dashboard-content">
        <div v-if="widgets.length === 0" class="empty-state">
          <el-empty description="暂无组件，请先编辑仪表板添加组件" />
        </div>
        
        <div v-else class="widgets-grid">
          <el-card
            v-for="widget in widgets"
            :key="widget.id"
            class="widget-card"
            shadow="hover"
          >
            <template #header>
              <div class="widget-header">
                <h4>{{ widget.title }}</h4>
                <el-tag size="small">{{ widget.widget_type }}</el-tag>
              </div>
            </template>
            
            <div class="widget-content" :style="{ height: widget.height + 'px' }">
              <div v-if="widget.widget_type === 'chart'" class="chart-container">
                <div
                  ref="chartRefs"
                  :id="`chart-${widget.id}`"
                  :style="{ width: '100%', height: '100%' }"
                ></div>
              </div>
              <div v-else-if="widget.widget_type === 'table'" class="table-container">
                <el-table
                  :data="widget.tableData || []"
                  style="width: 100%"
                  max-height="300"
                >
                  <el-table-column
                    v-for="(col, idx) in widget.tableColumns || []"
                    :key="idx"
                    :prop="col"
                    :label="col"
                  />
                </el-table>
              </div>
            </div>
          </el-card>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  DataBoard,
  Edit
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import dashboardApi from '@/api/dashboards'

const route = useRoute()
const router = useRouter()

const dashboard = ref({})
const widgets = ref([])
const loading = ref(false)
const chartRefs = ref({})

// 加载仪表板详情
const loadDashboard = async () => {
  loading.value = true
  try {
    const dashboardId = parseInt(route.params.id)
    const response = await dashboardApi.getDashboard(dashboardId)
    
    if (response.code === 200 || response.success) {
      dashboard.value = response.data || {}
      widgets.value = response.data?.widgets || []
      
      // 处理组件数据（解析config和tableData）
      widgets.value = widgets.value.map(widget => {
        if (widget.config) {
          // 如果是字符串，解析为对象
          if (typeof widget.config === 'string') {
            try {
              widget.config = JSON.parse(widget.config)
            } catch (e) {
              console.error('解析widget config失败:', e)
              widget.config = {}
            }
          }
          
          // 如果是表格类型，提取数据
          if (widget.widget_type === 'table' && widget.config.data) {
            widget.tableData = Array.isArray(widget.config.data) ? widget.config.data : []
            
            // 处理列名：确保是数组
            if (widget.config.columns) {
              if (Array.isArray(widget.config.columns)) {
                widget.tableColumns = widget.config.columns
              } else if (typeof widget.config.columns === 'string') {
                // 如果是字符串，尝试解析为数组，或使用单个元素数组
                try {
                  widget.tableColumns = JSON.parse(widget.config.columns)
                  if (!Array.isArray(widget.tableColumns)) {
                    widget.tableColumns = [widget.config.columns]
                  }
                } catch (e) {
                  widget.tableColumns = [widget.config.columns]
                }
              } else {
                widget.tableColumns = []
              }
            } else if (widget.tableData.length > 0 && typeof widget.tableData[0] === 'object') {
              // 从数据第一行提取列名
              widget.tableColumns = Object.keys(widget.tableData[0])
            } else {
              widget.tableColumns = []
            }
          }
        }
        return widget
      })
      
      // 渲染图表
      await nextTick()
      renderCharts()
    } else {
      ElMessage.error(response.message || '加载仪表板失败')
    }
  } catch (error) {
    console.error('加载仪表板失败:', error)
    ElMessage.error('加载仪表板失败：' + (error.response?.data?.detail || error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 渲染图表
const renderCharts = () => {
  widgets.value.forEach((widget) => {
    if (widget.widget_type === 'chart' && widget.config) {
      const chartId = `chart-${widget.id}`
      const chartDom = document.getElementById(chartId)
      if (chartDom) {
        try {
          // 确保config是对象
          let chartConfig = widget.config
          if (typeof chartConfig === 'string') {
            try {
              chartConfig = JSON.parse(chartConfig)
            } catch (e) {
              console.error('解析图表配置失败:', e)
              return
            }
          }
          
          // 验证配置对象
          if (typeof chartConfig !== 'object' || chartConfig === null) {
            console.error('图表配置格式错误:', chartConfig)
            return
          }
          
          const chart = echarts.init(chartDom)
          chart.setOption(chartConfig)
          chartRefs.value[widget.id] = chart
        } catch (error) {
          console.error(`渲染图表失败 (widget ${widget.id}):`, error)
        }
      }
    }
  })
}

// 返回
const goBack = () => {
  router.push('/dashboard-list')
}

// 编辑
const goToEdit = () => {
  router.push(`/dashboard-edit/${route.params.id}`)
}

onMounted(() => {
  loadDashboard()
})
</script>

<style scoped>
.dashboard-view-container {
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

.dashboard-content {
  min-height: 400px;
}

.empty-state {
  padding: 100px 0;
}

.widgets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}

.widget-card {
  min-height: 300px;
}

.widget-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.widget-header h4 {
  margin: 0;
  font-size: 16px;
}

.widget-content {
  padding: 10px 0;
}

.chart-container,
.table-container {
  width: 100%;
  height: 100%;
}
</style>

