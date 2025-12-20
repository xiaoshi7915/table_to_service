/**
 * SQL示例库API
 */
import api from './index'

// 获取SQL示例列表
export const getSQLExamples = (params) => {
  return api.get('/sql-examples', { params })
}

// 获取SQL示例详情
export const getSQLExample = (id) => {
  return api.get(`/sql-examples/${id}`)
}

// 创建SQL示例
export const createSQLExample = (data) => {
  return api.post('/sql-examples', data)
}

// 更新SQL示例
export const updateSQLExample = (id, data) => {
  return api.put(`/sql-examples/${id}`, data)
}

// 删除SQL示例
export const deleteSQLExample = (id) => {
  return api.delete(`/sql-examples/${id}`)
}

// 下载SQL示例导入模板
export const downloadSQLExampleTemplate = () => {
  return api.get('/sql-examples/template', {
    responseType: 'blob'
  })
}

// 批量导入SQL示例
export const batchCreateSQLExamples = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/sql-examples/batch', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}


