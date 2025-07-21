# ComfyUI Docker 部署指南

## 🚀 快速开始（给其他人）

如果你已经发布了 Docker 镜像，其他人只需要：

```bash
# 1. 下载运行脚本
wget https://your-repo/docker-run.sh
chmod +x docker-run.sh

# 2. 运行 ComfyUI
./docker-run.sh

# 3. 访问 http://localhost:8188
```

## 📦 构建和发布镜像（给你自己）

### 1. 准备工作

编辑 `docker-build.sh`，修改以下内容：
```bash
DOCKER_USERNAME="your-docker-username"  # 改为你的 Docker Hub 用户名
```

### 2. 构建镜像

```bash
chmod +x docker-build.sh
./docker-build.sh
```

选择构建模式：
- **轻量版**（推荐）：不包含模型，用户需要自己下载
- **完整版**：包含所有模型（镜像可能超过 100GB）
- **自定义**：选择性包含某些模型

### 3. 推送到 Docker Hub

```bash
# 登录 Docker Hub
docker login

# 推送镜像（脚本会自动询问）
```

## 🏃 运行方式

### 方式 1：使用 Docker Compose（推荐）

```bash
# 启动
docker-compose up -d

# 停止
docker-compose down

# 查看日志
docker-compose logs -f
```

### 方式 2：使用 Docker Run

```bash
docker run -d \
  --name comfyui \
  --gpus all \
  -p 8188:8188 \
  -v $(pwd)/models:/app/ComfyUI/models \
  -v $(pwd)/input:/app/ComfyUI/input \
  -v $(pwd)/output:/app/ComfyUI/output \
  your-username/comfyui-complete:latest
```

## 📁 目录结构

使用 Docker 后的目录结构：
```
./
├── models/          # 模型文件（挂载卷）
├── input/           # 输入图片
├── output/          # 输出结果
├── workflows/       # 工作流文件
└── docker-compose.yml
```

## 🔧 模型管理

### 轻量版镜像的模型下载

如果使用轻量版镜像，需要手动下载模型：

1. **进入容器下载**：
```bash
docker exec -it comfyui bash
cd /app/ComfyUI
# 运行下载脚本
```

2. **在宿主机下载**：
直接将模型文件放到 `./models/` 对应目录

### 模型位置对照表

| 模型类型 | 放置目录 |
|---------|---------|
| Stable Diffusion | `models/checkpoints/` |
| VAE | `models/vae/` |
| LoRA | `models/loras/` |
| ControlNet | `models/controlnet/` |
| CLIP | `models/clip/` |
| Upscale | `models/upscale_models/` |

## 🌐 网络配置

### 局域网访问
```bash
# 修改 docker-compose.yml
command: python main.py --listen 0.0.0.0 --port 8188
```

### 使用代理
```bash
# 在 docker-compose.yml 中添加
environment:
  - HTTP_PROXY=http://your-proxy:port
  - HTTPS_PROXY=http://your-proxy:port
```

## 🛠️ 故障排除

### 1. GPU 不可用
```bash
# 检查 NVIDIA Docker 支持
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi

# 安装 nvidia-docker2
# Ubuntu/Debian
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

### 2. 内存不足
```yaml
# 在 docker-compose.yml 中限制内存使用
services:
  comfyui:
    deploy:
      resources:
        limits:
          memory: 16G
```

### 3. 查看日志
```bash
# 实时日志
docker logs -f comfyui

# 最后 100 行
docker logs --tail 100 comfyui
```

## 🔐 安全建议

1. **不要在生产环境暴露 8188 端口**
2. **使用反向代理（如 Nginx）添加认证**
3. **定期更新镜像**

## 📝 自定义配置

### 添加额外参数
修改 `docker-compose.yml`：
```yaml
environment:
  - COMMANDLINE_ARGS=--listen 0.0.0.0 --port 8188 --highvram
```

### 持久化设置
```yaml
volumes:
  - ./extra_model_paths.yaml:/app/ComfyUI/extra_model_paths.yaml
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

与 ComfyUI 保持一致的开源许可。