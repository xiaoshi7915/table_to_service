/**
 * 术语库API
 */
import api from './index'

// 获取术语列表
export const getTerminologies = (params) => {
  return api.get('/terminologies', { params })
}

// 获取术语详情
export const getTerminology = (id) => {
  return api.get(`/terminologies/${id}`)
}

// 创建术语
export const createTerminology = (data) => {
  return api.post('/terminologies', data)
}

// 更新术语
export const updateTerminology = (id, data) => {
  return api.put(`/terminologies/${id}`, data)
}

// 删除术语
export const deleteTerminology = (id) => {
  return api.delete(`/terminologies/${id}`)
}

// 批量创建术语
export const batchCreateTerminologies = (data) => {
  return api.post('/terminologies/batch', data)
}

// 获取分类列表
export const getCategories = () => {
  return api.get('/terminologies/categories/list')
}


