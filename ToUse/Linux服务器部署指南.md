# 专家团 - Linux 服务器部署指南

本文档指导您将专家团应用部署到 Linux 服务器的生产环境中。

---

## 目录

- [整体架构](#整体架构)
- [环境要求](#环境要求)
- [部署步骤](#部署步骤)
- [Nginx 配置](#nginx-配置)
- [Systemd 服务管理](#systemd-服务管理)
- [SSL/HTTPS 配置](#sslhttps-配置)
- [防火墙配置](#防火墙配置)
- [日志管理](#日志管理)
- [日常维护](#日常维护)
- [常见问题](#常见问题)

---

## 整体架构

```
┌──────────────────────────────────────────────────────────────┐
│                        用户浏览器                              │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                      Nginx (反向代理)                        │
│                    端口: 80 (HTTP) / 443 (HTTPS)             │
└──────────────────────────────────────────────────────────────┘
│  静态文件服务 │           API 代理                            │
│       │       │              │                              │
│       ▼       │              ▼                              │
│  /var/www/    │    http://127.0.0.1:8000                    │
│  expert-room/ │              │                              │
│  (前端文件)   │    ┌─────────────────────┐                  │
│               │    │  FastAPI 服务        │                  │
│               │    │  (Uvicorn)          │                  │
│               │    └─────────────────────┘                  │
│               │              │                              │
│               │    ┌─────────────────────┐                  │
│               │    │  SQLite 数据库       │                  │
│               │    │  expert_room.db     │                  │
│               │    └─────────────────────┘                  │
└──────────────────────────────────────────────────────────────┘
```

---

## 环境要求

### 硬件要求

| 项目 | 最低要求 | 推荐配置 |
|------|----------|----------|
| **操作系统** | Ubuntu 20.04 / CentOS 7 | Ubuntu 22.04 LTS |
| **CPU** | 1 核 | 2 核+ |
| **内存** | 1 GB | 2 GB+ |
| **磁盘** | 10 GB | 20 GB+ |
| **网络** | 公网 IP | 固定公网 IP |

### 软件依赖

| 软件 | 版本要求 |
|------|----------|
| **Python** | 3.11+ |
| **Node.js** | 18+ |
| **Nginx** | 1.18+ |
| **Git** | 2.30+ |

---

## 部署步骤

### 1. 安装基础软件

#### 1.1 更新系统

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
```

#### 1.2 安装 Python 3.11+

```bash
# Ubuntu/Debian
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# 验证安装
python3.11 --version
```

```bash
# CentOS/RHEL
sudo yum install -y epel-release
sudo yum install -y python3.11 python3.11-pip

# 验证安装
python3.11 --version
```

#### 1.3 安装 Node.js 18+

```bash
# 使用 NodeSource 安装
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# 验证安装
node --version
npm --version
```

#### 1.4 安装 Nginx

```bash
# Ubuntu/Debian
sudo apt install -y nginx

# CentOS/RHEL
sudo yum install -y nginx

# 启动并设置开机自启
sudo systemctl start nginx
sudo systemctl enable nginx

# 验证安装
nginx -v
```

#### 1.5 安装 Git

```bash
# Ubuntu/Debian
sudo apt install -y git

# CentOS/RHEL
sudo yum install -y git

# 验证安装
git --version
```

---

### 2. 部署后端服务

#### 2.1 创建应用目录

```bash
sudo mkdir -p /opt/expert-room
sudo chown $USER:$USER /opt/expert-room
```

#### 2.2 获取代码

```bash
cd /opt/expert-room
git clone <你的仓库地址> .
```

或本地上传：

```bash
# 在本地打包
tar -czf expert-room.tar.gz --exclude=node_modules --exclude=.venv --exclude=dist project/

# 上传到服务器
scp expert-room.tar.gz user@server:/opt/expert-room/

# 在服务器解压
cd /opt/expert-room
tar -xzf expert-room.tar.gz
```

#### 2.3 创建 Python 虚拟环境

```bash
cd /opt/expert-room/project/backend

# 创建虚拟环境
python3.11 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 2.4 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 生成加密密钥
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

编辑 `.env` 文件：

```bash
nano .env
```

配置内容：

```env
# 应用配置
APP_NAME=Expert Room
DEBUG=false

# 数据库
DATABASE_URL=sqlite+aiosqlite:///./expert_room.db

# CORS - 替换为你的域名（JSON 数组格式）
CORS_ORIGINS=["https://your-domain.com","https://www.your-domain.com"]

# 安全 - 填入你生成的密钥
ENCRYPTION_KEY=your-generated-key-here

# LLM 默认参数
DEFAULT_MAX_TOKENS=4096
DEFAULT_TEMPERATURE=0.7
MAX_DISCUSSION_ROUNDS=5

# 文件处理
MAX_FILE_SIZE_MB=10
```

#### 2.5 初始化数据库

```bash
# 确保虚拟环境已激活
source .venv/bin/activate

# 初始化数据库
python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"
```

#### 2.6 测试后端服务

```bash
# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 看到以下输出表示成功：
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete.

# 按 Ctrl+C 停止
```

---

### 3. 构建前端

#### 3.1 进入前端目录

```bash
cd /opt/expert-room/project/frontend
```

#### 3.2 安装依赖

```bash
npm install
```

#### 3.3 配置 API 地址

编辑 `vite.config.ts`，修改代理配置为你的服务器地址：

```bash
nano vite.config.ts
```

#### 3.4 构建生产版本

```bash
npm run build
```

构建完成后，`dist/` 目录中包含所有静态文件。

#### 3.5 部署前端文件

```bash
# 创建部署目录
sudo mkdir -p /var/www/expert-room

# 复制构建文件
sudo cp -r dist/* /var/www/expert-room/

# 设置权限
sudo chown -R www-data:www-data /var/www/expert-room
sudo chmod -R 755 /var/www/expert-room
```

---

## Nginx 配置

### 创建 Nginx 配置文件

```bash
sudo nano /etc/nginx/sites-available/expert-room
```

配置内容：

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;  # 替换为你的域名

    # 前端静态文件
    root /var/www/expert-room;
    index index.html;

    # 前端路由 - 所有文件请求返回 index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 请求 - 转发到后端服务
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 支持
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
    }

    # Swagger 文档（可选，开发环境建议开启）
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /redoc {
        proxy_pass http://127.0.0.1:8000/redoc;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # 禁止访问隐藏文件
    location ~ /\. {
        deny all;
    }

    # 文件上传大小限制
    client_max_body_size 20M;

    # 日志配置
    access_log /var/log/nginx/expert-room-access.log;
    error_log /var/log/nginx/expert-room-error.log;
}
```

### 启用站点配置

```bash
# 创建符号链接
sudo ln -s /etc/nginx/sites-available/expert-room /etc/nginx/sites-enabled/

# 删除默认站点（可选）
sudo rm /etc/nginx/sites-enabled/default

# 测试配置
sudo nginx -t

# 重新加载 Nginx
sudo systemctl reload nginx
```

---

## Systemd 服务管理

### 创建后端服务文件

```bash
sudo nano /etc/systemd/system/expert-room.service
```

配置内容：

```ini
[Unit]
Description=Expert Room Backend API
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/expert-room/project/backend
Environment="PATH=/opt/expert-room/project/backend/.venv/bin"
ExecStart=/opt/expert-room/project/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=expert-room

# 安全加固
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/expert-room/project/backend
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### 管理服务

```bash
# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start expert-room

# 设置开机自启
sudo systemctl enable expert-room

# 查看服务状态
sudo systemctl status expert-room
```

### 常用服务命令

```bash
# 启动服务
sudo systemctl start expert-room

# 停止服务
sudo systemctl stop expert-room

# 重启服务
sudo systemctl restart expert-room

# 查看状态
sudo systemctl status expert-room

# 查看日志
sudo journalctl -u expert-room -f

# 查看最近 100 行日志
sudo journalctl -u expert-room -n 100
```

---

## SSL/HTTPS 配置

### 使用 Let's Encrypt 免费证书

#### 安装 Certbot

```bash
# Ubuntu/Debian
sudo apt install -y certbot python3-certbot-nginx

# CentOS/RHEL
sudo yum install -y certbot python3-certbot-nginx
```

#### 申请证书

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

按照提示完成证书申请。

#### 自动续期

```bash
# 测试续期
sudo certbot renew --dry-run

# 添加定时任务
sudo crontab -e
```

添加以下内容：

```bash
0 0 1 * * /usr/bin/certbot renew --quiet
```

### 手动配置 SSL

如果使用自己的证书，修改 Nginx 配置：

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # ... 其他配置同上 ...
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

---

## 防火墙配置

### UFW (Ubuntu)

```bash
# 启用防火墙
sudo ufw enable

# 允许 SSH
sudo ufw allow ssh

# 允许 HTTP
sudo ufw allow 80/tcp

# 允许 HTTPS
sudo ufw allow 443/tcp

# 查看状态
sudo ufw status
```

### firewalld (CentOS)

```bash
# 启动防火墙
sudo systemctl start firewalld
sudo systemctl enable firewalld

# 添加规则
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-service=ssh

# 重新加载规则
sudo firewall-cmd --reload

# 查看状态
sudo firewall-cmd --list-all
```

---

## 日志管理

### 应用日志位置

| 日志类型 | 位置 |
|----------|------|
| **应用日志** | `sudo journalctl -u expert-room -f` |
| **Nginx 访问日志** | `/var/log/nginx/expert-room-access.log` |
| **Nginx 错误日志** | `/var/log/nginx/expert-room-error.log` |

### 配置日志轮转

创建日志轮转配置：

```bash
sudo nano /etc/logrotate.d/expert-room
```

配置内容：

```
/var/log/nginx/expert-room-*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 `cat /var/run/nginx.pid`
    endscript
}
```

---

## 日常维护

### 健康检查

```bash
# 检查后端服务
curl http://localhost:8000/api/health

# 预期响应：
# {"status":"ok","version":"0.1.0"}

# 检查 Nginx
sudo nginx -t

# 检查服务状态
sudo systemctl status expert-room
sudo systemctl status nginx
```

### 磁盘空间检查

```bash
# 查看磁盘使用
df -h

# 查看数据库大小
ls -lh /opt/expert-room/project/backend/expert_room.db

# 查看上传文件大小
du -sh /opt/expert-room/project/backend/uploads
```

### 数据库备份

创建备份脚本：

```bash
sudo nano /opt/expert-room/backup.sh
```

脚本内容：

```bash
#!/bin/bash
BACKUP_DIR="/opt/expert-room/backups"
DB_PATH="/opt/expert-room/project/backend/expert_room.db"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 备份数据库
cp $DB_PATH "$BACKUP_DIR/expert_room_$DATE.db"

# 备份配置文件
cp /opt/expert-room/project/backend/.env "$BACKUP_DIR/env_$DATE.backup"

# 删除超过 30 天的备份
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -name "*.backup" -mtime +30 -delete

echo "Backup completed: $DATE"
```

设置定时备份：

```bash
# 添加执行权限
chmod +x /opt/expert-room/backup.sh

# 添加定时任务
sudo crontab -e
```

添加以下内容：

```bash
# 每天凌晨 2 点备份
0 2 * * * /opt/expert-room/backup.sh >> /var/log/expert-room-backup.log 2>&1
```

---

## 常见问题

### Q1: 后端服务启动失败

**查看日志**：
```bash
sudo journalctl -u expert-room -n 50
```

**常见原因**：
1. 端口被占用：`sudo lsof -i :8000`
2. 权限问题：检查目录权限
3. 依赖缺失：重新安装依赖

### Q2: Nginx 502 Bad Gateway

**原因**：后端服务未启动或崩溃

**解决**：
```bash
# 检查后端服务状态
sudo systemctl status expert-room

# 重启服务
sudo systemctl restart expert-room

# 检查端口监听
sudo netstat -tlnp | grep 8000
```

### Q3: 前端页面空白

**原因**：前端静态文件未正确部署

**解决**：
```bash
# 重新构建前端
cd /opt/expert-room/project/frontend
npm run build

# 重新部署
sudo cp -r dist/* /var/www/expert-room/
sudo chown -R www-data:www-data /var/www/expert-room
```

### Q4: API 请求跨域错误

**原因**：CORS 配置不正确

**解决**：
编辑 `/opt/expert-room/project/backend/.env`：

```env
CORS_ORIGINS=["https://your-domain.com","https://www.your-domain.com"]
```

重启后端服务：

```bash
sudo systemctl restart expert-room
```

### Q5: SSE 连接中断

**原因**：Nginx 超时配置不正确

**解决**：确保 Nginx 配置包含 SSE 相关设置：

```nginx
location /api/ {
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 86400s;
}
```

### Q6: 文件上传失败

**原因**：Nginx 或应用的文件大小限制

**解决**：
1. Nginx 配置：`client_max_body_size 20M;`
2. 应用配置：`.env` 中 `MAX_FILE_SIZE_MB=10`
3. 上传目录权限：`sudo chown -R www-data:www-data /opt/expert-room/project/backend/uploads`

---

## 下一步

- 阅读 [手动分步操作指南](./手动分步操作指南.md) 了解版本更新流程
- 阅读 [用户快速使用指南](./用户快速使用指南.md) 了解功能使用方法

---

**如有问题，请查看项目 README.md 或联系开发团队。**
