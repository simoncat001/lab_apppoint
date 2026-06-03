# NEMO 集群部署手册

从零到能登录前端的完整步骤，按这个顺序执行不会踩坑。

> 本文是运维 runbook。架构说明、单文件用途请看 [README.md](README.md)。

---

## 0. 部署前检查清单

在 **管理机**（能跑 kubectl 的机器）上确认：

```bash
# kubectl 连接到对的集群
kubectl config current-context

# 三个底座资源已就绪
kubectl get sc | grep juicefs-sc                  # ✅ JuiceFS StorageClass
kubectl get pods -n mysql-db | grep jfs-mysql     # ✅ MySQL InnoDB Cluster
kubectl get pods -n jfs-rustfs | grep rustfs      # ✅ rustfs 对象存储
```

在 **构建机**（能跑 docker 的机器，可以和管理机是同一台）上确认：

```bash
docker info                                       # docker 守护进程在跑
docker login harbor.local:8088                    # Harbor 账号能登录
```

如果 Harbor 是 HTTP（默认 8088 没 TLS），第一次用要先把它加到信任列表：

- **Linux/macOS Docker**：`/etc/docker/daemon.json` → 加 `"insecure-registries": ["harbor.local:8088"]` → 重启 docker
- **Docker Desktop**：Settings → Docker Engine → 加同样的 JSON → Apply
- **每台 K8s 节点的 containerd**：`/etc/containerd/config.toml` 加：
  ```toml
  [plugins."io.containerd.grpc.v1.cri".registry.mirrors."harbor.local:8088"]
    endpoint = ["http://harbor.local:8088"]
  ```
  然后 `systemctl restart containerd`
- **每台 K8s 节点 + 管理机**：`/etc/hosts` 加一行
  ```
  <harbor 宿主机 IP>  harbor.local
  ```

---

## 1. 构建并推送镜像

在 Harbor 控制台先建好项目 `oppointments-system`（公开或者用一个有写权限的账号）。

### Linux / macOS / WSL / Git Bash

```bash
cd /path/to/nemo_2/k8s
TAG=v0.1.0 ./build-and-push.sh
```

### Windows PowerShell

```powershell
cd .\k8s
$env:TAG="v0.1.0"
.\build-and-push.ps1
```

脚本会依次：
1. `docker login harbor.local:8088`
2. `docker build` 两个目标 — `nemo-backend`（context = `backend/`），`nemo-ui`（context = 仓库根，因为它的 Dockerfile 同时把 `ui/` 和 `security-server-ui/` 编进同一个镜像）
3. `docker tag` 成 `harbor.local:8088/oppointments-system/<name>:<TAG>`
4. `docker push` 到 Harbor

预计耗时：第一次 5–10 分钟（拉基础镜像 + npm/pip 装依赖），后续增量 1–3 分钟。

> 历史上的 `security-server`（Java/Maven）已经 port 进 nemo-backend，作为 `/security-api/api/*` 子路由提供服务。原来独立的 `security-server-ui` 也被打进了 nemo-ui 镜像 `/security/` 子路径。

后端默认使用 `continuumio/miniconda3:latest`，镜像内会创建 `nemo` conda 环境并安装 Python 3.12。如果构建机访问 Docker Hub/镜像站不稳定，可以先在能访问上游镜像的机器上预置基础镜像到 Harbor：

```bash
cd /path/to/nemo_2/k8s
REGISTRY=harbor.local:8088 ./stage-base-images.sh
```

如果 Docker daemon 直连 `registry-1.docker.io` 被拒绝，给脚本指定一个当前网络能访问的 Docker Hub 镜像代理：

```bash
UPSTREAM_PREFIX=<dockerhub-mirror> REGISTRY=harbor.local:8088 ./stage-base-images.sh
```

脚本会把 `continuumio/miniconda3:latest` 解析成 `<dockerhub-mirror>/continuumio/miniconda3:latest`，把 `node:20-alpine` 这类官方镜像解析成 `<dockerhub-mirror>/library/node:20-alpine`。

如果完全没有可用镜像代理，就在另一台能联网的机器上 `docker pull` 后 `docker save`，把 tar 拷到构建机 `docker load`，再跳过拉取直接推 Harbor：

```bash
SKIP_PULL=1 REGISTRY=harbor.local:8088 ./stage-base-images.sh
```

之后构建业务镜像时让脚本使用 Harbor 里的基础镜像：

