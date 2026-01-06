# MCP 服务 Dockerfile
# 用于 MCP 服务器（factor-hub, data-hub, strategy-hub）

FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件（利用 Docker 层缓存）
COPY pyproject.toml ./

# 创建最小包结构让 pip install -e 工作
RUN mkdir -p backend/app && touch backend/app/__init__.py && touch README.md

# 安装 Python 依赖（只有 pyproject.toml 变化才重建此层）
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir \
    psycopg2-binary \
    redis

# 最后复制代码（开发模式会通过 volume 覆盖）
COPY backend/ ./backend/
COPY config/ ./config/
COPY factors/ ./factors/

# 复制 supervisor 配置
COPY docker/mcp/supervisord.conf /etc/supervisor/conf.d/mcp.conf

# 设置环境变量
ENV PYTHONPATH=/app:/app/backend
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 6789 6790 6791 6792

# 健康检查（检查 factor-hub）
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:6789/health || exit 1

# 启动 supervisor
CMD ["supervisord", "-n", "-c", "/etc/supervisor/conf.d/mcp.conf"]
