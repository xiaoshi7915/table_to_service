#!/bin/bash

# 表转服务管理系统 - 一键启动/停止/重启前后端服务
# 使用方法: ./service_manager.sh [start|stop|restart|status]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
PID_FILE_BACKEND="$SCRIPT_DIR/.backend.pid"
PID_FILE_FRONTEND="$SCRIPT_DIR/.frontend.pid"
LOG_FILE_BACKEND="$SCRIPT_DIR/logs/backend.log"
LOG_FILE_FRONTEND="$SCRIPT_DIR/logs/frontend.log"

# 创建日志目录
mkdir -p "$SCRIPT_DIR/logs"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[信息]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[成功]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[警告]${NC} $1"
}

print_error() {
    echo -e "${RED}[错误]${NC} $1"
}

# 检查进程是否运行（通过PID文件和进程特征）
is_process_running() {
    local pid_file=$1
    local process_pattern=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            # 检查进程是否匹配我们的服务特征
            if [ -n "$process_pattern" ]; then
                if ps -p "$pid" -o cmd= | grep -q "$process_pattern"; then
                    return 0
                else
                    # PID存在但进程不匹配，清理PID文件
                    rm -f "$pid_file"
                    return 1
                fi
            fi
            return 0
        else
            rm -f "$pid_file"
            return 1
        fi
    fi
    return 1
}

# 检查端口是否被占用
is_port_in_use() {
    local port=$1
    if netstat -tlnp 2>/dev/null | grep -q ":$port " || ss -tlnp 2>/dev/null | grep -q ":$port "; then
        return 0
    fi
    return 1
}

# 查找运行在指定端口的进程
find_process_by_port() {
    local port=$1
    local pid=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 | head -1)
    if [ -z "$pid" ]; then
        pid=$(ss -tlnp 2>/dev/null | grep ":$port " | grep -oP 'pid=\K\d+' | head -1)
    fi
    echo "$pid"
}

# 启动后端服务
start_backend() {
    # 检查端口是否被占用
    if is_port_in_use 8300; then
        local existing_pid=$(find_process_by_port 8300)
        if [ -n "$existing_pid" ]; then
            # 检查是否是我们的服务
            local cmd=$(ps -p "$existing_pid" -o cmd= 2>/dev/null)
            if echo "$cmd" | grep -q "table_to_service.*uvicorn.*8300"; then
                print_warning "后端服务已在运行中 (PID: $existing_pid)"
                echo "$existing_pid" > "$PID_FILE_BACKEND"
                return 1
            else
                print_error "端口8300已被其他进程占用 (PID: $existing_pid)"
                print_info "进程信息: $cmd"
                return 1
            fi
        fi
    fi
    
    # 检查PID文件中的进程
    if is_process_running "$PID_FILE_BACKEND" "table_to_service.*uvicorn.*8300"; then
        print_warning "后端服务已在运行中 (PID: $(cat $PID_FILE_BACKEND))"
        return 1
    fi
    
    print_info "启动后端服务..."
    
    if [ ! -d "$BACKEND_DIR/venv" ]; then
        print_error "后端虚拟环境不存在，请先运行安装脚本"
        return 1
    fi
    
    # 创建日志目录
    mkdir -p "$(dirname "$LOG_FILE_BACKEND")"
    
    cd "$BACKEND_DIR" || exit 1
    
    # 激活虚拟环境并启动服务（使用绝对路径确保正确）
    # 注意：使用 tr 命令过滤掉 NUL 字符（\0），避免二进制数据污染日志文件
    nohup bash -c "cd '$BACKEND_DIR' && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8300 --reload 2>&1 | tr -d '\0' > '$LOG_FILE_BACKEND'" &
    local pid=$!
    echo $pid > "$PID_FILE_BACKEND"
    
    sleep 3
    
    # 检查进程是否还在运行
    if ps -p "$pid" > /dev/null 2>&1; then
        # 再次检查端口
        sleep 2
        if is_port_in_use 8300; then
            print_success "后端服务启动成功 (PID: $pid)"
            print_info "后端服务地址: http://121.36.205.70:8300"
            print_info "API文档地址: http://121.36.205.70:8300/docs"
            print_info "日志文件: $LOG_FILE_BACKEND"
            return 0
        else
            print_error "后端服务进程启动但端口未监听，请查看日志: $LOG_FILE_BACKEND"
            rm -f "$PID_FILE_BACKEND"
            return 1
        fi
    else
        print_error "后端服务启动失败，请查看日志: $LOG_FILE_BACKEND"
        if [ -f "$LOG_FILE_BACKEND" ]; then
            print_info "最后10行日志:"
            tail -10 "$LOG_FILE_BACKEND"
        fi
        rm -f "$PID_FILE_BACKEND"
        return 1
    fi
}

