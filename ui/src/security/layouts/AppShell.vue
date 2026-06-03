<template>
  <div>
    <AppHeader />
    <div class="page-shell">
      <SidebarNav />
      <main class="shell-main">
        <RouterView v-slot="{ Component }">
          <component :is="Component" />
        </RouterView>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import SidebarNav from '@/security/components/SidebarNav.vue';
import AppHeader from '@/security/components/AppHeader.vue';
</script>
