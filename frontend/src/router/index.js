import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue')
      },
      {
        path: 'database-config',
        name: 'DatabaseConfig',
        component: () => import('@/views/DatabaseConfig.vue')
      },
      {
        path: 'interface-list',
        name: 'InterfaceList',
        component: () => import('@/views/InterfaceList.vue')
      },
      {
        path: 'interface-config',
        name: 'InterfaceConfig',
        component: () => import('@/views/InterfaceConfig.vue')
      },
      {
        path: 'api-docs',
        name: 'ApiDocs',
        component: () => import(/* webpackChunkName: "api-docs" */ '@/views/ApiDocs.vue')
      },
      {
        path: 'ai-model-config',
        name: 'AIModelConfig',
        component: () => import('@/views/AIModelConfig.vue')
      },
      {
        path: 'terminology-config',
        name: 'TerminologyConfig',
        component: () => import('@/views/TerminologyConfig.vue')
      },
      {
        path: 'sql-example-config',
        name: 'SQLExampleConfig',
        component: () => import('@/views/SQLExampleConfig.vue')
      },
      {
        path: 'prompt-config',
        name: 'PromptConfig',
        component: () => import('@/views/PromptConfig.vue')
      },
      {
        path: 'knowledge-config',
        name: 'KnowledgeConfig',
        component: () => import('@/views/KnowledgeConfig.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    next('/')
  } else {
    next()
  }
})

export default router