```bash
USE_STAGED_BASE_IMAGES=1 TAG=v0.1.0 ./build-and-push.sh
```

PowerShell：

```powershell
$env:USE_STAGED_BASE_IMAGES="1"
$env:TAG="v0.1.0"
.\build-and-push.ps1
```

跑完应该看到：
```
All images pushed:
  harbor.local:8088/oppointments-system/nemo-backend:v0.1.0
  harbor.local:8088/oppointments-system/nemo-ui:v0.1.0
```

> 想用其他 tag/registry/项目名时：`REGISTRY=... PROJECT=... TAG=... ./build-and-push.sh`。基础镜像预置到非 `library` 项目时，用 `BASE_PROJECT=... USE_STAGED_BASE_IMAGES=1`。

---

## 2. 改配置占位符

编辑 [`10-secrets.yaml`](10-secrets.yaml)，把所有 `CHANGE_ME_*` 替换成真实值。**注意 `MYSQL_PASSWORD` 必须等于 `NEMO_DB_PASSWORD`**（一边是 backend 读、一边是 DB-init Job 用）：

```text
nemo-backend-secret:
  SECRET_KEY:                 ← openssl rand -hex 64 生成新值
  MYSQL_PASSWORD:        ┐
  FIRST_SUPERUSER_PASSWORD    ← 你能记住的管理员口令
nemo-db-init:
  NEMO_DB_PASSWORD:      ┘    ← 必须和 MYSQL_PASSWORD 完全一样
  MYSQL_ROOT_PASSWORD:        ← Root@12345678（已和 jfs-mysql-auth 对齐）
```

**生成强随机值参考**：

```bash
openssl rand -hex 64                        # SECRET_KEY
openssl rand -base64 24 | tr -d '/+=' | head -c 24   # 数据库口令
```

如果你打的 tag 不是 `latest`，编辑两个 Deployment 把 `image:` 末尾的 `:latest` 换成你的 tag：

- [`30-backend.yaml`](30-backend.yaml)
- [`32-ui.yaml`](32-ui.yaml)

或者用一行命令统一改：

```bash
TAG=v0.1.0
sed -i.bak "s|:latest$|:${TAG}|g" k8s/3*-*.yaml && rm k8s/3*-*.yaml.bak
```

---

## 3. 创建 namespace 和 Harbor 拉取凭证

```bash
# namespace（其它资源 apply 时会再次确认）
kubectl apply -f k8s/00-namespace.yaml

# Harbor 拉取凭证（注意 Secret 名字必须叫 harbor-cred，所有 Deployment 都引用它）
kubectl -n nemo create secret docker-registry harbor-cred \
  --docker-server=harbor.local:8088 \
  --docker-username='<你的 harbor 账号>' \
  --docker-password='<你的 harbor 密码>'
```

确认：
```bash
kubectl -n nemo get secret harbor-cred
# 输出有一行 harbor-cred  kubernetes.io/dockerconfigjson  ...
```

---

## 4. 一键部署

```bash
kubectl apply -k k8s/
```

输出大致这些资源：
```
namespace/nemo configured
serviceaccount/nemo-backend created
role.rbac.authorization.k8s.io/nemo-backend-job-watcher created
rolebinding.rbac.authorization.k8s.io/nemo-backend-job-watcher created
secret/nemo-backend-secret created
secret/nemo-db-init created
configmap/nemo-backend-config created
configmap/nemo-ui-nginx created
configmap/nemo-db-init-sql created
job.batch/nemo-db-init created
deployment.apps/nemo-backend created
deployment.apps/nemo-ui created
service/nemo-backend created
service/nemo-ui created
ingress.networking.k8s.io/nemo created
```

启动顺序由 init-container 控制：
```
nemo-db-init Job 跑完
        │
        ▼
nemo-backend pod 启动（init-container kubectl wait）
        │
        ▼
backend 启动: Base.metadata.create_all() 建全部业务表（含 staff_*） + 自动建超管
        │
        ▼
nemo-ui 转发：
  /              → nemo SPA
  /security/     → staff SPA
  /api/*         → nemo-backend
  /security-api/*→ nemo-backend (in-process staff endpoints)
```

---

## 5. 验证

### 5.1 Job 完成

```bash
kubectl -n nemo wait --for=condition=complete --timeout=300s job/nemo-db-init
kubectl -n nemo logs job/nemo-db-init
```
末尾应看到：`Database init complete.`

### 5.2 Pod 全部 Running

