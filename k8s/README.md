# NEMO Kubernetes 部署

把整套系统（FastAPI 后端 + Vue/Nginx 前端 + 共享 MySQL）部署到任意 Kubernetes 集群的清单。所有资源放在 `nemo` 命名空间。

> Spring `security-server` 已经被 port 进 FastAPI，作为 nemo-backend 内的 `/security-api/api/*` 子路由；原来独立的 `security-server-ui` SPA 也被打进了 nemo-ui 镜像的 `/security/` 路径。集群里**只剩两个业务镜像**：`nemo-backend` + `nemo-ui`。

## 组成

| 文件 | 作用 |
| --- | --- |
| `00-namespace.yaml` | 命名空间 `nemo` |
| `05-rbac.yaml` | 后端 ServiceAccount + 监视 Job 的 RBAC |
| `10-secrets.yaml` | JWT / DB / 管理员等敏感配置（**部署前务必替换占位符**） |
| `11-configmap.yaml` | 后端环境变量与 UI 的 nginx 配置 |
| `20-db-init.yaml` | 一次性 Job：在共享 MySQL 集群上建库 + 建账号 |
| `30-backend.yaml` | FastAPI 后端 Deployment + Service + 50Gi 媒体 PVC |
| `32-ui.yaml` | 前端 Deployment（nginx 同时反代 `/api` 和 `/security-api`） + Service |
| `40-ingress.yaml` | 集群入口（默认 host `nemo.local`） |
| `kustomization.yaml` | 一键 apply 索引 |

## 镜像约定

清单中的 `image:` 已经写成 Harbor 地址：

| 服务 | 镜像 |
| --- | --- |
| 后端 | `harbor.local:8088/oppointments-system/nemo-backend:<tag>` |
| 前端 | `harbor.local:8088/oppointments-system/nemo-ui:<tag>` |

两个 Deployment 都声明了 `imagePullSecrets: [harbor-cred]`，所以集群每个工作节点不需要预先 `docker login`，只要 `nemo` 命名空间里有 `harbor-cred` 这个 docker-registry Secret 即可。

## 快速开始

### 1. 让 Docker / 节点信任 Harbor（HTTP 仓库）

`harbor.local:8088` 走 HTTP，需要把它加进每个会执行 push/pull 的机器：

- **构建机 / 开发机**：`/etc/docker/daemon.json`（Linux/macOS）或 Docker Desktop → Settings → Docker Engine：
  ```json
  { "insecure-registries": ["harbor.local:8088"] }
  ```
  保存后 `systemctl restart docker` 或重启 Docker Desktop。
- **K8s 节点（containerd）**：`/etc/containerd/config.toml` 加：
  ```toml
  [plugins."io.containerd.grpc.v1.cri".registry.mirrors."harbor.local:8088"]
    endpoint = ["http://harbor.local:8088"]
  ```
  然后 `systemctl restart containerd`。
- **DNS**：每个节点 `/etc/hosts` 加 `<harbor-ip>  harbor.local`，确保能解析。

### 2. 构建并推送镜像

```bash
# Linux / macOS / WSL / Git Bash
cd k8s
TAG=v0.1.0 ./build-and-push.sh
```
```powershell
# Windows PowerShell
cd k8s
$env:TAG="v0.1.0"
.\build-and-push.ps1
```

脚本会：登录 → 依次 `docker build` 三个目录 → 打 tag `harbor.local:8088/oppointments-system/<name>:<tag>` → push。
默认 `TAG=latest`，可通过环境变量覆盖。换 registry/项目名时也可以传 `REGISTRY=` / `PROJECT=`。

后端默认使用 `continuumio/miniconda3:latest`，在镜像里创建 Python 3.12 的 `nemo` conda 环境。如果构建机拉 Docker Hub/镜像站不稳定，可以先把基础镜像预置到 Harbor：

```bash
cd k8s
REGISTRY=harbor.local:8088 ./stage-base-images.sh
USE_STAGED_BASE_IMAGES=1 TAG=v0.1.0 ./build-and-push.sh
```

如果 Docker daemon 直连 `registry-1.docker.io` 被拒绝，先指定当前网络能访问的 Docker Hub 镜像代理：

```bash
UPSTREAM_PREFIX=<dockerhub-mirror> REGISTRY=harbor.local:8088 ./stage-base-images.sh
```

没有可用镜像代理时，也可以先从别的机器 `docker save` / `docker load` 这些基础镜像，再执行：

