import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
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
api.interceptors.response.use(
  (response) => {
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

export default api
