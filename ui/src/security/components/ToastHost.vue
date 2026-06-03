<template>
  <div class="toast-host" v-if="items.length">
    <div
      v-for="item in items"
      :key="item.id"
      class="toast"
      :class="item.tone"
      @click="remove(item.id)"
    >
      <span>{{ item.message }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia';
import { useNotifyStore } from '@/security/stores/notify';

const notify = useNotifyStore();
const { items } = storeToRefs(notify);
const { remove } = notify;
</script>