```bash
SKIP_PULL=1 REGISTRY=harbor.local:8088 ./stage-base-images.sh
```

PowerShell 构建时可设置：

```powershell
$env:USE_STAGED_BASE_IMAGES="1"
$env:TAG="v0.1.0"
.\build-and-push.ps1
```

> 推送前确保 Harbor 控制台里已经创建 `oppointments-system` 项目（公开或者用一个有写权限的账号都行）。

### 3. 在集群中创建 Harbor 拉取凭证

```bash
kubectl -n nemo create secret docker-registry harbor-cred \
  --docker-server=harbor.local:8088 \
  --docker-username='<harbor 账号>' \
  --docker-password='<harbor 密码>' \
  --docker-email='ops@example.com'
```

确认：
```bash
kubectl -n nemo get secret harbor-cred
```

> 名字必须叫 `harbor-cred`，与 Deployment 里的 `imagePullSecrets` 一致。如果你想换名字，记得三个 Deployment 都要改。

### 4. 改业务 Secret / Config

- 编辑 `10-secrets.yaml`，替换所有 `CHANGE_ME_*` 占位符。
  - `SECRET_KEY` 推荐 `openssl rand -hex 64`
  - `mysql-secret.MYSQL_PASSWORD` 要和 `nemo-backend-secret.MYSQL_PASSWORD` 一致
- 按需改 `11-configmap.yaml`：
  - `BACKEND_CORS_ORIGINS`：线上前端域名
  - `SECURITY_SERVER_ENABLED`：不用统一认证就 `"false"`
- 如果用了 `TAG` 而不是 `latest`，把三个 Deployment 里 `image:` 末尾的 `:latest` 改成你打的 tag（或用 `kustomize edit set image`）。

### 5. 应用清单

```bash
kubectl apply -k k8s/
```

### 6. 验证

```bash
kubectl -n nemo get pods,svc,pvc
kubectl -n nemo describe pod -l app=nemo-backend | sed -n '/Events:/,$p'
kubectl -n nemo logs deploy/nemo-backend
```

如果 Pod 卡在 `ImagePullBackOff`：99% 是 `insecure-registries` 没配 / `harbor-cred` 没建 / tag 拼错。`kubectl describe pod` 的 Events 段会写明具体原因。

### 7. 入口

- 集群有 ingress-controller：把 `nemo.local` 解析到 ingress 的外部 IP，浏览器访问 `http://nemo.local`。
- 没有 ingress：`kubectl -n nemo port-forward svc/nemo-ui 8080:80` 后访问 `http://localhost:8080`。

## 升级镜像

```bash
TAG=v0.2.0 ./k8s/build-and-push.sh
kubectl -n nemo set image deploy/nemo-backend  backend=harbor.local:8088/oppointments-system/nemo-backend:v0.2.0
kubectl -n nemo set image deploy/nemo-ui       ui=harbor.local:8088/oppointments-system/nemo-ui:v0.2.0
```

## 媒体存储 (JuiceFS)

后端的图片、培训资料、考试附件都落在 `/app/media`，由 PVC `nemo-backend-media` 提供。这个 PVC 走集群里现有的 `juicefs-sc` StorageClass（已在 `jfs-rustfs` 命名空间运行），RWX 访问模式让后端可以多副本横向扩展。

直接 `kubectl apply -k k8s/` 即可，CSI 驱动会按 `juicefs-sc` 的参数自动给该 PVC 分配子目录。无需在本仓库内额外建 Secret/SC。

### 验证 JuiceFS 挂载

```bash
kubectl -n nemo get pvc nemo-backend-media           # 应显示 Bound
kubectl -n nemo exec deploy/nemo-backend -- df -h /app/media
kubectl -n nemo exec deploy/nemo-backend -- ls -la /app/media
# 写一个探针文件试试持久化与多副本可见性：
kubectl -n nemo exec deploy/nemo-backend -- sh -c 'echo hi > /app/media/_probe && cat /app/media/_probe'
```

挂上以后，`media/users/<id>/`、`media/tools/<id>/`、`media/announcements/<id>/`、`media/training/<id>/` 这几个子目录都会落到 JuiceFS 里，多副本后端 pod 共享读写。

> 如果将来 `juicefs-sc` 改名或被删除，从 git history 里恢复 `50-juicefs-storage.yaml` 自建一份 SC 即可。

## 注意事项

