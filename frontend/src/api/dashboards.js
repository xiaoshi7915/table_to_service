import request from '@/utils/request'

export default {
  // 获取仪表板列表
  getDashboards(params = {}) {
    return request({
      url: '/api/v1/dashboards',
      method: 'get',
      params
    })
  },
  
  // 创建仪表板
  createDashboard(data) {
    return request({
      url: '/api/v1/dashboards',
      method: 'post',
      data
    })
  },
  
  // 获取仪表板详情
  getDashboard(dashboardId) {
    return request({
      url: `/api/v1/dashboards/${dashboardId}`,
      method: 'get'
    })
  },
  
  // 更新仪表板
  updateDashboard(dashboardId, data) {
    return request({
      url: `/api/v1/dashboards/${dashboardId}`,
      method: 'put',
      data
    })
  },
  
  // 删除仪表板
  deleteDashboard(dashboardId) {
    return request({
      url: `/api/v1/dashboards/${dashboardId}`,
      method: 'delete'
    })
  },
  
  // 添加组件
  createWidget(dashboardId, data) {
    return request({
      url: `/api/v1/dashboards/${dashboardId}/widgets`,
      method: 'post',
      data
    })
  },
  
  // 更新组件
  updateWidget(dashboardId, widgetId, data) {
    return request({
      url: `/api/v1/dashboards/${dashboardId}/widgets/${widgetId}`,
      method: 'put',
      data
    })
  },
  
  // 删除组件
  deleteWidget(dashboardId, widgetId) {
    return request({
      url: `/api/v1/dashboards/${dashboardId}/widgets/${widgetId}`,
      method: 'delete'
    })
  }
}

