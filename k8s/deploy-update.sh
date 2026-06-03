#!/usr/bin/env bash
# 一键更新生产环境（包含本轮所有改动）
#
# 流程：
#   1. 预检查（kubectl/docker 可用、镜像 tag、未跑的迁移）
#   2. 数据库迁移：把残留个人账户转成共享 + 加成员（idempotent，重复跑无害）
#   3. 构建 + 推送 backend / ui 镜像
#   4. rollout restart 让 deployment 拉新镜像
#   5. 等待 ready + 健康检查
#
# 用法：
#   ./deploy-update.sh                   # 全流程（会在迁移前要确认）
#   TAG=v2026.05.06 ./deploy-update.sh   # 自定义镜像 tag
#   SKIP_MIGRATION=1 ./deploy-update.sh  # 跳过 SQL 迁移（已确认生产已跑）
#   SKIP_BUILD=1 ./deploy-update.sh      # 跳过 build/push（镜像已存在）
#   SKIP_RESTART=1 ./deploy-update.sh    # 只迁移和 build，不重启
#   AUTO_CONFIRM=1 ./deploy-update.sh    # CI 模式，不交互直接执行
#   DRY_RUN=1 ./deploy-update.sh         # 仅打印计划，不执行任何写操作
#
# 依赖：kubectl、docker、bash 4+
# 必须在 k8s/ 目录下执行
set -euo pipefail

# -------- 配置 --------
NAMESPACE="${NAMESPACE:-nemo}"
MYSQL_NS="${MYSQL_NS:-mysql-db}"
MYSQL_DB="${MYSQL_DB:-szlab_appoint}"
MYSQL_HOST="${MYSQL_HOST:-jfs-mysql-router.mysql-db.svc.cluster.local}"
MYSQL_PORT="${MYSQL_PORT:-6446}"
REGISTRY="${REGISTRY:-harbor.local:8088}"
PROJECT="${PROJECT:-oppointments-system}"
TAG="${TAG:-latest}"

SKIP_MIGRATION="${SKIP_MIGRATION:-0}"
SKIP_BUILD="${SKIP_BUILD:-0}"
SKIP_RESTART="${SKIP_RESTART:-0}"
AUTO_CONFIRM="${AUTO_CONFIRM:-0}"
DRY_RUN="${DRY_RUN:-0}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MIGRATION_FILE="${REPO_ROOT}/backend/migrations/20260506_drop_personal_accounts.sql"

# -------- 工具 --------
log()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*" >&2; }
err()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; }
die()  { err "$@"; exit 1; }

confirm() {
  [[ "${AUTO_CONFIRM}" == "1" ]] && return 0
  local prompt="${1:-继续？}"
  read -r -p "${prompt} [y/N] " resp
  [[ "${resp,,}" == "y" || "${resp,,}" == "yes" ]]
}

# Print + run; in DRY_RUN mode only print
run() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '\033[2m  [dry-run] %s\033[0m\n' "$*"
    return 0
  fi
  "$@"
}

if [[ "${DRY_RUN}" == "1" ]]; then
  warn "DRY_RUN=1 — 仅打印将执行的命令，不真的修改集群和数据库"
fi

# -------- 1. 预检查 --------
log "[1/5] 预检查"

command -v kubectl >/dev/null || die "kubectl 不在 PATH 里"
command -v docker  >/dev/null || die "docker 不在 PATH 里"

CTX=$(kubectl config current-context)
log "kubectl context: ${CTX}"

kubectl -n "${NAMESPACE}" get deploy nemo-backend nemo-ui >/dev/null \
  || die "namespace ${NAMESPACE} 下找不到 nemo-backend / nemo-ui"

# MySQL 客户端 pod（用 jfs-mysql-0 内置的 mysql client）
MYSQL_POD="${MYSQL_POD:-jfs-mysql-0}"
kubectl -n "${MYSQL_NS}" get pod "${MYSQL_POD}" >/dev/null \
  || die "MySQL pod ${MYSQL_NS}/${MYSQL_POD} 不存在；export MYSQL_POD=<pod-name> 覆盖"

