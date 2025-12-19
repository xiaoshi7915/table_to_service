import request from '@/utils/request'

export default {
  // 获取对话列表
  getSessions(params = {}) {
    return request({
      url: '/api/v1/chat/sessions',
      method: 'get',
      params
    })
  },
  
  // 创建对话
  createSession(data) {
    return request({
      url: '/api/v1/chat/sessions',
      method: 'post',
      data
    })
  },
  
  // 获取对话详情
  getSession(sessionId) {
    return request({
      url: `/api/v1/chat/sessions/${sessionId}`,
      method: 'get'
    })
  },
  
  // 删除对话
  deleteSession(sessionId) {
    return request({
      url: `/api/v1/chat/sessions/${sessionId}`,
      method: 'delete'
    })
  },
  
  // 获取消息列表
  getMessages(sessionId) {
    return request({
      url: `/api/v1/chat/sessions/${sessionId}/messages`,
      method: 'get'
    })
  },
  
  // 发送消息
  sendMessage(sessionId, data) {
    return request({
      url: `/api/v1/chat/sessions/${sessionId}/messages`,
      method: 'post',
      data
    })
  },
  
  // 获取推荐问题
  getRecommendedQuestions(sessionId) {
    return request({
      url: `/api/v1/chat/sessions/${sessionId}/recommended-questions`,
      method: 'get'
    })
  },
  
  // 切换图表类型
  changeChartType(messageId, chartType) {
    return request({
      url: `/api/v1/chat/messages/${messageId}/chart-type`,
      method: 'put',
      data: { chart_type: chartType }
    })
  },
  
  // 导出数据
  exportData(messageId, format = 'excel') {
    return request({
      url: `/api/v1/chat/messages/${messageId}/export`,
      method: 'get',
      params: { format },
      responseType: 'blob'
    })
  },
  
  // 更新会话（重命名）
  updateSession(sessionId, data) {
    return request({
      url: `/api/v1/chat/sessions/${sessionId}`,
      method: 'put',
      data
    })
  },
  
  // 批量删除会话
  batchDeleteSessions(sessionIds) {
    return request({
      url: '/api/v1/chat/sessions/batch-delete',
      method: 'post',
      data: { session_ids: sessionIds }
    })
  }
}

