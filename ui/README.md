# NEMO UI - Vue 3 Frontend

现代化的 NEMO 实验室管理系统前端界面，使用 Vue 3 + TypeScript + Vite 构建。

## 🚀 技术栈

- **框架**: Vue 3.4 (Composition API + `<script setup>`)
- **构建工具**: Vite 5
- **语言**: TypeScript 5
- **UI 框架**: Element Plus 2.5
- **状态管理**: Pinia 2
- **路由**: Vue Router 4
- **HTTP 客户端**: Axios
- **图表**: ECharts 5
- **工具库**: VueUse, Day.js, Lodash-es

## 📦 项目结构

```
ui/
├── public/              # 静态资源
├── src/
│   ├── api/            # API 接口定义
│   │   ├── auth.ts
│   │   ├── users.ts
│   │   ├── tools.ts
│   │   ├── reservations.ts
│   │   ├── accounts.ts
│   │   ├── usage-events.ts
│   │   ├── tasks.ts
│   │   ├── staff-charges.ts
│   │   └── configurations.ts
│   ├── assets/         # 资源文件
│   │   ├── styles/
│   │   └── images/
│   ├── components/     # 全局组件
│   │   ├── common/
│   │   └── layout/
│   ├── composables/    # 组合式函数
│   ├── router/         # 路由配置
│   ├── stores/         # Pinia 状态管理
│   │   ├── auth.ts
│   │   ├── user.ts
│   │   └── app.ts
│   ├── types/          # TypeScript 类型定义
│   ├── utils/          # 工具函数
│   │   ├── request.ts
│   │   └── helpers.ts
│   ├── views/          # 页面组件
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── tools/
│   │   ├── reservations/
│   │   ├── accounts/
│   │   ├── usage-events/
│   │   ├── tasks/
│   │   ├── staff-charges/
│   │   └── configurations/
│   ├── App.vue
│   └── main.ts
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## 🎯 核心功能模块

### 1. 用户认证 (Authentication)
- ✅ 登录/登出
- ✅ JWT Token 管理
- ✅ 权限验证

### 2. 工具管理 (Tools)
- ✅ 工具列表/详情
- ✅ 工具状态监控
- ✅ 工具预约

### 3. 预约系统 (Reservations)
- ✅ 预约日历视图
- ✅ 创建/编辑预约
- ✅ 预约确认/取消

### 4. 账户管理 (Accounts)
- ✅ 账户列表
- ✅ 账户激活/停用
- ✅ 账户类型管理

### 5. 使用记录 (Usage Events)
- ✅ 使用记录列表
- ✅ 时长统计
- ✅ 验证/豁免操作

### 6. 任务管理 (Tasks)
- ✅ 任务列表/详情
- ✅ 任务创建/更新
- ✅ 任务状态追踪
- ✅ 紧急程度分级

### 7. 员工收费 (Staff Charges)
- ✅ 收费记录列表
- ✅ 开始/结束服务
- ✅ 验证/豁免
- ✅ 统计分析

### 8. 配置管理 (Configurations)
- ✅ 工具配置列表
- ✅ 配置设置修改
- ✅ 配置历史查看
- ✅ 颜色标记

## 🛠️ 开发指南

### 安装依赖

```bash
cd ui
npm install
```

### 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:3000

### 构建生产版本

```bash
npm run build
```

### 预览生产版本

```bash
npm run preview
```

### 代码检查

```bash
npm run lint
```

### 代码格式化

```bash
npm run format
```

## 🎨 设计规范

### 颜色方案
- 主色: `#409EFF` (Element Plus 默认蓝)
- 成功: `#67C23A`
- 警告: `#E6A23C`
- 危险: `#F56C6C`
- 信息: `#909399`

### 布局
- 左侧导航栏: 固定宽度 200px
- 顶部导航栏: 固定高度 60px
- 内容区域: 响应式布局

### 组件规范
- 使用 Composition API
- 使用 `<script setup>` 语法
- 使用 TypeScript 类型定义
- 组件命名采用 PascalCase

## 📡 API 集成

后端 API 地址: `http://localhost:8000/api`

所有 API 请求通过 Axios 实例统一管理，自动添加认证 Token。

### API 模块
- `/auth` - 认证相关
- `/users` - 用户管理
- `/tools` - 工具管理
- `/reservations` - 预约管理
- `/accounts` - 账户管理
- `/usage` - 使用记录
- `/tasks` - 任务管理
- `/staff` - 员工收费
- `/config` - 配置管理

## 🔐 权限控制

### 角色定义
- **超级管理员** (Superuser): 完全访问权限
- **管理员** (Staff): 管理功能权限
- **普通用户** (User): 基本功能权限

### 路由守卫
- 未登录用户重定向到登录页
- 权限不足显示 403 页面
- Token 过期自动跳转登录

## 📱 响应式设计

支持以下设备尺寸:
- 桌面端: ≥1200px
- 平板端: 768px - 1199px
- 手机端: <768px

## 🌐 国际化

当前支持语言:
- 简体中文 (默认)
- 英文 (计划中)

## 🧪 测试

```bash
# 单元测试
npm run test:unit

# E2E 测试
npm run test:e2e
```

## 📝 代码风格

- ESLint + Prettier 自动格式化
- Vue 3 官方风格指南
- TypeScript 严格模式

## 🚢 部署

### Docker 部署

```bash
docker build -t nemo-ui .
docker run -p 80:80 nemo-ui
```

### Nginx 配置

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    root /usr/share/nginx/html;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📄 License

MIT License

## 👥 Contributors

- NEMO Development Team

---

**Version**: 6.0.0  
**Last Updated**: 2025-12-26
