#!/usr/bin/env bash
# 一键执行本轮对话涉及的数据库迁移。
#
# 当前包含的迁移：
#   - 20260506_drop_personal_accounts.sql   消灭遗留个人账户，转换为共享账户
#                                           (account.user_id IS NOT NULL → 加入 account_members 后置 NULL)
#
# 设计：
#   - 幂等：可重复执行无副作用（INSERT IGNORE + UPDATE WHERE NOT NULL）
#   - 自动备份（默认开启）：跑迁移前 mysqldump 整个库到本地 ./db-backups/
#   - 显式确认：默认会停下让人审计前后差异，AUTO_CONFIRM=1 跳过
#   - 双模式：K8s 模式（默认，进 mysql pod 执行）；LOCAL=1 用本地 mysql 客户端
#
# 用法：
#   K8s 集群模式（默认）
#     ./migrate-db.sh                    # 跑迁移，先盘点 → 备份 → 确认 → 执行 → 复盘
#     DRY_RUN=1 ./migrate-db.sh          # 只盘点，不写
#     SKIP_BACKUP=1 ./migrate-db.sh      # 不做 mysqldump 备份（不推荐）
#     AUTO_CONFIRM=1 ./migrate-db.sh     # CI 模式
#
#   本地开发模式
#     LOCAL=1 MYSQL_BIN=/path/to/mysql ./migrate-db.sh
#     LOCAL=1 MYSQL_PWD=12345678 ./migrate-db.sh
#
# 退出码：
#   0 = 成功    1 = 用户取消    2 = 前置检查失败    3 = 迁移失败
set -euo pipefail

# -------- 配置（环境变量可覆盖）--------
LOCAL="${LOCAL:-0}"
DRY_RUN="${DRY_RUN:-0}"
AUTO_CONFIRM="${AUTO_CONFIRM:-0}"
SKIP_BACKUP="${SKIP_BACKUP:-0}"

# K8s 模式
NAMESPACE="${NAMESPACE:-mysql-db}"
MYSQL_POD="${MYSQL_POD:-jfs-mysql-0}"
MYSQL_HOST="${MYSQL_HOST:-jfs-mysql-router.mysql-db.svc.cluster.local}"
MYSQL_PORT="${MYSQL_PORT:-6446}"
MYSQL_DB="${MYSQL_DB:-szlab_appoint}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_ROOT_PWD="${MYSQL_ROOT_PWD:-}"

# 本地模式
MYSQL_BIN="${MYSQL_BIN:-mysql}"
MYSQLDUMP_BIN="${MYSQLDUMP_BIN:-mysqldump}"
MYSQL_PWD="${MYSQL_PWD:-12345678}"
LOCAL_HOST="${LOCAL_HOST:-127.0.0.1}"
LOCAL_PORT="${LOCAL_PORT:-3306}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MIGRATIONS_DIR="${REPO_ROOT}/backend/migrations"
BACKUP_DIR="${SCRIPT_DIR}/db-backups"

# 本轮要执行的迁移（按顺序）
MIGRATIONS=(
  "20260506_drop_personal_accounts.sql"
)

# -------- utils --------
log()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*" >&2; }
err()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; }
die()  { err "$@"; exit "${2:-1}"; }

confirm() {
  [[ "${AUTO_CONFIRM}" == "1" ]] && return 0
  local prompt="${1:-继续？}"
  read -r -p "${prompt} [y/N] " resp
  [[ "${resp,,}" == "y" || "${resp,,}" == "yes" ]]
}

# 统一的 mysql 调用：参数附加在末尾（如 -e "SQL" 或 < file）
# 用法: mysql_run -e "SELECT 1"   /  mysql_run < file.sql
mysql_run() {
  if [[ "${LOCAL}" == "1" ]]; then
    "${MYSQL_BIN}" -h"${LOCAL_HOST}" -u"${MYSQL_USER}" -p"${MYSQL_PWD}" -P"${LOCAL_PORT}" "${MYSQL_DB}" "$@" 2>/dev/null
  else
    kubectl -n "${NAMESPACE}" exec -i "${MYSQL_POD}" -c mysql -- \
      mysql -u"${MYSQL_USER}" -p"${MYSQL_ROOT_PWD}" -h "${MYSQL_HOST}" -P "${MYSQL_PORT}" "${MYSQL_DB}" "$@" 2>/dev/null
  fi
}

mysqldump_run() {
  local out="$1"
  if [[ "${LOCAL}" == "1" ]]; then
    "${MYSQLDUMP_BIN}" -h"${LOCAL_HOST}" -u"${MYSQL_USER}" -p"${MYSQL_PWD}" -P"${LOCAL_PORT}" \
      --single-transaction --quick "${MYSQL_DB}" > "${out}" 2>/dev/null
  else
    kubectl -n "${NAMESPACE}" exec "${MYSQL_POD}" -c mysql -- \
      mysqldump -u"${MYSQL_USER}" -p"${MYSQL_ROOT_PWD}" -h "${MYSQL_HOST}" -P "${MYSQL_PORT}" \
      --single-transaction --quick "${MYSQL_DB}" > "${out}" 2>/dev/null
  fi
}

