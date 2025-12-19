/**
 * 业务知识库API
 */
import api from './index'

// 搜索知识库
export const searchKnowledge = (params) => {
  return api.get('/knowledge', { params })
}

// 获取知识条目详情
export const getKnowledge = (id) => {
  return api.get(`/knowledge/${id}`)
}

// 创建知识条目
export const createKnowledge = (data) => {
  return api.post('/knowledge', data)
}

// 更新知识条目
export const updateKnowledge = (id, data) => {
  return api.put(`/knowledge/${id}`, data)
}

// 删除知识条目
export const deleteKnowledge = (id) => {
  return api.delete(`/knowledge/${id}`)
}

// 获取分类列表
export const getKnowledgeCategories = () => {
  return api.get('/knowledge/categories/list')
}

// 获取标签列表
export const getKnowledgeTags = () => {
  return api.get('/knowledge/tags/list')
}


