import request from '@/utils/request'

// 获取AI模型列表
export function getAIModels() {
  return request({
    url: '/api/v1/ai-models',
    method: 'get'
  })
}

// 获取AI模型详情
export function getAIModel(id) {
  return request({
    url: `/api/v1/ai-models/${id}`,
    method: 'get'
  })
}

// 创建AI模型配置
export function createAIModel(data) {
  return request({
    url: '/api/v1/ai-models',
    method: 'post',
    data
  })
}

// 更新AI模型配置
export function updateAIModel(id, data) {
  return request({
    url: `/api/v1/ai-models/${id}`,
    method: 'put',
    data
  })
}

// 删除AI模型配置
export function deleteAIModel(id) {
  return request({
    url: `/api/v1/ai-models/${id}`,
    method: 'delete'
  })
}

// 设置默认模型
export function setDefaultModel(id) {
  return request({
    url: `/api/v1/ai-models/${id}/set-default`,
    method: 'post'
  })
}

// 测试模型连接
export function testModelConnection(id) {
  return request({
    url: `/api/v1/ai-models/${id}/test`,
    method: 'post'
  })
}

// 获取支持的提供商列表
export function getProviders() {
  return request({
    url: '/api/v1/ai-models/providers/list',
    method: 'get'
  })
}
