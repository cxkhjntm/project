#!/bin/bash
# ========================================
#   专家团 - Linux 启动脚本
# ========================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_success() { echo -e "${GREEN}[成功]${NC} $1"; }
print_error() { echo -e "${RED}[错误]${NC} $1"; }
print_info() { echo -e "${BLUE}[信息]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[警告]${NC} $1"; }

echo "========================================"
echo "  专家团 - Linux 启动脚本"
echo "========================================"
echo

# 设置项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# 检查 Python
print_info "[1/6] 检查 Python 版本..."
if ! command -v python3 &> /dev/null; then
    print_error "Python3 未安装"
    echo "请安装 Python 3.11+:"
    echo "  Ubuntu/Debian: sudo apt install python3.11 python3.11-venv python3.11-dev"
    echo "  CentOS/RHEL: sudo yum install python3.11"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
print_success "Python 版本: $PYTHON_VERSION"

# 检查 pip
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 未安装"
    echo "请安装 pip: sudo apt install python3-pip"
    exit 1
fi

# 检查 Node.js
print_info "[2/6] 检查 Node.js 版本..."
if ! command -v node &> /dev/null; then
    print_error "Node.js 未安装"
    echo "请安装 Node.js 18+:"
    echo "  curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -"
    echo "  sudo apt install -y nodejs"
    exit 1
fi

NODE_VERSION=$(node --version)
NPM_VERSION=$(npm --version)
print_success "Node.js 版本: $NODE_VERSION"
print_success "npm 版本: $NPM_VERSION"

# 安装后端依赖
print_info "[3/6] 安装后端依赖..."
cd "$BACKEND_DIR"

if [ ! -f "requirements.txt" ]; then
    print_error "未找到 requirements.txt"
    exit 1
fi

# 创建虚拟环境（如果不存在）
if [ ! -d ".venv" ]; then
    print_info "创建 Python 虚拟环境..."
    python3 -m venv .venv
    print_success "虚拟环境创建完成"
fi

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
print_success "后端依赖安装完成"

# 检查并创建 .env 文件
if [ ! -f ".env" ]; then
    print_warning "未找到 .env 文件，正在创建..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success "已从 .env.example 创建 .env"
        print_warning "重要: 请编辑 .env 文件配置 ENCRYPTION_KEY"
        echo "生成密钥命令: python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    else
        print_error "未找到 .env.example，请手动创建 .env 文件"
        exit 1
    fi
fi

# 初始化数据库
print_info "[4/6] 初始化数据库..."
python3 -c "from app.database import init_db; import asyncio; asyncio.run(init_db())" 2>/dev/null || true
print_success "数据库初始化完成"

# 安装前端依赖
print_info "[5/6] 安装前端依赖..."
cd "$FRONTEND_DIR"

if [ ! -f "package.json" ]; then
    print_error "未找到 package.json"
    exit 1
fi

if [ ! -d "node_modules" ]; then
    print_info "安装前端依赖..."
    npm install
    print_success "前端依赖安装完成"
else
    print_info "node_modules 已存在，跳过安装"
fi

# 启动服务
print_info "[6/6] 启动服务..."
echo
echo "========================================"
echo "  启动服务"
echo "========================================"
echo

# 启动后端（后台运行）
print_info "启动后端服务..."
cd "$BACKEND_DIR"
source .venv/bin/activate
nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > "$PROJECT_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$PROJECT_DIR/backend.pid"
print_success "后端服务已启动 (PID: $BACKEND_PID)"

# 等待后端启动
print_info "等待后端服务启动..."
sleep 3

# 检查后端是否启动成功
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    print_success "后端服务启动成功"
else
    print_warning "后端服务可能仍在启动中..."
fi

# 启动前端（后台运行）
print_info "启动前端服务..."
cd "$FRONTEND_DIR"
nohup npm run dev > "$PROJECT_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$PROJECT_DIR/frontend.pid"
print_success "前端服务已启动 (PID: $FRONTEND_PID)"

# 等待前端启动
sleep 2

echo
echo "========================================"
echo "  服务启动完成"
echo "========================================"
echo
echo -e "${GREEN}后端地址:${NC} http://localhost:8000"
echo -e "${GREEN}前端地址:${NC} http://localhost:5173"
echo -e "${GREEN}API 文档:${NC} http://localhost:8000/docs"
echo
echo -e "${YELLOW}日志文件:${NC}"
echo "  后端: $PROJECT_DIR/backend.log"
echo "  前端: $PROJECT_DIR/frontend.log"
echo
echo -e "${YELLOW}停止服务命令:${NC}"
echo "  $PROJECT_DIR/stop_linux.sh"
echo
echo "或手动停止:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo

# 创建停止脚本
cat > "$PROJECT_DIR/stop_linux.sh" << 'EOF'
#!/bin/bash
# 停止专家团服务

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "停止专家团服务..."

# 停止后端
if [ -f "$SCRIPT_DIR/backend.pid" ]; then
    BACKEND_PID=$(cat "$SCRIPT_DIR/backend.pid")
    if kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID
        echo -e "${GREEN}[成功]${NC} 后端服务已停止 (PID: $BACKEND_PID)"
    else
        echo -e "${RED}[警告]${NC} 后端服务未运行"
    fi
    rm -f "$SCRIPT_DIR/backend.pid"
else
    echo -e "${RED}[警告]${NC} 未找到后端 PID 文件"
fi

# 停止前端
if [ -f "$SCRIPT_DIR/frontend.pid" ]; then
    FRONTEND_PID=$(cat "$SCRIPT_DIR/frontend.pid")
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        kill $FRONTEND_PID
        echo -e "${GREEN}[成功]${NC} 前端服务已停止 (PID: $FRONTEND_PID)"
    else
        echo -e "${RED}[警告]${NC} 前端服务未运行"
    fi
    rm -f "$SCRIPT_DIR/frontend.pid"
else
    echo -e "${RED}[警告]${NC} 未找到前端 PID 文件"
fi

echo "服务已停止"
EOF

chmod +x "$PROJECT_DIR/stop_linux.sh"
print_success "停止脚本已创建: $PROJECT_DIR/stop_linux.sh"

# 等待用户输入
echo
read -p "按 Enter 键打开浏览器 (或 Ctrl+C 退出)..."
xdg-open http://localhost:5173 2>/dev/null || echo "请手动打开浏览器访问 http://localhost:5173"
