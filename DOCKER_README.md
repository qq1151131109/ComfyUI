# ComfyUI Docker部署指南

## 快速开始

### 1. 直接拉取镜像（推荐）

```bash
# 拉取轻量版镜像（不含模型）
docker pull qq1151131109/comfyui:latest

# 运行容器
docker run -d \
  --name comfyui \
  -p 8188:8188 \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/input:/app/input \
  --gpus all \
  qq1151131109/comfyui:latest
```

### 2. 使用Docker Compose（推荐）

```bash
# 使用docker-compose启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 3. 本地构建

提供了多个Dockerfile版本：

- `Dockerfile` - 标准版（带GPU支持）
- `Dockerfile.minimal` - 最小版（CPU模式）
- `Dockerfile.full` - 完整版（包含模型）

```bash
# 使用构建脚本
chmod +x docker-build.sh
./docker-build.sh

# 或手动构建
docker build -t qq1151131109/comfyui:latest .
```

## 访问ComfyUI

浏览器访问：http://localhost:8188

## 模型管理

模型文件放置在以下目录：
- `models/checkpoints/` - 主模型文件
- `models/loras/` - LoRA模型
- `models/vae/` - VAE模型
- `models/embeddings/` - 嵌入模型

## Docker Hub登录

```bash
# 登录Docker Hub
docker login -u your-username
# 输入你的Docker Hub访问令牌

# 推送镜像
docker push your-username/comfyui:latest
```

## 环境要求

- Docker 20.10+
- Docker Compose 2.0+（可选）
- NVIDIA Docker支持（GPU版本）
- 至少8GB RAM
- 建议20GB+存储空间

## 常见问题

### GPU支持
确保安装了nvidia-docker2：
```bash
# Ubuntu/Debian
sudo apt-get install nvidia-docker2
sudo systemctl restart docker
```

### 内存不足
添加swap或使用CPU模式：
```bash
docker run -d --name comfyui -p 8188:8188 qq1151131109/comfyui:latest python main.py --cpu
```

### 模型下载
可以手动下载模型到models目录，或在容器内使用wget下载：
```bash
docker exec -it comfyui bash
cd models/checkpoints
wget <模型URL>
```