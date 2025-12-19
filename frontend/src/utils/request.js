import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

// 创建 axios 实例
const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

// 请求拦截器：处理 URL 和认证
request.interceptors.request.use(
  (config) => {
    // 如果 URL 已经包含 /api/v1，移除 baseURL 避免重复
    if (config.url && config.url.startsWith('/api/v1')) {
      config.url = config.url.replace('/api/v1', '')
    }
    
    // 添加认证 token
    const authStore = useAuthStore()
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    // 处理响应数据
    if (response.data && typeof response.data === 'object') {
      // 如果响应数据有 code 字段，直接返回 data
      if ('code' in response.data) {
        return response.data
      }
      // 如果响应数据有 success 字段（ResponseModel格式），转换为统一格式
      if ('success' in response.data) {
        return {
          code: response.data.success ? 200 : 500,
          success: response.data.success,
          message: response.data.message || '',
          data: response.data.data,
          pagination: response.data.pagination
        }
      }
    }
    // 否则返回完整的 response 对象，保持与 axios 一致的行为
    return response
  },
  (error) => {
    // 401错误处理
    if (error.response?.status === 401) {
      const authStore = useAuthStore()
      const currentPath = window.location.pathname
      
      // 只有在已登录状态下且不在登录页才执行logout
      // 避免登录接口返回401时也触发退出
      if (authStore.isAuthenticated && currentPath !== '/login') {
        authStore.logout()
        ElMessage.error('登录已过期，请重新登录')
        window.location.href = '/login'
      }
      // 如果是登录接口返回401，不处理，让登录页面显示错误
    } else if (error.response?.data?.detail) {
      ElMessage.error(error.response.data.detail)
    } else if (!error.response) {
      // 网络错误等
      ElMessage.error('网络错误，请检查连接')
    } else {
      ElMessage.error('请求失败，请稍后重试')
    }
    return Promise.reject(error)
  }
)

export default request

