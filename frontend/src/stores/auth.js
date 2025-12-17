import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)

  // 使用computed确保响应式更新
  const isAuthenticated = computed(() => !!token.value)

  const login = async (username, password) => {
    try {
      const response = await api.post('/auth/login', {
        username,
        password
      })
      
      token.value = response.data.access_token
      localStorage.setItem('token', token.value)
      
      // 获取用户信息（如果失败不影响登录）
      await fetchUserInfo()
      
      return { success: true }
    } catch (error) {
      return {
        success: false,
        message: error.response?.data?.detail || '登录失败'
      }
    }
  }

  const fetchUserInfo = async () => {
    try {
      const response = await api.get('/auth/me')
      user.value = response.data.data
      return true
    } catch (error) {
      console.warn('获取用户信息失败:', error)
      // 不抛出错误，避免影响登录流程
      return false
    }
  }

  const logout = () => {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  return {
    token,
    user,
    isAuthenticated,
    login,
    logout,
    fetchUserInfo
  }
})
