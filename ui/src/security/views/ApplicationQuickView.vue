<template>
  <div class="card" style="max-width: 720px;">
    <h3>快捷申请</h3>
    <p class="muted" style="margin-top: 6px;">输入名称匹配目标，选择后提交申请。</p>

    <div style="margin-top: 16px; display: grid; gap: 12px;">
      <label class="field">
        <span>目标类型</span>
        <select v-model.number="form.targetType" class="input">
          <option :value="1">部门</option>
          <option :value="2">项目</option>
          <option :value="3">小组</option>
        </select>
      </label>

      <label v-if="form.targetType === 3" class="field">
        <span>所属项目</span>
        <select v-model.number="selectedProjectId" class="input">
          <option :value="0">请选择项目</option>
          <option v-for="project in projects" :key="project.id" :value="project.id">
            {{ project.name }}
          </option>
        </select>
      </label>

      <label class="field">
        <span>目标名称</span>
        <input
          v-model="search"
          class="input"
          placeholder="输入名称搜索"
          @input="form.targetId = 0"
        />
      </label>

      <div v-if="search && filteredTargets.length" class="search-results">
        <button
          v-for="item in filteredTargets"
          :key="item.id"
          type="button"
          class="search-item"
          @click="selectTarget(item)"
        >
          <span>{{ item.name }}</span>
          <span class="pill">ID {{ item.id }}</span>
        </button>
      </div>

      <div v-else-if="search" class="muted" style="font-size: 13px;">未找到匹配结果</div>

      <div v-if="form.targetId" class="pill" style="width: fit-content;">
        已选择：{{ selectedLabel }}（ID {{ form.targetId }}）
      </div>

      <label class="field">
        <span>申请理由</span>
        <textarea v-model="form.reason" class="input" rows="4" placeholder="可选" />
      </label>
      <button class="button" @click="submit">提交申请</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import type { Department, Group, Project } from '@/security/types/models';
import { createApplication, fetchDepartments, fetchGroups, fetchProjects } from '@/security/api/endpoints';
import { useNotifyStore } from '@/security/stores/notify';

const notify = useNotifyStore();

const form = reactive({
  targetType: 1,
  targetId: 0,
  reason: ''
});

const search = ref('');
const selectedLabel = ref('');
const selectedProjectId = ref(0);

const departments = ref<Department[]>([]);
const projects = ref<Project[]>([]);
const groups = ref<Group[]>([]);

const loadDepartments = async () => {
  try {
    departments.value = (await fetchDepartments()) as Department[];
  } catch {
    departments.value = [];
  }
};

const loadProjects = async () => {
  try {
    projects.value = (await fetchProjects()) as Project[];
  } catch {
    projects.value = [];
  }
};

const loadGroups = async () => {
  if (!selectedProjectId.value) {
    groups.value = [];
    return;
  }
  try {
    groups.value = (await fetchGroups(selectedProjectId.value)) as Group[];
  } catch {
    groups.value = [];
  }
};

const sourceList = computed(() => {
  if (form.targetType === 1) return departments.value;
  if (form.targetType === 2) return projects.value;
  return groups.value;
});

const filteredTargets = computed(() => {
  const query = search.value.trim().toLowerCase();
  if (!query) return [];
  return sourceList.value.filter((item: any) => (item.name || '').toLowerCase().includes(query));
});

const selectTarget = (item: { id: number; name: string }) => {
  form.targetId = item.id;
  selectedLabel.value = item.name;
  search.value = item.name;
};

const submit = async () => {
  if (!form.targetId) {
    notify.push('请选择目标名称', 'error');
    return;
  }
  try {
    await createApplication({
      targetType: form.targetType,
      targetId: form.targetId,
      reason: form.reason
    });
    notify.push('申请已提交', 'success');
    form.targetId = 0;
    form.reason = '';
    search.value = '';
    selectedLabel.value = '';
  } catch (error: any) {
    notify.push(error?.message || '申请提交失败', 'error');
  }
};

watch(
  () => form.targetType,
  async (type) => {
    form.targetId = 0;
    search.value = '';
    selectedLabel.value = '';
    if (type === 1) {
      await loadDepartments();
    } else if (type === 2) {
      await loadProjects();
    } else {
      await loadProjects();
      await loadGroups();
    }
  },
  { immediate: true }
);

watch(selectedProjectId, async () => {
  if (form.targetType === 3) {
    form.targetId = 0;
    search.value = '';
    selectedLabel.value = '';
    await loadGroups();
  }
});

onMounted(async () => {
  await loadDepartments();
});
</script>

<style scoped>
.search-results {
  display: grid;
  gap: 8px;
  max-height: 200px;
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 8px;
  background: #fff;
}

.search-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  cursor: pointer;
}

.search-item:hover {
  background: #eef2ff;
}
</style>