# 启动前端服务
start_frontend() {
    # 检查端口是否被占用
    if is_port_in_use 3003; then
        local existing_pid=$(find_process_by_port 3003)
        if [ -n "$existing_pid" ]; then
            # 检查是否是我们的服务
            local cmd=$(ps -p "$existing_pid" -o cmd= 2>/dev/null)
            if echo "$cmd" | grep -q "table_to_service.*vite.*3003"; then
                print_warning "前端服务已在运行中 (PID: $existing_pid)"
                echo "$existing_pid" > "$PID_FILE_FRONTEND"
                return 1
            else
                print_error "端口3003已被其他进程占用 (PID: $existing_pid)"
                print_info "进程信息: $cmd"
                return 1
            fi
        fi
    fi
    
    # 检查PID文件中的进程
    if is_process_running "$PID_FILE_FRONTEND" "table_to_service.*vite.*3003"; then
        print_warning "前端服务已在运行中 (PID: $(cat $PID_FILE_FRONTEND))"
        return 1
    fi
    
    print_info "启动前端服务..."
    
    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        print_warning "前端依赖未安装，正在安装..."
        cd "$FRONTEND_DIR" || exit 1
        npm install
        if [ $? -ne 0 ]; then
            print_error "前端依赖安装失败"
            return 1
        fi
    fi
    
    # 创建日志目录
    mkdir -p "$(dirname "$LOG_FILE_FRONTEND")"
    
    cd "$FRONTEND_DIR" || exit 1
    
    # 启动前端服务（使用绝对路径）
    nohup bash -c "cd '$FRONTEND_DIR' && npm run dev" > "$LOG_FILE_FRONTEND" 2>&1 &
    local pid=$!
    echo $pid > "$PID_FILE_FRONTEND"
    
    sleep 4
    
    # 检查进程是否还在运行
    if ps -p "$pid" > /dev/null 2>&1; then
        # 再次检查端口
        sleep 2
        if is_port_in_use 3003; then
            print_success "前端服务启动成功 (PID: $pid)"
            print_info "前端服务地址: http://121.36.205.70:3003"
            print_info "日志文件: $LOG_FILE_FRONTEND"
            return 0
        else
            print_error "前端服务进程启动但端口未监听，请查看日志: $LOG_FILE_FRONTEND"
            rm -f "$PID_FILE_FRONTEND"
            return 1
        fi
    else
        print_error "前端服务启动失败，请查看日志: $LOG_FILE_FRONTEND"
        if [ -f "$LOG_FILE_FRONTEND" ]; then
            print_info "最后10行日志:"
            tail -10 "$LOG_FILE_FRONTEND"
        fi
        rm -f "$PID_FILE_FRONTEND"
        return 1
    fi
}

