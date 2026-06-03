# NEMO FastAPI Backend Startup Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "NEMO FastAPI Backend" -ForegroundColor Cyan  
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查是否在 backend 目录
if (-not (Test-Path "main.py")) {
    Write-Host "错误: 请在 backend 目录中运行此脚本" -ForegroundColor Red
    Write-Host "使用: cd backend; .\start.ps1" -ForegroundColor Yellow
    exit 1
}

# 检查 .env 文件
if (-not (Test-Path ".env")) {
    Write-Host "警告: 未找到 .env 文件" -ForegroundColor Yellow
    Write-Host "正在从 .env.example 复制..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✓ 已创建 .env 文件，请根据需要修改配置" -ForegroundColor Green
    Write-Host ""
}

# 检查依赖
Write-Host "检查 FastAPI 是否已安装..." -ForegroundColor Yellow
$fastapi = python -c "import fastapi; print('installed')" 2>$null

if ($fastapi -ne "installed") {
    Write-Host "FastAPI 未安装" -ForegroundColor Yellow
    $install = Read-Host "是否安装依赖? (y/N)"
    
    if ($install -eq "y" -or $install -eq "Y") {
        Write-Host "正在安装依赖..." -ForegroundColor Yellow
        pip install -r requirements.txt
    } else {
        Write-Host "已取消" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "启动 FastAPI 服务器..." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "API 文档: http://localhost:8000/api/docs" -ForegroundColor Cyan
Write-Host "健康检查: http://localhost:8000/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "按 Ctrl+C 停止服务器" -ForegroundColor Yellow
Write-Host ""

# 启动服务器
python main.py
