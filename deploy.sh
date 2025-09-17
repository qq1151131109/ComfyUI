#!/bin/bash

# ComfyUI 部署脚本
# 用于在目标服务器上快速部署ComfyUI

set -e

# 配置
DOCKER_USER="qq1151131109"
DOCKER_REPO="comfyui"
DOCKER_TAG="latest"
COMFYUI_PORT="8188"

echo "========================================="
echo "ComfyUI Docker部署脚本"
echo "========================================="
echo ""

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "错误：Docker未安装"
    echo "请先安装Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# 部署选项
echo "请选择部署方式："
echo "1) 从Docker Hub拉取预构建镜像（推荐）"
echo "2) 从GitHub克隆代码并本地构建"
echo "3) 使用当前目录构建"
read -p "请输入选择 (1-3): " choice

case $choice in
    1)
        echo "从Docker Hub拉取镜像..."
        docker pull $DOCKER_USER/$DOCKER_REPO:$DOCKER_TAG
        
        echo "创建本地目录..."
        mkdir -p comfyui-data/models/checkpoints
        mkdir -p comfyui-data/models/loras
        mkdir -p comfyui-data/models/vae
        mkdir -p comfyui-data/output
        mkdir -p comfyui-data/input
        mkdir -p comfyui-data/custom_nodes
        
        echo "启动容器..."
        docker run -d \
            --name comfyui \
            --restart unless-stopped \
            -p $COMFYUI_PORT:8188 \
            -v $(pwd)/comfyui-data/models:/app/models \
            -v $(pwd)/comfyui-data/output:/app/output \
            -v $(pwd)/comfyui-data/input:/app/input \
            -v $(pwd)/comfyui-data/custom_nodes:/app/custom_nodes \
            --gpus all \
            $DOCKER_USER/$DOCKER_REPO:$DOCKER_TAG
        ;;
        
    2)
        echo "从GitHub克隆代码..."
        git clone https://github.com/comfyanonymous/ComfyUI.git
        cd ComfyUI
        
        # 下载Dockerfile
        echo "下载Dockerfile..."
        cat > Dockerfile << 'EOF'
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    git wget libgl1-mesa-glx libglib2.0-0 libgomp1 libsm6 libxext6 libxrender-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p input output custom_nodes models/checkpoints models/loras models/vae
EXPOSE 8188
ENV PYTHONUNBUFFERED=1
CMD ["python", "main.py", "--listen", "0.0.0.0", "--port", "8188"]
EOF
        
        echo "构建Docker镜像..."
        docker build -t $DOCKER_USER/$DOCKER_REPO:$DOCKER_TAG .
        
        echo "启动容器..."
        docker run -d \
            --name comfyui \
            --restart unless-stopped \
            -p $COMFYUI_PORT:8188 \
            -v $(pwd)/models:/app/models \
            -v $(pwd)/output:/app/output \
            -v $(pwd)/input:/app/input \
            -v $(pwd)/custom_nodes:/app/custom_nodes \
            --gpus all \
            $DOCKER_USER/$DOCKER_REPO:$DOCKER_TAG
        ;;
        
    3)
        if [ ! -f "requirements.txt" ]; then
            echo "错误：当前目录不是ComfyUI项目目录"
            exit 1
        fi
        
        echo "使用当前目录构建..."
        if [ ! -f "Dockerfile" ]; then
            echo "创建Dockerfile..."
            cat > Dockerfile << 'EOF'
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    git wget libgl1-mesa-glx libglib2.0-0 libgomp1 libsm6 libxext6 libxrender-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p input output custom_nodes models/checkpoints models/loras models/vae
EXPOSE 8188
ENV PYTHONUNBUFFERED=1
CMD ["python", "main.py", "--listen", "0.0.0.0", "--port", "8188"]
EOF
        fi
        
        echo "构建Docker镜像..."
        docker build -t $DOCKER_USER/$DOCKER_REPO:$DOCKER_TAG .
        
        echo "启动容器..."
        docker run -d \
            --name comfyui \
            --restart unless-stopped \
            -p $COMFYUI_PORT:8188 \
            -v $(pwd)/models:/app/models \
            -v $(pwd)/output:/app/output \
            -v $(pwd)/input:/app/input \
            -v $(pwd)/custom_nodes:/app/custom_nodes \
            --gpus all \
            $DOCKER_USER/$DOCKER_REPO:$DOCKER_TAG
        ;;
        
    *)
        echo "无效选择"
        exit 1
        ;;
esac

# 检查容器状态
if docker ps | grep -q comfyui; then
    echo ""
    echo "========================================="
    echo "✅ ComfyUI已成功部署！"
    echo "========================================="
    echo ""
    echo "访问地址: http://$(hostname -I | awk '{print $1}'):$COMFYUI_PORT"
    echo ""
    echo "常用命令："
    echo "  查看日志: docker logs -f comfyui"
    echo "  停止容器: docker stop comfyui"
    echo "  启动容器: docker start comfyui"
    echo "  重启容器: docker restart comfyui"
    echo "  进入容器: docker exec -it comfyui bash"
    echo ""
    echo "模型目录："
    echo "  主模型: $(pwd)/comfyui-data/models/checkpoints/"
    echo "  LoRA: $(pwd)/comfyui-data/models/loras/"
    echo "  VAE: $(pwd)/comfyui-data/models/vae/"
else
    echo "❌ 容器启动失败，请检查日志："
    echo "docker logs comfyui"
fi