#!/bin/bash
# =============================================================================
# PostgreSQL 数据库备份脚本
# =============================================================================
# 用法:
#   ./scripts/backup.sh              # 立即执行备份 (覆盖已有备份)
#   ./scripts/backup.sh --schedule   # 安装定时备份 (每天凌晨3点)
#   ./scripts/backup.sh --restore    # 从备份恢复
#   ./scripts/backup.sh --info       # 查看备份信息
# =============================================================================

set -e

# 配置
BACKUP_DIR="${BACKUP_DIR:-./backups}"
CONTAINER_DEV="quant-postgres-dev"
CONTAINER_PROD="quant-postgres"
DB_USER="quant"
DB_NAME="quant"
BACKUP_FILE="${BACKUP_DIR}/quant_backup.sql.gz"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检测运行中的容器
detect_container() {
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_DEV}$"; then
        echo "$CONTAINER_DEV"
    elif docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_PROD}$"; then
        echo "$CONTAINER_PROD"
    else
        log_error "没有找到运行中的 PostgreSQL 容器"
        exit 1
    fi
}

# 执行备份 (覆盖模式，只保留一份)
do_backup() {
    local container=$(detect_container)

    mkdir -p "$BACKUP_DIR"

    log_info "开始备份数据库..."
    log_info "容器: $container"
    log_info "目标: $BACKUP_FILE"

    # 使用 pg_dump 导出并压缩，直接覆盖
    docker exec "$container" pg_dump -U "$DB_USER" -d "$DB_NAME" \
        --no-owner --no-acl \
        | gzip > "$BACKUP_FILE"

    local size=$(du -h "$BACKUP_FILE" | cut -f1)
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    log_info "备份完成: $BACKUP_FILE ($size)"
    log_info "备份时间: $timestamp"
}

# 恢复备份
do_restore() {
    if [[ ! -f "$BACKUP_FILE" ]]; then
        log_error "备份文件不存在: $BACKUP_FILE"
        exit 1
    fi

    local container=$(detect_container)

    log_warn "即将恢复数据库，这将覆盖现有数据!"
    log_warn "容器: $container"
    log_warn "备份: $BACKUP_FILE"
    read -p "确认继续? (yes/no): " confirm

    if [[ "$confirm" != "yes" ]]; then
        log_info "已取消"
        exit 0
    fi

    log_info "开始恢复数据库..."
    gunzip -c "$BACKUP_FILE" | docker exec -i "$container" psql -U "$DB_USER" -d "$DB_NAME"
    log_info "恢复完成!"
}

# 查看备份信息
show_info() {
    if [[ -f "$BACKUP_FILE" ]]; then
        local size=$(du -h "$BACKUP_FILE" | cut -f1)
        local mtime=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$BACKUP_FILE" 2>/dev/null || stat -c "%y" "$BACKUP_FILE" 2>/dev/null | cut -d'.' -f1)
        log_info "备份文件: $BACKUP_FILE"
        log_info "文件大小: $size"
        log_info "备份时间: $mtime"
    else
        log_warn "暂无备份文件"
    fi
}

# 安装定时任务
install_schedule() {
    local script_path="$(cd "$(dirname "$0")" && pwd)/backup.sh"
    local log_file="${BACKUP_DIR}/backup.log"
    local cron_job="0 3 * * * $script_path >> $log_file 2>&1"

    # 检查是否已安装
    if crontab -l 2>/dev/null | grep -q "$script_path"; then
        log_warn "定时任务已存在"
        crontab -l | grep "$script_path"
        return
    fi

    # 添加定时任务
    (crontab -l 2>/dev/null; echo "$cron_job") | crontab -

    log_info "已安装定时备份任务 (每天凌晨3点)"
    log_info "查看: crontab -l"
    log_info "日志: $log_file"
}

# 卸载定时任务
uninstall_schedule() {
    local script_path="$(cd "$(dirname "$0")" && pwd)/backup.sh"

    if ! crontab -l 2>/dev/null | grep -q "$script_path"; then
        log_warn "定时任务不存在"
        return
    fi

    crontab -l 2>/dev/null | grep -v "$script_path" | crontab -
    log_info "已卸载定时备份任务"
}

# 主函数
main() {
    case "${1:-}" in
        --restore)
            do_restore
            ;;
        --info)
            show_info
            ;;
        --schedule)
            install_schedule
            ;;
        --unschedule)
            uninstall_schedule
            ;;
        --help|-h)
            echo "PostgreSQL 数据库备份工具 (单文件覆盖模式)"
            echo ""
            echo "用法:"
            echo "  $0              立即执行备份 (覆盖已有备份)"
            echo "  $0 --restore    从备份恢复"
            echo "  $0 --info       查看备份信息"
            echo "  $0 --schedule   安装定时备份 (每天凌晨3点)"
            echo "  $0 --unschedule 卸载定时备份"
            echo ""
            echo "备份文件: $BACKUP_FILE"
            ;;
        *)
            do_backup
            ;;
    esac
}

main "$@"
