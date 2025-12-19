/**
 * 自定义提示词API
 */
import api from './index'

// 获取提示词列表
export const getPrompts = (params) => {
  return api.get('/prompts', { params })
}

// 获取提示词详情
export const getPrompt = (id) => {
  return api.get(`/prompts/${id}`)
}

// 创建提示词
export const createPrompt = (data) => {
  return api.post('/prompts', data)
}

// 更新提示词
export const updatePrompt = (id, data) => {
  return api.put(`/prompts/${id}`, data)
}

// 删除提示词
export const deletePrompt = (id) => {
  return api.delete(`/prompts/${id}`)
}

// 获取提示词类型列表
export const getPromptTypes = () => {
  return api.get('/prompts/types/list')
}


