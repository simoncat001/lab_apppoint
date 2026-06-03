export const formatDateTime = (value?: string) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
};

export const statusLabel: Record<number, string> = {
  0: '待审核',
  1: '已通过',
  2: '已拒绝'
};

export const targetTypeLabel: Record<number, string> = {
  1: '部门',
  2: '项目',
  3: '小组'
};

export const userStatusLabel: Record<number, string> = {
  0: '待审核/禁用',
  1: '正常'
};