# 停止后端服务
stop_backend() {
    # 查找运行在8300端口的进程
    local port_pid=$(find_process_by_port 8300)
    
    # 查找PID文件中的进程
    local file_pid=""
    if [ -f "$PID_FILE_BACKEND" ]; then
        file_pid=$(cat "$PID_FILE_BACKEND")
    fi
    
    if [ -z "$port_pid" ] && [ -z "$file_pid" ]; then
        print_warning "后端服务未运行"
        rm -f "$PID_FILE_BACKEND"
        return 1
    fi
    
    print_info "停止后端服务..."
    
    # 停止端口上的进程
    if [ -n "$port_pid" ]; then
        local cmd=$(ps -p "$port_pid" -o cmd= 2>/dev/null)
        if echo "$cmd" | grep -q "table_to_service\|8300"; then
            print_info "停止进程 (PID: $port_pid)"
            kill -TERM "$port_pid" 2>/dev/null
            # 同时停止进程组
            kill -TERM -$port_pid 2>/dev/null
        fi
    fi
    
    # 停止PID文件中的进程
    if [ -n "$file_pid" ] && [ "$file_pid" != "$port_pid" ]; then
        if ps -p "$file_pid" > /dev/null 2>&1; then
            print_info "停止进程 (PID: $file_pid)"
            kill -TERM "$file_pid" 2>/dev/null
            kill -TERM -$file_pid 2>/dev/null
        fi
    fi
    
    sleep 2
    
    # 强制杀死仍在运行的进程
    port_pid=$(find_process_by_port 8300)
    if [ -n "$port_pid" ]; then
        local cmd=$(ps -p "$port_pid" -o cmd= 2>/dev/null)
        if echo "$cmd" | grep -q "table_to_service\|8300"; then
            kill -9 "$port_pid" 2>/dev/null
            kill -9 -$port_pid 2>/dev/null
        fi
    fi
    
    # 清理PID文件
    rm -f "$PID_FILE_BACKEND"
    
    sleep 1
    
    # 检查端口是否还在使用
    if ! is_port_in_use 8300; then
        print_success "后端服务已停止"
        return 0
    else
        print_error "后端服务停止失败，端口8300仍被占用"
        return 1
    fi
}

# 停止前端服务
stop_frontend() {
    # 查找运行在3003端口的进程
    local port_pid=$(find_process_by_port 3003)
    
    # 查找PID文件中的进程
    local file_pid=""
    if [ -f "$PID_FILE_FRONTEND" ]; then
        file_pid=$(cat "$PID_FILE_FRONTEND")
    fi
    
    if [ -z "$port_pid" ] && [ -z "$file_pid" ]; then
        print_warning "前端服务未运行"
        rm -f "$PID_FILE_FRONTEND"
        return 1
    fi
    
    print_info "停止前端服务..."
    
    # 停止端口上的进程
    if [ -n "$port_pid" ]; then
        local cmd=$(ps -p "$port_pid" -o cmd= 2>/dev/null)
        if echo "$cmd" | grep -q "table_to_service\|3003"; then
            print_info "停止进程 (PID: $port_pid)"
            kill -TERM "$port_pid" 2>/dev/null
            # 同时停止进程组
            kill -TERM -$port_pid 2>/dev/null
        fi
    fi
    
    # 停止PID文件中的进程
    if [ -n "$file_pid" ] && [ "$file_pid" != "$port_pid" ]; then
        if ps -p "$file_pid" > /dev/null 2>&1; then
            print_info "停止进程 (PID: $file_pid)"
            kill -TERM "$file_pid" 2>/dev/null
            kill -TERM -$file_pid 2>/dev/null
        fi
    fi
    
    sleep 2
    
    # 强制杀死仍在运行的进程
    port_pid=$(find_process_by_port 3003)
    if [ -n "$port_pid" ]; then
        local cmd=$(ps -p "$port_pid" -o cmd= 2>/dev/null)
        if echo "$cmd" | grep -q "table_to_service\|3003"; then
            kill -9 "$port_pid" 2>/dev/null
            kill -9 -$port_pid 2>/dev/null
        fi
    fi
    
    # 清理PID文件
    rm -f "$PID_FILE_FRONTEND"
    
    sleep 1
    
    # 检查端口是否还在使用
    if ! is_port_in_use 3003; then
        print_success "前端服务已停止"
        return 0
    else
        print_error "前端服务停止失败，端口3003仍被占用"
        return 1
    fi
}

