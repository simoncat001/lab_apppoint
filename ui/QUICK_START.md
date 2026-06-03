# 🚀 NEMO 前端快速启动指南

## 第一步：安装依赖

```powershell
cd ui
npm install
```

这将安装以下主要依赖：
- Vue 3.4
- Element Plus 2.5
- Vue Router 4
- Pinia 2
- TypeScript 5
- Vite 5
- Axios

安装时间约 2-5 分钟（取决于网络速度）

## 第二步：启动开发服务器

```powershell
npm run dev
```

服务器启动后，打开浏览器访问：**http://localhost:3000**

## 第三步：登录测试

使用测试账号登录：
- 用户名: `admin`
- 密码: `admin123`

（需要后端 API 已启动在 http://localhost:8000）

## 📁 项目结构说明

```
ui/
├── src/
│   ├── api/            # API 接口调用
│   ├── assets/         # 静态资源
│   ├── components/     # 公共组件
│   ├── router/         # 路由配置
│   ├── stores/         # 状态管理
│   ├── types/          # TS 类型定义
│   ├── utils/          # 工具函数
│   ├── views/          # 页面组件
│   ├── App.vue         # 根组件
│   └── main.ts         # 入口文件
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## 🎯 功能菜单

登录后可以看到以下菜单：

### 主要功能
- **仪表盘** - 数据概览
- **工具管理** - 实验室工具管理
- **预约系统** - 工具预约和日历
- **使用记录** - 工具使用历史
- **任务管理** - 工单系统

### 管理功能（需管理员权限）
- **账户管理** - 用户账户管理
- **员工收费** - 员工服务计费
- **配置管理** - 工具配置管理

## 🔧 开发命令

```powershell
# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview

# 代码检查
npm run lint

# 代码格式化
npm run format
```

## 📝 开发建议

### 1. 使用 VS Code 开发

推荐安装扩展：
- Volar (Vue 语言支持)
- TypeScript Vue Plugin (Volar)
- ESLint
- Prettier

### 2. 热重载

修改代码后自动刷新，无需手动重启服务器。

### 3. TypeScript 支持

所有组件都有完整的类型提示，提高开发效率。

## ⚠️ 注意事项

### 1. 后端依赖

前端需要后端 API 支持，确保后端已启动：

```powershell
# 在 backend 目录
cd d:\Data\Code\NEMO\backend
python main.py
```

### 2. 代理配置

开发环境下，`/api` 请求会自动代理到 `http://localhost:8000`

### 3. 环境变量

如需修改 API 地址，创建 `.env` 文件：

```env
VITE_API_BASE_URL=http://your-api-server:8000/api
```

## 🎨 UI 组件库

项目使用 **Element Plus**，提供丰富的组件：

- 表格 (el-table)
- 表单 (el-form)
- 按钮 (el-button)
- 对话框 (el-dialog)
- 消息提示 (el-message)
- 等等...

文档: https://element-plus.org/zh-CN/

## 🐛 常见问题

### Q: npm install 失败？

A: 尝试：
```powershell
npm cache clean --force
npm install
```

### Q: 端口 3000 被占用？

A: 修改 `vite.config.ts` 中的 `server.port`

### Q: 登录失败？

A: 检查：
1. 后端是否启动
2. 网络请求是否正常（F12 查看 Console）
3. 用户名密码是否正确

### Q: 页面空白？

A: 打开浏览器开发者工具（F12），查看 Console 错误信息。

## 📞 获取帮助

如遇到问题：
1. 查看浏览器控制台（F12）
2. 查看终端错误信息
3. 查看 `PROJECT_STATUS.md` 了解项目状态

---

**开始开发**: `npm run dev`  
**快乐编码** 🎉
