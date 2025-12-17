@echo off
chcp 65001 >nul
echo ========================================
echo MySQL数据库表转服务
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.11+
    pause
    exit /b 1
)

REM 检查依赖是否安装
echo [信息] 检查依赖...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [信息] 正在安装依赖...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

REM 检查.env文件
if not exist .env (
    if exist ..\.env (
        echo [信息] 使用项目根目录的.env文件
    ) else (
        echo [警告] 未找到.env文件，请先配置数据库连接信息
        echo [提示] 可以复制.env.example为.env并修改配置
        pause
    )
)

REM 创建logs目录
if not exist logs mkdir logs

REM 启动服务
echo [信息] 启动服务...
echo.
cd /d %~dp0
python -m uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload

pause