```bash
kubectl -n nemo get pod
```
预期：
```
NAME                               READY   STATUS    RESTARTS
nemo-backend-xxxxxxxxx-aaaaa       1/1     Running   0
nemo-ui-xxxxxxxxx-bbbbb            1/1     Running   0
nemo-ui-xxxxxxxxx-ccccc            1/1     Running   0
```

### 5.3 PVC 已绑定 JuiceFS

```bash
kubectl -n nemo get pvc nemo-backend-media
# STATUS=Bound  ACCESS MODES=RWX  STORAGECLASS=juicefs-sc

kubectl -n nemo exec deploy/nemo-backend -- df -h /app/media
# Filesystem 应当是 JuiceFS:nemo-... 之类
```

### 5.4 后端建表 + 超管

```bash
kubectl -n nemo logs deploy/nemo-backend | grep -E "create_all|superuser"
# 应能看到: Created initial superuser admin (admin@nemo.local)
```

### 5.5 数据库直连冒烟

```bash
kubectl -n nemo run mysql-shell -it --rm --restart=Never \
  --image=mysql:8.4 -- \
  mysql -h jfs-mysql-router.mysql-db.svc.cluster.local -P 6446 \
        -u nemo -p<NEMO_DB_PASSWORD> -e \
        "USE szlab_appoint; SHOW TABLES; SELECT username,is_superuser FROM user;"
```
表应该有 30 张左右、`user` 表里有一行 `admin / 1`。

---

## 6. 访问

### 有 Ingress Controller

把 Ingress 的 ExternalIP 解析为 `nemo.local`（DNS 或 hosts），浏览器打开 `http://nemo.local`，用 `admin@nemo.local` + 你设置的 `FIRST_SUPERUSER_PASSWORD` 登录。

### 没有 Ingress Controller

```bash
kubectl -n nemo port-forward svc/nemo-ui 8080:80
```
浏览器打开 `http://localhost:8080`。

---

## 7. 常见问题速查

| 现象 | 原因 / 排查 |
| --- | --- |
| `ImagePullBackOff` + `http: server gave HTTP response to HTTPS client` | 节点 containerd 没配 `insecure-registries`。改 `/etc/containerd/config.toml` 重启。 |
| `ImagePullBackOff` + `unauthorized` | `harbor-cred` 没建或账号没项目权限。`kubectl -n nemo get secret harbor-cred` 检查。 |
| `ImagePullBackOff` + `no such host: harbor.local` | 节点 `/etc/hosts` 缺记录。 |
| `ImagePullBackOff` + `manifest unknown` | image tag 拼错或没 push 成功。回 Harbor 看仓库。 |
| Pod 卡在 `Init:0/1`，init-container 一直 running | DB init Job 没跑通。`kubectl -n nemo logs job/nemo-db-init` 看具体错误（最常见：root 密码不对）。 |
| Backend 启动报 `Access denied for user 'nemo'@'%'` | `nemo-backend-secret.MYSQL_PASSWORD` 和 `nemo-db-init.NEMO_DB_PASSWORD` 不一致。改一致后重跑 Job + 重启 backend。 |
| Backend 启动报 `Unknown database 'szlab_appoint'` | DB init Job 没跑或失败。回到上一行排查。 |
| Backend 卡在连接 MySQL 重试 | Router service 名/端口写错。确认 `MYSQL_SERVER=jfs-mysql-router.mysql-db.svc.cluster.local`、`MYSQL_PORT=6446`。 |
| 前端 502 | backend 还没 ready 或 Service 名不一致。`kubectl -n nemo get pod` + `kubectl -n nemo describe svc nemo-backend`。 |
| 上传图片成功但取不到 | JuiceFS PVC 没挂上。`kubectl -n nemo describe pod -l app=nemo-backend` 看 Volume。 |

`kubectl -n nemo describe pod <pod>` 的 `Events:` 段几乎能定位 90% 的问题。

---

## 8. 运维操作

### 8.1 升级业务镜像

```bash
TAG=v0.2.0
cd k8s && ./build-and-push.sh

kubectl -n nemo set image deploy/nemo-backend  backend=harbor.local:8088/oppointments-system/nemo-backend:$TAG
kubectl -n nemo set image deploy/nemo-ui       ui=harbor.local:8088/oppointments-system/nemo-ui:$TAG

kubectl -n nemo rollout status deploy/nemo-backend
kubectl -n nemo rollout status deploy/nemo-ui
```

