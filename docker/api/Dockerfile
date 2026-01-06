# API 服务 Dockerfile
# 多阶段构建：开发和生产共用依赖层

# ============================================
# 基础阶段：安装所有依赖（开发/生产共用）
# ============================================
FROM python:3.11-slim AS base

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件（利用 Docker 层缓存）
COPY pyproject.toml ./

# 创建最小包结构让 pip install -e 工作
# README.md 是 pyproject.toml 的 dynamic 字段依赖，创建空文件即可
RUN mkdir -p backend/app && touch backend/app/__init__.py && touch README.md

# 安装 Python 依赖（只有 pyproject.toml 变化才重建此层）
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir \
    gunicorn \
    psycopg2-binary \
    redis \
    arq

# 最后复制代码（开发模式会通过 volume 覆盖）
COPY backend/ ./backend/
COPY config/ ./config/

# 设置环境变量
ENV PYTHONPATH=/app:/app/backend
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8000

# ============================================
# 生产阶段：添加生产配置
# ============================================
FROM base AS production

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 生产启动命令（gunicorn）
CMD ["gunicorn", "app.main:app", \
     "-w", "2", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