# 查看服务状态
show_status() {
    echo ""
    echo "=========================================="
    echo "服务状态"
    echo "=========================================="
    echo ""
    
    # 后端状态 - 通过端口检查
    local backend_pid=$(find_process_by_port 8300)
    if [ -n "$backend_pid" ]; then
        local cmd=$(ps -p "$backend_pid" -o cmd= 2>/dev/null)
        # 检查是否是我们的服务
        if echo "$cmd" | grep -q "table_to_service\|8300"; then
            print_success "后端服务: 运行中 (PID: $backend_pid)"
            print_info "  访问地址: http://121.36.205.70:8300"
            print_info "  API文档: http://121.36.205.70:8300/docs"
            print_info "  日志文件: $LOG_FILE_BACKEND"
            if [ -f "$LOG_FILE_BACKEND" ]; then
                local log_size=$(stat -c%s "$LOG_FILE_BACKEND" 2>/dev/null || echo "0")
                if [ "$log_size" -gt 0 ]; then
                    print_info "  日志大小: $(du -h "$LOG_FILE_BACKEND" | cut -f1)"
                fi
            fi
        else
            print_warning "后端服务: 端口8300被其他进程占用 (PID: $backend_pid)"
            print_info "  进程信息: $cmd"
        fi
    else
        print_error "后端服务: 未运行"
        if [ -f "$PID_FILE_BACKEND" ]; then
            rm -f "$PID_FILE_BACKEND"
        fi
    fi
    
    echo ""
    
    # 前端状态 - 通过端口检查
    local frontend_pid=$(find_process_by_port 3003)
    if [ -n "$frontend_pid" ]; then
        local cmd=$(ps -p "$frontend_pid" -o cmd= 2>/dev/null)
        # 检查是否是我们的服务
        if echo "$cmd" | grep -q "table_to_service\|3003"; then
            print_success "前端服务: 运行中 (PID: $frontend_pid)"
            print_info "  访问地址: http://121.36.205.70:3003"
            print_info "  日志文件: $LOG_FILE_FRONTEND"
            if [ -f "$LOG_FILE_FRONTEND" ]; then
                local log_size=$(stat -c%s "$LOG_FILE_FRONTEND" 2>/dev/null || echo "0")
                if [ "$log_size" -gt 0 ]; then
                    print_info "  日志大小: $(du -h "$LOG_FILE_FRONTEND" | cut -f1)"
                fi
            fi
        else
            print_warning "前端服务: 端口3003被其他进程占用 (PID: $frontend_pid)"
            print_info "  进程信息: $cmd"
        fi
    else
        print_error "前端服务: 未运行"
        if [ -f "$PID_FILE_FRONTEND" ]; then
            rm -f "$PID_FILE_FRONTEND"
        fi
    fi
    
    echo ""
    echo "=========================================="
}

# 启动所有服务
start_all() {
    echo "=========================================="
    echo "启动所有服务"
    echo "=========================================="
    echo ""
    
    start_backend
    echo ""
    start_frontend
    echo ""
    
    show_status
}

# 停止所有服务
stop_all() {
    echo "=========================================="
    echo "停止所有服务"
    echo "=========================================="
    echo ""
    
    stop_frontend
    echo ""
    stop_backend
    echo ""
    
    print_info "所有服务已停止"
}

# 重启所有服务
restart_all() {
    echo "=========================================="
    echo "重启所有服务"
    echo "=========================================="
    echo ""
    
    stop_all
    echo ""
    sleep 2
    start_all
}

# 主函数
main() {
    case "${1:-}" in
        start)
            start_all
            ;;
        stop)
            stop_all
            ;;
        restart)
            restart_all
            ;;
        status)
            show_status
            ;;
        start-backend)
            start_backend
            ;;
        stop-backend)
            stop_backend
            ;;
        start-frontend)
            start_frontend
            ;;
        stop-frontend)
            stop_frontend
            ;;
        *)
            echo "使用方法: $0 {start|stop|restart|status|start-backend|stop-backend|start-frontend|stop-frontend}"
            echo ""
            echo "命令说明:"
            echo "  start           - 启动所有服务（后端+前端）"
            echo "  stop            - 停止所有服务"
            echo "  restart         - 重启所有服务"
            echo "  status          - 查看服务状态"
            echo "  start-backend   - 仅启动后端服务"
            echo "  stop-backend    - 仅停止后端服务"
            echo "  start-frontend  - 仅启动前端服务"
            echo "  stop-frontend   - 仅停止前端服务"
            exit 1
            ;;
    esac
}

main "$@"