backend 的 `bootstrap.py` 会在新版启动时把新增的 column / table / index 自动补上，向后兼容旧库。

### 8.2 回滚

```bash
kubectl -n nemo rollout undo deploy/nemo-backend
kubectl -n nemo rollout undo deploy/nemo-ui
```

### 8.3 扩缩容

```bash
# 后端横向扩展（JuiceFS RWX，所有副本共享 /app/media）
kubectl -n nemo scale deploy/nemo-backend --replicas=3

# UI 默认 2 副本，可继续扩
kubectl -n nemo scale deploy/nemo-ui --replicas=4
```

### 8.4 改密码 / 重置账号

改 [`10-secrets.yaml`](10-secrets.yaml) 后：
```bash
kubectl apply -f k8s/10-secrets.yaml
kubectl -n nemo delete job nemo-db-init        # 让 Job 重跑
kubectl apply -k k8s/                          # 重建 Job
kubectl -n nemo wait --for=condition=complete --timeout=300s job/nemo-db-init
kubectl -n nemo rollout restart deploy/nemo-backend
```
`init.sql` 里 `CREATE USER IF NOT EXISTS … ; ALTER USER … IDENTIFIED BY …;` 是幂等的，第二次跑会用新密码 `ALTER USER` 重置。

### 8.5 重置数据库（清空重来）

⚠️ **此操作会丢失全部业务数据**。

```bash
# 用 root 登 router，DROP DATABASE
kubectl -n nemo run mysql-shell -it --rm --restart=Never --image=mysql:8.4 -- \
  mysql -h jfs-mysql-router.mysql-db.svc.cluster.local -P 6446 \
        -u root -pRoot@12345678 -e \
        "DROP DATABASE IF EXISTS \`szlab_appoint\`;"

# 重跑建库 Job
kubectl -n nemo delete job nemo-db-init
kubectl apply -f k8s/20-db-init.yaml

# 重启 backend，会重新 create_all + 建超管
kubectl -n nemo rollout restart deploy/nemo-backend
```

### 8.6 清空媒体文件

⚠️ **会清掉所有上传的图片/培训资料**。

```bash
kubectl -n nemo exec deploy/nemo-backend -- sh -c 'rm -rf /app/media/* && ls /app/media'
```
不需要重启，POSIX 写入立即可见。

### 8.7 完全卸载

```bash
kubectl delete -k k8s/                  # 业务全删
kubectl -n nemo delete pvc nemo-backend-media   # JuiceFS 子目录释放
kubectl delete ns nemo                  # 收尾

# DB 清理（可选；如果以后还想留这个数据库就跳过）
kubectl run mysql-shell -it --rm --restart=Never --image=mysql:8.4 -- \
  mysql -h jfs-mysql-router.mysql-db.svc.cluster.local -P 6446 \
        -u root -pRoot@12345678 -e \
        "DROP DATABASE IF EXISTS \`szlab_appoint\`;
         DROP USER IF EXISTS 'nemo'@'%';
         DROP USER IF EXISTS 'secsrv'@'%';  -- legacy account, may not exist
         DROP DATABASE IF EXISTS \`security-server\`;  -- legacy db, may not exist"
```

---

## 9. 一键脚本（可选）

把 1–4 步包装一下：

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

TAG="${TAG:-v0.1.0}"

echo "==> [1/4] Building & pushing images (tag=$TAG)"
TAG="$TAG" k8s/build-and-push.sh

echo "==> [2/4] Make sure 10-secrets.yaml is filled in. Press Enter to continue."
read -r

echo "==> [3/4] Ensuring namespace + Harbor cred"
kubectl apply -f k8s/00-namespace.yaml
kubectl -n nemo get secret harbor-cred >/dev/null 2>&1 || {
  echo "Please run:"
  echo "  kubectl -n nemo create secret docker-registry harbor-cred \\"
  echo "    --docker-server=harbor.local:8088 --docker-username=... --docker-password=..."
  exit 1
}

echo "==> [4/4] Applying manifests"
kubectl apply -k k8s/

kubectl -n nemo wait --for=condition=complete --timeout=300s job/nemo-db-init
kubectl -n nemo rollout status deploy/nemo-backend
kubectl -n nemo rollout status deploy/nemo-ui

echo
echo "Done. Try: kubectl -n nemo port-forward svc/nemo-ui 8080:80"
```

保存为 `deploy.sh` + `chmod +x deploy.sh` 后跑 `TAG=v0.1.0 ./deploy.sh`。
