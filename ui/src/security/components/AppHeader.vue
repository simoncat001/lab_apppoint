<template>
  <header class="app-bar">
    <div class="toolbar">
      <div class="title-group">
        <h1>{{ title }}</h1>
        <span v-if="subtitle" class="subtitle">{{ subtitle }}</span>
      </div>
      <div class="spacer"></div>
      <div class="user-section">
        <span class="user-chip">{{ userLabel }}</span>
        <button class="button ghost" style="margin-left: 12px;" @click="handleLogout">退出</button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useStaffAuthStore } from '@/security/stores/auth';
import { useNotifyStore } from '@/security/stores/notify';

const route = useRoute();
const router = useRouter();
const auth = useStaffAuthStore();
const notify = useNotifyStore();

const title = computed(() => (route.meta.title as string) || '控制台');
const subtitle = computed(() => (route.meta.subtitle as string) || '');
const userLabel = computed(() => auth.user?.name || auth.user?.username || '未登录');

const handleLogout = async () => {
  await auth.logout();
  notify.push('已退出登录', 'success');
  router.push('/security/login');
};
</script>