# Harbor 凭证
docker info >/dev/null 2>&1 || die "docker daemon 没在跑"

if [[ -f "${MIGRATION_FILE}" ]]; then
  log "迁移文件存在: ${MIGRATION_FILE}"
else
  warn "迁移文件不存在: ${MIGRATION_FILE}（如果 SKIP_MIGRATION=1 可忽略）"
fi

if [[ "${TAG}" == "latest" ]]; then
  warn "TAG=latest（推荐用版本号如 v2026.05.06，方便回滚）"
fi

# -------- 2. 数据库迁移 --------
if [[ "${SKIP_MIGRATION}" == "1" ]]; then
  log "[2/5] 跳过 SQL 迁移（SKIP_MIGRATION=1）"
else
  log "[2/5] SQL 迁移：消灭遗留个人账户"
  [[ -f "${MIGRATION_FILE}" ]] || die "找不到迁移文件 ${MIGRATION_FILE}"

  # 取 root 密码：优先用环境变量；否则从 jfs-mysql-auth secret 读
  if [[ -n "${MYSQL_ROOT_PWD:-}" ]]; then
    ROOT_PWD="${MYSQL_ROOT_PWD}"
  else
    log "从 ${MYSQL_NS}/jfs-mysql-auth 读取 root 密码"
    ROOT_PWD=$(kubectl -n "${MYSQL_NS}" get secret jfs-mysql-auth \
      -o jsonpath='{.data.rootPassword}' 2>/dev/null | base64 -d || true)
    if [[ -z "${ROOT_PWD}" ]]; then
      ROOT_PWD=$(kubectl -n "${MYSQL_NS}" get secret jfs-mysql-auth \
        -o jsonpath='{.data.MYSQL_ROOT_PASSWORD}' 2>/dev/null | base64 -d || true)
    fi
    [[ -n "${ROOT_PWD}" ]] || die "无法从 secret 读到 root 密码；export MYSQL_ROOT_PWD=<pwd> 覆盖"
  fi

  log "迁移前盘点（个人账户列表）"
  kubectl -n "${MYSQL_NS}" exec "${MYSQL_POD}" -c mysql -- \
    mysql -uroot -p"${ROOT_PWD}" -h "${MYSQL_HOST}" -P "${MYSQL_PORT}" "${MYSQL_DB}" \
    -t -e "
      SELECT COUNT(*) AS personal_account_count FROM \`account\` WHERE user_id IS NOT NULL;
      SELECT id, name, user_id, active, balance FROM \`account\` WHERE user_id IS NOT NULL ORDER BY id;
    " 2>/dev/null || die "MySQL 盘点失败（密码错？或 pod/MySQL_HOST 不通？）"

  if ! confirm "上面会被迁移成共享账户（owner 加入 account_members）。继续？"; then
    die "用户取消迁移"
  fi

  log "执行迁移（事务包裹，幂等）"
  # 注意：迁移文件里的 inspection 段落是 SELECT，不会改数据；
  #      START TRANSACTION ... COMMIT 段是真实写入。直接执行即可，重复跑也是 INSERT IGNORE + UPDATE NULL，幂等安全。
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '\033[2m  [dry-run] kubectl -n %s exec -i %s -c mysql -- mysql ... < %s\033[0m\n' \
      "${MYSQL_NS}" "${MYSQL_POD}" "${MIGRATION_FILE}"
  else
    kubectl -n "${MYSQL_NS}" exec -i "${MYSQL_POD}" -c mysql -- \
      mysql -uroot -p"${ROOT_PWD}" -h "${MYSQL_HOST}" -P "${MYSQL_PORT}" "${MYSQL_DB}" \
      < "${MIGRATION_FILE}" 2>/dev/null
  fi

  log "迁移后校验"
  kubectl -n "${MYSQL_NS}" exec "${MYSQL_POD}" -c mysql -- \
    mysql -uroot -p"${ROOT_PWD}" -h "${MYSQL_HOST}" -P "${MYSQL_PORT}" "${MYSQL_DB}" \
    -t -e "
      SELECT 'personal_left'  AS metric, COUNT(*) AS value FROM \`account\` WHERE user_id IS NOT NULL
      UNION ALL SELECT 'shared_total',  COUNT(*) FROM \`account\` WHERE user_id IS NULL
      UNION ALL SELECT 'members_total', COUNT(*) FROM account_members;
    " 2>/dev/null

  log "✅ 迁移完成（personal_left 应为 0）"
fi

# -------- 3. Build & Push --------
if [[ "${SKIP_BUILD}" == "1" ]]; then
  log "[3/5] 跳过 build/push（SKIP_BUILD=1）"
else
  log "[3/5] 构建 + 推送镜像（tag=${TAG}）"

  # 用现有的 build 脚本，复用基础镜像
  for name in nemo-backend nemo-ui; do
    image="${REGISTRY}/${PROJECT}/${name}:${TAG}"
    ctx_dir="${REPO_ROOT}/$([ "${name}" = nemo-backend ] && echo backend || echo ui)"
    log "build ${image} (context=${ctx_dir})"
    run docker build -t "${image}" "${ctx_dir}"
    log "push ${image}"
    run docker push "${image}"
  done
fi

# -------- 4. Rollout restart --------
if [[ "${SKIP_RESTART}" == "1" ]]; then
  log "[4/5] 跳过 rollout restart（SKIP_RESTART=1）"
else
  log "[4/5] Rollout restart"

  # 如果不是 latest tag，要 set image 以更新 deployment 引用
  if [[ "${TAG}" != "latest" ]]; then
    run kubectl -n "${NAMESPACE}" set image deploy/nemo-backend \
      backend="${REGISTRY}/${PROJECT}/nemo-backend:${TAG}"
    run kubectl -n "${NAMESPACE}" set image deploy/nemo-ui \
      ui="${REGISTRY}/${PROJECT}/nemo-ui:${TAG}"
  else
    # latest tag + imagePullPolicy:Always → rollout restart 就会重新拉
    run kubectl -n "${NAMESPACE}" rollout restart deploy/nemo-backend
    run kubectl -n "${NAMESPACE}" rollout restart deploy/nemo-ui
  fi

  log "等待 nemo-backend ready"
  run kubectl -n "${NAMESPACE}" rollout status deploy/nemo-backend --timeout=5m

  log "等待 nemo-ui ready"
  run kubectl -n "${NAMESPACE}" rollout status deploy/nemo-ui --timeout=5m
fi

# -------- 5. 健康检查 --------
log "[5/5] 健康检查"

BACKEND_POD=$(kubectl -n "${NAMESPACE}" get pod -l app=nemo-backend \
  --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
if [[ -n "${BACKEND_POD}" ]]; then
  log "backend pod: ${BACKEND_POD}"
  kubectl -n "${NAMESPACE}" exec "${BACKEND_POD}" -- \
    sh -c 'wget -qO- http://127.0.0.1:8000/health 2>/dev/null \
           || curl -s http://127.0.0.1:8000/health 2>/dev/null \
           || python -c "import urllib.request; print(urllib.request.urlopen(\"http://127.0.0.1:8000/health\").read().decode())"' \
    || warn "backend /health 检查失败"
else
  warn "找不到 Running 的 backend pod"
fi

UI_POD=$(kubectl -n "${NAMESPACE}" get pod -l app=nemo-ui \
  --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
if [[ -n "${UI_POD}" ]]; then
  log "ui pod: ${UI_POD}（已 Running）"
fi

log "✅ 部署完成。建议手动验证："
cat <<EOF
  - 仪器列表能翻页
  - 创建预约的"结算账户"下拉只显示共享账户
  - AccountForm 不再有"绑定用户"字段
  - AccountList 不再有"个人账户"分组
EOF
