<template>
  <el-container class="layout-container">
    <el-aside width="250px" class="sidebar">
      <div class="logo">
        <h2>智能问数+服务</h2>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        :default-openeds="['sqlbot']"
        router
        class="sidebar-menu"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataBoard /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>

        <el-menu-item index="/interface-config">
          <el-icon><Tools /></el-icon>
          <span>表转服务</span>
        </el-menu-item>

        <el-menu-item index="/chat">
            <el-icon><ChatLineRound /></el-icon>
            <span>智能问数</span>
        </el-menu-item>

        <el-menu-item index="/dashboard-list">
            <el-icon><DataBoard /></el-icon>
            <span>仪表板</span>
        </el-menu-item>
        
        <el-menu-item index="/database-config">
          <el-icon><Connection /></el-icon>
          <span>数据源配置</span>
        </el-menu-item>
        
        <el-sub-menu index="tableService">
          <template #title>
            <el-icon><Tools /></el-icon>
            <span>表转服务</span>
          </template>
        <el-menu-item index="/interface-list">
          <el-icon><List /></el-icon>
          <span>接口清单</span>
        </el-menu-item>
        
        
        <el-menu-item index="/api-docs">
          <el-icon><Document /></el-icon>
          <span>API文档</span>
        </el-menu-item>
      </el-sub-menu>
        
        <el-sub-menu index="sqlbot">
          <template #title>
            <el-icon><ChatLineRound /></el-icon>
            <span>智能问数</span>
          </template>
          <el-menu-item index="/ai-model-config">
            <el-icon><Cpu /></el-icon>
            <span>AI模型配置</span>
          </el-menu-item>
          <el-menu-item index="/terminology-config">
            <el-icon><Collection /></el-icon>
            <span>术语配置</span>
          </el-menu-item>
          <el-menu-item index="/sql-example-config">
            <el-icon><DocumentCopy /></el-icon>
            <span>SQL示例配置</span>
          </el-menu-item>
          <el-menu-item index="/prompt-config">
            <el-icon><EditPen /></el-icon>
            <span>自定义提示词</span>
          </el-menu-item>
          <el-menu-item index="/knowledge-config">
            <el-icon><Reading /></el-icon>
            <span>业务知识库</span>
          </el-menu-item>
          <el-menu-item index="/chat-history">
            <el-icon><List /></el-icon>
            <span>历史对话</span>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>
    
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <h3>{{ pageTitle }}</h3>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-icon><User /></el-icon>
              {{ authStore.user?.username || '用户' }}
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <el-main class="main-content">
        <router-view />
      </el-main>
      
      <el-footer class="footer">
        <div class="footer-content">
          Copyright © 2025 mr stone的个人网站
        </div>
      </el-footer>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import { 
  DataBoard, 
  Connection, 
  List, 
  Tools, 
  Document, 
  User, 
  ArrowDown,
  ChatLineRound,
  Cpu,
  Collection,
  DocumentCopy,
  EditPen,
  Reading
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const activeMenu = computed(() => route.path)

const pageTitle = computed(() => {
  const titles = {
    '/dashboard': '仪表盘',
    '/database-config': '数据源配置',
    '/interface-list': '接口清单',
    '/interface-config': '数据表转接口',
    '/api-docs': 'API文档',
    '/ai-model-config': 'AI模型配置',
    '/terminology-config': '术语配置',
    '/sql-example-config': 'SQL示例配置',
    '/prompt-config': '自定义提示词',
    '/knowledge-config': '业务知识库'
  }
  return titles[route.path] || '智能问数'
})

const handleCommand = (command) => {
  if (command === 'logout') {
    authStore.logout()
    ElMessage.success('已退出登录')
    router.push('/login')
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.sidebar {
  background: linear-gradient(180deg, #2c3e50 0%, #34495e 100%);
  overflow-y: auto;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
}

.logo {
  height: 70px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  border-bottom: 1px solid rgba(255, 255, 255, 0.15);
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
  overflow: hidden;
}

.logo::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
  animation: shimmer 3s infinite;
}

@keyframes shimmer {
  0% { transform: translate(-50%, -50%) rotate(0deg); }
  100% { transform: translate(-50%, -50%) rotate(360deg); }
}

.logo h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 1px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  position: relative;
  z-index: 1;
}

.sidebar-menu {
  border-right: none;
  background-color: transparent;
  padding: 10px 0;
}

.sidebar-menu :deep(.el-menu-item) {
  color: rgba(255, 255, 255, 0.75);
  margin: 4px 12px;
  border-radius: 8px;
  transition: all 0.3s;
  height: 48px;
  line-height: 48px;
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%);
  color: white;
  transform: translateX(4px);
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  font-weight: 600;
}

.sidebar-menu :deep(.el-menu-item .el-icon) {
  font-size: 18px;
  margin-right: 8px;
}

/* 子菜单样式 */
.sidebar-menu :deep(.el-sub-menu) {
  margin: 4px 12px;
}

.sidebar-menu :deep(.el-sub-menu__title) {
  color: rgba(255, 255, 255, 0.75);
  border-radius: 8px;
  transition: all 0.3s;
  height: 48px;
  line-height: 48px;
  padding: 0 20px;
}

.sidebar-menu :deep(.el-sub-menu__title:hover) {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%);
  color: white;
  transform: translateX(4px);
}

.sidebar-menu :deep(.el-sub-menu.is-opened > .el-sub-menu__title) {
  color: white;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.3) 0%, rgba(118, 75, 162, 0.3) 100%);
}

.sidebar-menu :deep(.el-sub-menu .el-icon) {
  font-size: 18px;
  margin-right: 8px;
}

/* 子菜单项样式 - 保持与主菜单一致的深色背景 */
.sidebar-menu :deep(.el-sub-menu .el-menu) {
  background-color: transparent !important;
  border-radius: 8px;
  margin-top: 4px;
  padding: 4px 0;
}

.sidebar-menu :deep(.el-sub-menu .el-menu-item) {
  color: rgba(255, 255, 255, 0.85);
  margin: 2px 8px;
  padding-left: 40px !important;
  border-radius: 6px;
  height: 44px;
  line-height: 44px;
  background-color: transparent !important;
}

.sidebar-menu :deep(.el-sub-menu .el-menu-item:hover) {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.3) 0%, rgba(118, 75, 162, 0.3) 100%) !important;
  color: white;
  transform: translateX(4px);
}

.sidebar-menu :deep(.el-sub-menu .el-menu-item.is-active) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  color: white;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  font-weight: 600;
}

.sidebar-menu :deep(.el-sub-menu .el-menu-item .el-icon) {
  font-size: 16px;
  margin-right: 8px;
}

.header {
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  height: 70px;
}

.header-left h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
  color: #606266;
  font-size: 14px;
  padding: 8px 16px;
  border-radius: 8px;
  transition: all 0.3s;
  font-weight: 500;
}

.user-info:hover {
  background: #f5f7fa;
  color: #667eea;
}

.user-info .el-icon {
  margin-right: 8px;
  font-size: 18px;
}

.main-content {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  padding: 24px;
  overflow-y: auto;
  min-height: calc(100vh - 70px - 60px);
}

.footer {
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
  border-top: 1px solid #e4e7ed;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 24px;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.05);
}

.footer-content {
  color: #909399;
  font-size: 14px;
  text-align: center;
}
</style>