# -------- 1. 预检 --------
log "本次对话涉及的数据库迁移："
for m in "${MIGRATIONS[@]}"; do echo "  - ${m}"; done

if [[ "${DRY_RUN}" == "1" ]]; then
  warn "DRY_RUN=1 — 仅盘点，不会备份、不会写入"
fi

if [[ "${LOCAL}" == "1" ]]; then
  log "模式：本地（host=${LOCAL_HOST}:${LOCAL_PORT} db=${MYSQL_DB}）"
  command -v "${MYSQL_BIN}"     >/dev/null || die "mysql 不在 PATH；export MYSQL_BIN=/path/to/mysql" 2
  if [[ "${SKIP_BACKUP}" != "1" && "${DRY_RUN}" != "1" ]]; then
    command -v "${MYSQLDUMP_BIN}" >/dev/null || die "mysqldump 不在 PATH；export MYSQLDUMP_BIN=... 或 SKIP_BACKUP=1" 2
  fi
else
  log "模式：K8s（ns=${NAMESPACE} pod=${MYSQL_POD} host=${MYSQL_HOST}:${MYSQL_PORT} db=${MYSQL_DB}）"
  command -v kubectl >/dev/null || die "kubectl 不在 PATH" 2
  kubectl -n "${NAMESPACE}" get pod "${MYSQL_POD}" >/dev/null || die "找不到 pod ${NAMESPACE}/${MYSQL_POD}" 2
  if [[ -z "${MYSQL_ROOT_PWD}" ]]; then
    log "从 ${NAMESPACE}/jfs-mysql-auth 自动读取 root 密码"
    for KEY in rootPassword MYSQL_ROOT_PASSWORD; do
      MYSQL_ROOT_PWD=$(kubectl -n "${NAMESPACE}" get secret jfs-mysql-auth \
        -o jsonpath="{.data.${KEY}}" 2>/dev/null | base64 -d || true)
      [[ -n "${MYSQL_ROOT_PWD}" ]] && break
    done
    [[ -n "${MYSQL_ROOT_PWD}" ]] || die "无法读到 root 密码；export MYSQL_ROOT_PWD=<pwd>" 2
  fi
fi

# 验证迁移文件都存在
for m in "${MIGRATIONS[@]}"; do
  [[ -f "${MIGRATIONS_DIR}/${m}" ]] || die "迁移文件不存在: ${MIGRATIONS_DIR}/${m}" 2
done

# 测试连通
log "测试连接"
mysql_run -e "SELECT 1 AS ping;" >/dev/null || die "无法连接到 MySQL" 2
log "✅ MySQL 可达"

# -------- 2. 迁移前盘点 --------
log "迁移前盘点：当前个人账户"
mysql_run -t -e "
  SELECT COUNT(*) AS personal_account_count FROM \`account\` WHERE user_id IS NOT NULL;
  SELECT id, name, user_id, active, balance, credit_limit FROM \`account\`
    WHERE user_id IS NOT NULL ORDER BY id;
"

if [[ "${DRY_RUN}" == "1" ]]; then
  log "DRY_RUN 完成 — 未做任何写入。"
  exit 0
fi

# -------- 3. 备份 --------
if [[ "${SKIP_BACKUP}" == "1" ]]; then
  warn "SKIP_BACKUP=1 — 不会做备份（如果迁移出问题无法回滚）"
else
  mkdir -p "${BACKUP_DIR}"
  ts=$(date +%Y%m%d_%H%M%S)
  backup_file="${BACKUP_DIR}/${MYSQL_DB}-${ts}.sql"
  log "备份整个库到 ${backup_file}"
  if mysqldump_run "${backup_file}"; then
    sz=$(du -h "${backup_file}" 2>/dev/null | awk '{print $1}')
    log "✅ 备份完成（${sz}）"
  else
    die "mysqldump 失败；可设 SKIP_BACKUP=1 跳过（风险自负）" 2
  fi
fi

# -------- 4. 确认 --------
if ! confirm "上面这些个人账户将被迁移成共享账户（owner 加入 account_members）。确认执行？"; then
  warn "用户取消"
  exit 1
fi

# -------- 5. 执行所有迁移 --------
for m in "${MIGRATIONS[@]}"; do
  log "执行迁移：${m}"
  if mysql_run < "${MIGRATIONS_DIR}/${m}"; then
    log "✅ ${m} 已应用"
  else
    err "❌ ${m} 失败"
    if [[ -f "${backup_file:-}" ]]; then
      err "可用 ${backup_file} 恢复："
      err "  mysql_run < ${backup_file}"
    fi
    exit 3
  fi
done

# -------- 6. 复盘 --------
log "迁移后复盘"
mysql_run -t -e "
  SELECT 'personal_left'  AS metric, COUNT(*) AS value FROM \`account\` WHERE user_id IS NOT NULL
  UNION ALL SELECT 'shared_total',  COUNT(*) FROM \`account\` WHERE user_id IS NULL
  UNION ALL SELECT 'members_total', COUNT(*) FROM account_members;
"

log "✅ 全部完成。建议接着部署本轮代码（k8s/deploy-update.sh）。"