- 当前 PVC 用 RWX，后端可任意扩 `replicas`。如果你换回 RWO（NFS/CephFS 之外的本地盘），要把 `30-backend.yaml` 的 `accessModes` 改回 `ReadWriteOnce`、`strategy` 改回 `Recreate`，并把 `replicas` 锁回 1。

## 数据库（共用 MySQL InnoDB Cluster）

不在本仓库内启 MySQL，直接连用 `mysql-db` 命名空间里的共享集群：

- 集群：`InnoDBCluster/jfs-mysql`（3 个节点 + 2 个 Router，MySQL 9.5）
- Router：`jfs-mysql-router.mysql-db.svc.cluster.local`，**6446 = RW split（写入走主）**，6447 = RO
- root 凭证：`mysql-db/jfs-mysql-auth` Secret（`Root@12345678`）

### 一次性建库

`20-db-init.yaml` 是个 K8s Job，启动时：
1. 等 Router 可达；
2. 用 root 创建空库 `szlab_appoint`；
3. 创建专用账号 `nemo` 并只授该库全权（不给 root）；
4. 顺手 `DROP USER IF EXISTS 'secsrv'@'%'` 清理旧 Spring 账号（幂等无害）。

`30-backend.yaml` 的 init-container `kubectl wait --for=condition=complete job/nemo-db-init` 会在 Job 完成前阻塞业务 Pod。所以 `kubectl apply -k k8s/` 一次跑完就好。

### 表怎么建？

**不导任何数据 dump**——后端启动时会做两件事：

1. **`Base.metadata.create_all()`** 用 SQLAlchemy 模型在空库里建出全部基础表（user / project / tool / reservation / bill / usage_event / training_* / exam_* 以及融合进来的 staff_*）。
2. 跑增量 DDL（`audit_log` / `tool_image` / 各种新增列），保证旧库也能升级。
3. 如果 `user` 表是空的，自动用 `FIRST_SUPERUSER` / `FIRST_SUPERUSER_PASSWORD` 建一个超管账号。

也就是说从空库到能登录管理后台，**全部由后端自己完成**，运维只要保证连接通即可。

### 改密码

`10-secrets.yaml` 里需要保持一致的口令对：

| Secret | 字段 | 用途 |
| --- | --- | --- |
| `nemo-backend-secret.MYSQL_PASSWORD` | nemo 业务账号密码 | backend 连库 |
| `nemo-db-init.NEMO_DB_PASSWORD` | 同上 | Job 创建/重置 nemo 账号时使用 |
| `nemo-db-init.MYSQL_ROOT_PASSWORD` | `Root@12345678` | 与 `mysql-db/jfs-mysql-auth` 一致 |

改完用 `kubectl delete job nemo-db-init -n nemo && kubectl apply -k k8s/` 重跑 Job，就会用新密码 `ALTER USER` 重置（`init.sql` 里 `CREATE USER IF NOT EXISTS` 后跟 `ALTER USER`，幂等可重跑）。

### 验证

```bash
# Job 是否完成
kubectl -n nemo logs job/nemo-db-init

# 用 nemo 账号登一下 Router
kubectl -n nemo run mysql-shell -it --rm --restart=Never \
  --image=mysql:8.4 -- \
  mysql -h jfs-mysql-router.mysql-db.svc.cluster.local -P 6446 \
        -u nemo -p<NEMO_DB_PASSWORD> -e "SHOW DATABASES; USE szlab_appoint; SHOW TABLES;"
```

第一次运行后端时会看到日志：`Created initial superuser admin (admin@nemo.local)`，用这个账号登前端即可。

- MySQL 直接用 `mysql-db/jfs-mysql` 共享集群——本仓库不再启自带 StatefulSet。若想换成别的 MySQL，把 ConfigMap 里 `MYSQL_SERVER` / `MYSQL_PORT` 改对即可。
- 资源 `requests/limits` 为保守默认值，按你的负载调整。
- 要给入口加 TLS：在 `40-ingress.yaml` 里把 `tls:` 注释打开并提前创建 `nemo-tls` secret。
- staff 模块只剩 `SECURITY_SERVER_ENABLED` 和 `SECURITY_SERVER_PROJECT_SYNC_ENABLED` 两个开关（在 `11-configmap.yaml`）。需要关掉整个 staff 入口时改成 `"false"` 即可，原 Spring 服务相关的 BASE_URL / TIMEOUT / VERIFY_SSL 等环境变量已经彻底删除。
