# NEMO FastAPI 后端 - 快速安装指南

## 📋 前置要求

- Python 3.12+
- MySQL 数据库已设置 (`szlab_appoint`)
- pip

## 🚀 快速开始（3步）

### 1. 进入 backend 目录

```powershell
cd d:\Data\Code\NEMO\backend
```

### 2. 安装依赖

```powershell
pip install -r requirements.txt
```

### 3. 启动服务器

```powershell
python main.py
```

或者使用启动脚本：

```powershell
.\start.ps1
```

## 📖 访问 API 文档

服务启动后，访问：

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **健康检查**: http://localhost:8000/health

## 🔧 配置

复制环境变量示例文件：

```powershell
copy .env.example .env
```

然后编辑 `.env` 文件修改配置（特别是 `MYSQL_*`、`SECRET_KEY`）

## 🐳 使用 Docker（可选）

如果你想使用 Docker：

```powershell
docker-compose up
```

## ✅ 验证安装

### 方法 1: 浏览器

访问 http://localhost:8000 应该看到欢迎信息

### 方法 2: PowerShell

```powershell
curl http://localhost:8000/health
```

### 方法 3: 运行测试

```powershell
pytest
```

## 📝 API 使用示例

### 创建用户

```powershell
curl -X POST "http://localhost:8000/api/users" `
  -H "Content-Type: application/json" `
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "password": "password123"
  }'
```

### 登录获取 Token

```powershell
curl -X POST "http://localhost:8000/api/auth/login" `
  -H "Content-Type: application/x-www-form-urlencoded" `
  -d "username=testuser&password=password123"
```

## 🛠️ 常见问题

### Q: 端口 8000 已被占用？

**A:** 修改 `main.py` 中的端口号：

```python
uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
```

### Q: 数据库连接失败？

**A:** 检查 `.env` 文件中的数据库配置，确保 MySQL 正在运行

```powershell
Get-Service | Where-Object {$_.Name -like "*mysql*"}
```

### Q: 依赖安装失败？

**A:** 尝试升级 pip：

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 📚 下一步

- 查看 `README.md` 了解完整文档
- 查看 API 文档学习所有端点
- 查看 `app/models/` 了解数据模型
- 查看 `app/api/endpoints/` 了解 API 实现

## 🆘 需要帮助？

- 查看 FastAPI 文档: https://fastapi.tiangolo.com/
- 查看项目 README.md
- 检查日志输出

---

**祝你使用愉快！** 🎉
