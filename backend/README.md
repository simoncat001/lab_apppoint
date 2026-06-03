# NEMO FastAPI 后端

现代化、高性能的 NEMO 实验室管理系统后端 API，使用 FastAPI 框架重写。

## 🎯 项目状态

**当前版本**: Phase 1 Complete  
**实现进度**: 15% (11/75 模型)  
**API 端点**: 57 个  
**最后更新**: 2025年12月26日

## ✨ 已实现的功能

### 核心系统
- ✅ **用户管理** - 用户 CRUD、认证、权限
- ✅ **工具管理** - 工具 CRUD、分类、状态
- ✅ **预约系统** - 预约 CRUD、冲突检测
- ✅ **项目管理** - 项目 CRUD、账户关联
- ✅ **账户系统** - 账户管理、类型分类 ⭐ 新增
- ✅ **使用记录** - 工具使用追踪、统计分析 ⭐ 新增
- ✅ **任务系统** - 工单管理、历史追踪 ⭐ 新增

### 技术特性
- ⚡ **异步性能** - 基于 asyncio 的高性能异步操作
- 🔒 **类型安全** - 完整的 Pydantic 验证和类型注解
- 🏗️ **分层架构** - Models → Services → Endpoints
- 🔐 **JWT 认证** - 安全的用户认证和授权
- 📚 **自动文档** - Swagger UI 和 ReDoc
- 🐳 **Docker 支持** - 容器化部署

## 项目简介

这是 NEMO (实验室物流管理系统) 的 FastAPI 后端重写版本。

### 技术栈

- **FastAPI** - 现代、快速的 Web 框架
- **SQLAlchemy 2.0** - ORM (异步支持)
- **PostgreSQL** - 数据库
- **Pydantic** - 数据验证
- **JWT** - 身份认证
- **Uvicorn** - ASGI 服务器

## 项目结构

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/      # API 端点
│   │       │   ├── auth.py     # 认证
│   │       │   ├── users.py    # 用户管理
│   │       │   ├── tools.py    # 工具管理
│   │       │   └── reservations.py  # 预约管理
│   │       └── api.py          # API 路由汇总
│   ├── core/                   # 核心配置
│   │   ├── config.py          # 配置设置
│   │   └── security.py        # 安全工具
│   ├── db/                    # 数据库
│   │   └── session.py         # 数据库会话
│   ├── models/                # SQLAlchemy 模型
│   │   ├── user.py
│   │   ├── tool.py
│   │   ├── reservation.py
│   │   └── project.py
│   ├── schemas/               # Pydantic 模型
│   │   ├── user.py
│   │   ├── tool.py
│   │   ├── reservation.py
│   │   └── project.py
│   └── services/              # 业务逻辑层
│       ├── user_service.py
│       ├── tool_service.py
│       └── reservation_service.py
├── tests/                     # 测试
├── main.py                    # 应用入口
├── requirements.txt           # 依赖
└── .env.example              # 环境变量示例
```

## 快速开始

### 1. 安装依赖

```powershell
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并修改配置：

```powershell
copy .env.example .env
```

### 3. 确保 MySQL 数据库已创建

数据库应该已经存在（从之前的设置）：
- 数据库名: `szlab_appoint`
- 用户: `root`
- 密码: 以 `.env` 为准

### 4. 运行应用

```powershell
python main.py
```

或使用 uvicorn：

```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 访问 API 文档

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- OpenAPI JSON: http://localhost:8000/api/openapi.json

## API 端点

### 认证
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/me` - 获取当前用户信息

### 用户管理
- `GET /api/users` - 获取用户列表
- `GET /api/users/{id}` - 获取用户详情
- `POST /api/users` - 创建用户
- `PUT /api/users/{id}` - 更新用户
- `DELETE /api/users/{id}` - 删除用户

### 工具管理
- `GET /api/tools` - 获取工具列表
- `GET /api/tools/{id}` - 获取工具详情
- `POST /api/tools` - 创建工具
- `PUT /api/tools/{id}` - 更新工具
- `DELETE /api/tools/{id}` - 删除工具

### 预约管理
- `GET /api/reservations` - 获取预约列表
- `GET /api/reservations/{id}` - 获取预约详情
- `POST /api/reservations` - 创建预约
- `PUT /api/reservations/{id}` - 更新预约
- `DELETE /api/reservations/{id}` - 取消预约

## 开发

### 运行测试

```powershell
pytest
```

### 代码格式化

```powershell
black app/
```

### 类型检查

```powershell
mypy app/
```

## 特性

- ✅ **异步支持** - 使用 async/await 提高性能
- ✅ **自动文档** - Swagger UI 和 ReDoc
- ✅ **数据验证** - Pydantic 模型
- ✅ **JWT 认证** - 安全的用户认证
- ✅ **CORS 支持** - 跨域资源共享
- ✅ **服务层架构** - 清晰的业务逻辑分离
- ✅ **类型提示** - 完整的类型注解

## 与原 Django 版本的对比

| 特性 | Django | FastAPI |
|------|--------|---------|
| 性能 | 同步 | 异步 (更快) |
| API 文档 | 需要额外配置 | 自动生成 |
| 类型安全 | 弱 | 强 (Pydantic) |
| 学习曲线 | 陡峭 | 平缓 |
| 生态系统 | 丰富 | 快速增长 |

## 下一步

- [ ] 添加更多模型 (Area, Task, UsageEvent 等)
- [ ] 实现完整的权限系统
- [ ] 添加 WebSocket 支持实时通知
- [ ] 实现缓存层 (Redis)
- [ ] 添加完整的测试覆盖
- [ ] Docker 容器化部署
- [ ] CI/CD 配置

## 许可

与原 NEMO 项目相同
