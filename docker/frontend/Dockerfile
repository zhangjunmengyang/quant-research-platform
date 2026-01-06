# 前端 Dockerfile
# 多阶段构建：构建阶段 + 生产阶段

# === 构建阶段 ===
FROM node:20-alpine AS builder

WORKDIR /app

# 安装 pnpm
RUN npm install -g pnpm

# 复制 monorepo 根目录的配置文件
COPY pnpm-workspace.yaml package.json pnpm-lock.yaml ./

# 复制前端的 package.json
COPY frontend/package.json ./frontend/

# 安装依赖
RUN pnpm install --frozen-lockfile

# 复制前端源代码
COPY frontend/ ./frontend/

# 构建生产版本
WORKDIR /app/frontend
RUN pnpm build

# === 生产阶段 ===
FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/frontend/dist /usr/share/nginx/html

# 复制 nginx 配置
COPY docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1
