@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo   专家团 - Windows 启动脚本
echo ========================================
echo.

:: 设置项目根目录
set "PROJECT_DIR=%~dp0"
set "BACKEND_DIR=%PROJECT_DIR%backend"
set "FRONTEND_DIR=%PROJECT_DIR%frontend"

:: 检查 conda 环境
echo [1/6] 检查 Conda 环境...
call conda activate Test 2>nul
if errorlevel 1 (
    echo [错误] 无法激活 Conda 环境 "Test"
    echo 请确保已安装 Anaconda/Miniconda 并创建了 Test 环境
    echo 创建命令: conda create -n Test python=3.11
    pause
    exit /b 1
)
echo [成功] Conda 环境 "Test" 已激活

:: 检查 Python 版本
echo.
echo [2/6] 检查 Python 版本...
python --version
if errorlevel 1 (
    echo [错误] Python 未安装或不可用
    pause
    exit /b 1
)

:: 检查 Node.js 版本
echo.
echo [3/6] 检查 Node.js 版本...
node --version
if errorlevel 1 (
    echo [错误] Node.js 未安装或不可用
    echo 请安装 Node.js 18+: https://nodejs.org/
    pause
    exit /b 1
)
npm --version

:: 安装后端依赖
echo.
echo [4/6] 安装后端依赖...
cd /d "%BACKEND_DIR%"
if not exist "requirements.txt" (
    echo [错误] 未找到 requirements.txt
    pause
    exit /b 1
)
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo [错误] 后端依赖安装失败
    pause
    exit /b 1
)
echo [成功] 后端依赖安装完成

:: 检查并创建 .env 文件
if not exist ".env" (
    echo [提示] 未找到 .env 文件，正在创建...
    if exist ".env.example" (
        copy .env.example .env
        echo [成功] 已从 .env.example 创建 .env
        echo [重要] 请编辑 .env 文件配置 ENCRYPTION_KEY
        echo 生成密钥命令: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ) else (
        echo [警告] 未找到 .env.example，请手动创建 .env 文件
    )
)

:: 初始化数据库
echo.
echo [5/6] 初始化数据库...
python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"
if errorlevel 1 (
    echo [提示] 数据库初始化尝试完成（如果已存在则跳过）
)
echo [成功] 数据库初始化完成

:: 安装前端依赖
echo.
echo [6/6] 安装前端依赖...
cd /d "%FRONTEND_DIR%"
if not exist "package.json" (
    echo [错误] 未找到 package.json
    pause
    exit /b 1
)
if not exist "node_modules" (
    echo 正在安装前端依赖...
    npm install
    if errorlevel 1 (
        echo [错误] 前端依赖安装失败
        pause
        exit /b 1
    )
) else (
    echo [跳过] node_modules 已存在
)
echo [成功] 前端依赖安装完成

:: 启动服务
echo.
echo ========================================
echo   启动服务
echo ========================================
echo.

:: 启动后端（新窗口）
echo 启动后端服务...
start "专家团-后端" cmd /k "cd /d "%BACKEND_DIR%" && conda activate Test && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:: 等待后端启动
echo 等待后端服务启动...
timeout /t 3 /nobreak >nul

:: 启动前端（新窗口）
echo 启动前端服务...
start "专家团-前端" cmd /k "cd /d "%FRONTEND_DIR%" && npm run dev"

echo.
echo ========================================
echo   服务启动完成
echo ========================================
echo.
echo 后端地址: http://localhost:8000
echo 前端地址: http://localhost:5173
echo API 文档: http://localhost:8000/docs
echo.
echo 按任意键打开浏览器...
pause >nul

:: 打开浏览器
start http://localhost:5173

echo.
echo 提示: 关闭此窗口不会停止服务
echo 要停止服务，请关闭"专家团-后端"和"专家团-前端"窗口
echo.
pause
