@echo off
chcp 65001 >nul
title AI 老照片时光机 - 一键启动

echo ============================================
echo   AI 老照片时光机 - 一键启动
echo   TRAE AI 创造力大赛 · 生活娱乐赛道
echo ============================================
echo.

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

:: Check Node
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)

:: Check FFmpeg
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 未找到 FFmpeg，视频合成功能将不可用
    echo        请从 https://ffmpeg.org/download.html 下载并添加到 PATH
    echo.
)

:: Install backend dependencies
echo [1/4] 检查后端依赖...
cd /d "%~dp0backend"
pip install -q -r requirements.txt 2>nul

:: Install frontend dependencies
echo [2/4] 检查前端依赖...
cd /d "%~dp0frontend"
if not exist "node_modules" (
    echo       首次运行，安装前端依赖（可能需要几分钟）...
    call npm install
) else (
    echo       前端依赖已就绪
)

:: Start backend
echo [3/4] 启动后端服务 (端口 8000)...
cd /d "%~dp0backend"
start "后端 - FastAPI" cmd /k "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait for backend
timeout /t 3 /nobreak >nul

:: Start frontend
echo [4/4] 启动前端服务 (端口 5173)...
cd /d "%~dp0frontend"
start "前端 - Vite" cmd /k "npx vite --host"

:: Wait and open browser
timeout /t 3 /nobreak >nul
echo.
echo ============================================
echo   启动完成！
echo   前端地址: http://localhost:5173
echo   后端API:  http://localhost:8000
echo   API文档:  http://localhost:8000/docs
echo ============================================
echo.
echo 按任意键打开浏览器...
pause >nul
start http://localhost:5173
