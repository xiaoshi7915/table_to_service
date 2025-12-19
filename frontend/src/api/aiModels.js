/**
 * AI模型配置API
 */
import api from './index'

// 获取AI模型列表
export const getAIModels = () => {
  return api.get('/ai-models')
}

// 获取AI模型详情
export const getAIModel = (id) => {
  return api.get(`/ai-models/${id}`)
}

// 创建AI模型配置
export const createAIModel = (data) => {
  return api.post('/ai-models', data)
}

// 更新AI模型配置
export const updateAIModel = (id, data) => {
  return api.put(`/ai-models/${id}`, data)
}

// 删除AI模型配置
export const deleteAIModel = (id) => {
  return api.delete(`/ai-models/${id}`)
}

// 设置默认模型
export const setDefaultAIModel = (id) => {
  return api.post(`/ai-models/${id}/set-default`)
}

// 获取支持的提供商列表
export const getProviders = () => {
  return api.get('/ai-models/providers/list')
}


