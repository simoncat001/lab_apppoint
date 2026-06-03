<template>
  <el-container class="layout-container">
    <el-aside class="layout-sidebar" :width="sidebarWidth">
      <Sidebar />
    </el-aside>
    
    <el-container class="layout-main-shell" :style="{ marginLeft: sidebarWidth }">
      <el-header height="60px">
        <Header />
      </el-header>
      
      <el-main>
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'

const appStore = useAppStore()

const sidebarWidth = computed(() => {
  return appStore.sidebarCollapsed ? '64px' : '200px'
})
</script>

<style scoped>
.layout-container {
  height: 100vh;
  min-height: 100vh;
  overflow: hidden;
}

.layout-sidebar {
  background-color: #304156;
  transition: width 0.3s;
  overflow-x: hidden;
  position: fixed;
  top: 0;
  bottom: 0;
  left: 0;
  height: 100vh;
  height: 100dvh;
  min-height: 100vh;
  z-index: 20;
}

.layout-main-shell {
  min-width: 0;
  width: 100%;
  height: 100vh;
  min-height: 100vh;
  transition: margin-left 0.3s;
}

.el-header {
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  display: flex;
  align-items: center;
  padding: 0 20px;
}

.el-main {
  background-color: #f0f2f5;
  overflow-y: auto;
  height: calc(100vh - 60px);
}
</style>
