<template>
  <div class="card">
    <div style="display: flex; justify-content: space-between; align-items: center; gap: 12px;">
      <div>
        <h3>申请列表</h3>
        <p class="muted" style="margin-top: 6px;">仅显示你有权限查看的申请。</p>
      </div>
      <button class="button ghost" @click="loadApplications">刷新列表</button>
    </div>

    <div class="filter-row">
      <label class="field">
        <span>状态</span>
        <select v-model.number="filters.status" class="input">
          <option :value="-1">全部</option>
          <option :value="0">待审核</option>
          <option :value="1">已通过</option>
          <option :value="2">已拒绝</option>
        </select>
      </label>
      <label class="field">
        <span>目标类型</span>
        <select v-model.number="filters.targetType" class="input">
          <option :value="-1">全部</option>
          <option :value="1">部门</option>
          <option :value="2">项目</option>
          <option :value="3">小组</option>
        </select>
      </label>
      <label class="field">
        <span>目标 ID</span>
        <input v-model="filters.targetId" class="input" placeholder="可选" />
      </label>
      <div style="display: flex; align-items: flex-end; gap: 8px;">
        <button class="button" @click="loadApplications">应用筛选</button>
      </div>
    </div>

    <table class="table" style="margin-top: 16px;">
      <thead>
        <tr>
          <th>目标类型</th>
          <th>申请目标</th>
          <th>申请人</th>
          <th>状态</th>
          <th>提交时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in applications" :key="item.id">
          <td>{{ targetTypeLabel[item.targetType] }}</td>
          <td>{{ item.targetName || `#${item.targetId}` }}</td>
          <td>{{ item.applicantName || `#${item.userId}` }}</td>
          <td>{{ statusLabel[item.status] }}</td>
          <td>{{ formatDateTime(item.createdTime) }}</td>
          <td>
            <div style="display: flex; gap: 8px;">
              <button
                class="button secondary"
                v-if="item.status === 0"
                @click="approve(item.id)"
              >
                通过
              </button>
              <button
                class="button"
                style="background: #c94321;"
                v-if="item.status === 0"
                @click="openReject(item)"
              >
                拒绝
              </button>
            </div>
          </td>
        </tr>
        <tr v-if="!applications.length">
          <td colspan="6" style="text-align: center; padding: 20px;">暂无申请记录</td>
        </tr>
      </tbody>
    </table>
  </div>

  <ModalShell :open="showReject" title="拒绝申请" subtitle="填写拒绝原因" @close="showReject = false">
    <label class="field">
      <span>拒绝原因</span>
      <textarea v-model="rejectReason" class="input" rows="3" />
    </label>
    <button class="button" @click="submitReject">确认拒绝</button>
  </ModalShell>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import type { ApplicationRequest } from '@/security/types/models';
import { approveApplication, fetchApplications, rejectApplication } from '@/security/api/endpoints';
import { useNotifyStore } from '@/security/stores/notify';
import { formatDateTime, statusLabel, targetTypeLabel } from '@/security/utils/format';
import ModalShell from '@/security/components/ModalShell.vue';

const notify = useNotifyStore();
const applications = ref<ApplicationRequest[]>([]);

const filters = reactive({
  status: -1,
  targetType: -1,
  targetId: ''
});

const showReject = ref(false);
const rejectTarget = ref<ApplicationRequest | null>(null);
const rejectReason = ref('');

const loadApplications = async () => {
  try {
    const params: any = { auditOnly: true };
    if (filters.status !== -1) params.status = filters.status;
    if (filters.targetType !== -1) params.targetType = filters.targetType;
    if (filters.targetId) params.targetId = Number(filters.targetId);
    applications.value = (await fetchApplications(params)) as ApplicationRequest[];
  } catch (error: any) {
    notify.push(error?.message || '申请列表加载失败', 'error');
  }
};

const approve = async (id: number) => {
  try {
    await approveApplication(id);
    notify.push('已通过申请', 'success');
    await loadApplications();
  } catch (error: any) {
    notify.push(error?.message || '审批失败', 'error');
  }
};

const openReject = (item: ApplicationRequest) => {
  rejectTarget.value = item;
  rejectReason.value = '';
  showReject.value = true;
};

const submitReject = async () => {
  if (!rejectTarget.value) return;
  try {
    await rejectApplication(rejectTarget.value.id, { rejectReason: rejectReason.value });
    notify.push('已拒绝申请', 'success');
    showReject.value = false;
    await loadApplications();
  } catch (error: any) {
    notify.push(error?.message || '拒绝失败', 'error');
  }
};

onMounted(loadApplications);
</script>

<style scoped>
.filter-row {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  align-items: end;
}
</style>
