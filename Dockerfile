FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY backend/requirements.txt ./backend/

# 安装Python依赖
RUN pip install --no-cache-dir -r backend/requirements.txt

# 复制应用代码
COPY backend/ ./backend/

# 创建日志目录
RUN mkdir -p backend/logs

# 设置工作目录为backend
WORKDIR /app/backend

# 暴露端口
EXPOSE 8888

# 启动命令（使用新的目录结构）
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
