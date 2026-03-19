@echo off
chcp 65001 >nul
echo ========================================
echo   Super Agent - Web 服务启动
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

REM 检查 .env 文件
if not exist .env (
    echo [警告] 未找到 .env 文件
    echo 请确保已配置 SILICONFLOW_API_KEY 环境变量
    echo.
)

REM 检查依赖
echo [1/3] 检查依赖...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [安装] 正在安装 FastAPI...
    pip install fastapi uvicorn
)

REM 初始化测试数据库
echo [2/3] 初始化测试数据库...
if not exist data\test.db (
    python data\init_db.py
)

REM 启动服务
echo [3/3] 启动 Web 服务...
echo.
echo 服务地址: http://localhost:8000
echo API 文档: http://localhost:8000/docs
echo.
echo 按 Ctrl+C 停止服务
echo.

python -m uvicorn src.web.main:app --host 0.0.0.0 --port 8000 --reload
