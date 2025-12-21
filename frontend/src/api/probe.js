import request from '@/utils/request'

export default {
  // 获取任务列表
  getTasks(params = {}) {
    return request({
      url: '/api/v1/probe-tasks',
      method: 'get',
      params
    })
  },
  
  // 获取任务详情
  getTask(id) {
    return request({
      url: `/api/v1/probe-tasks/${id}`,
      method: 'get'
    })
  },
  
  // 获取库级探查结果
  getDatabaseResult(taskId) {
    return request({
      url: `/api/v1/probe-results/task/${taskId}/database`,
      method: 'get'
    })
  },
  
  // 根据数据源配置ID获取或创建探查任务
  getTaskByDatabaseConfig(databaseConfigId, probeMode = null, probeLevel = null) {
    const params = {}
    if (probeMode) params.probe_mode = probeMode
    if (probeLevel) params.probe_level = probeLevel
    return request({
      url: `/api/v1/probe-tasks/by-database-config/${databaseConfigId}`,
      method: 'get',
      params
    })
  },
  
  // 创建任务
  createTask(data) {
    return request({
      url: '/api/v1/probe-tasks',
      method: 'post',
      data
    })
  },
  
  // 更新任务
  updateTask(id, data) {
    return request({
      url: `/api/v1/probe-tasks/${id}`,
      method: 'put',
      data
    })
  },
  
  // 删除任务
  deleteTask(id) {
    return request({
      url: `/api/v1/probe-tasks/${id}`,
      method: 'delete'
    })
  },
  
  // 启动任务
  startTask(id, data = {}) {
    return request({
      url: `/api/v1/probe-tasks/${id}/start`,
      method: 'post',
      data,
      timeout: 60000 // 60秒超时，给启动任务足够的时间
    })
  },
  
  // 停止任务
  stopTask(id) {
    return request({
      url: `/api/v1/probe-tasks/${id}/stop`,
      method: 'post'
    })
  },
  
  // 批量启动任务
  batchStartTasks(ids, probeMode, schedulingType) {
    return request({
      url: '/api/v1/probe-tasks/batch-start',
      method: 'post',
      data: {
        task_ids: ids,
        probe_mode: probeMode,
        scheduling_type: schedulingType
      }
    })
  },
  
  // 获取库级结果
  getDatabaseResult(taskId) {
    return request({
      url: `/api/v1/probe-results/task/${taskId}/database`,
      method: 'get'
    })
  },
  
  // 获取表级结果列表
  getTableResults(taskId, params = {}) {
    return request({
      url: `/api/v1/probe-results/task/${taskId}/tables`,
      method: 'get',
      params
    })
  },
  
  // 获取表级结果详情
  getTableResult(taskId, tableName) {
    return request({
      url: `/api/v1/probe-results/task/${taskId}/tables/${tableName}`,
      method: 'get'
    })
  },
  
  // 获取列级结果
  getColumnResults(taskId, tableName) {
    return request({
      url: `/api/v1/probe-results/task/${taskId}/tables/${tableName}/columns`,
      method: 'get'
    })
  },
  
  // 获取列详情
  getColumnResult(taskId, columnId) {
    return request({
      url: `/api/v1/probe-results/task/${taskId}/columns/${columnId}`,
      method: 'get'
    })
  },
  
  // 屏蔽/取消屏蔽表
  hideTable(taskId, tableName, isHidden) {
    return request({
      url: `/api/v1/probe-results/task/${taskId}/tables/${tableName}/hide`,
      method: 'put',
      params: { is_hidden: isHidden }
    })
  },
  
  // 导出结果
  exportResults(taskId, format = 'excel') {
    if (format === 'json') {
      // JSON格式返回JSON数据
      return request({
        url: `/api/v1/probe-results/task/${taskId}/export`,
        method: 'get',
        params: { format }
      })
    } else {
      return request({
        url: `/api/v1/probe-results/task/${taskId}/export`,
        method: 'get',
        params: { format },
        responseType: 'blob'
      })
    }
  },
  
  // 导入到知识库
  importToKnowledge(taskId) {
    return request({
      url: `/api/v1/probe-results/task/${taskId}/import-to-knowledge`,
      method: 'post'
    })
  }
}

