#!/bin/bash

# Docker 运行脚本 - 供其他人使用

# 配置
DOCKER_IMAGE="your-docker-username/comfyui-complete:latest"  # 替换为你的镜像
CONTAINER_NAME="comfyui"
PORT="8188"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== ComfyUI Docker 快速启动脚本 ===${NC}"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: 请先安装 Docker${NC}"
    echo "访问 https://docs.docker.com/get-docker/ 获取安装指南"
    exit 1
fi

# 检查 NVIDIA Docker 支持
if ! docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi &> /dev/null; then
    echo -e "${YELLOW}警告: NVIDIA GPU 支持未检测到${NC}"
    echo "如果需要 GPU 加速，请安装 nvidia-docker2"
    echo "访问 https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
    read -p "是否继续以 CPU 模式运行? (y/n): " CONTINUE_CPU
    if [ "$CONTINUE_CPU" != "y" ]; then
        exit 1
    fi
    GPU_ARGS=""
else
    GPU_ARGS="--gpus all"
fi

# 创建必要目录
echo -e "${GREEN}创建本地目录...${NC}"
mkdir -p models input output workflows

# 检查是否已有运行的容器
if docker ps -a | grep -q $CONTAINER_NAME; then
    echo -e "${YELLOW}发现已存在的容器 $CONTAINER_NAME${NC}"
    read -p "是否删除并重新创建? (y/n): " RECREATE
    if [ "$RECREATE" = "y" ]; then
        docker stop $CONTAINER_NAME 2>/dev/null
        docker rm $CONTAINER_NAME 2>/dev/null
    else
        echo "退出"
        exit 0
    fi
fi

# 拉取镜像
echo -e "${GREEN}拉取 Docker 镜像...${NC}"
docker pull $DOCKER_IMAGE

# 运行容器
echo -e "${GREEN}启动 ComfyUI 容器...${NC}"
docker run -d \
    --name $CONTAINER_NAME \
    --restart unless-stopped \
    $GPU_ARGS \
    -p $PORT:8188 \
    -v $(pwd)/models:/app/ComfyUI/models \
    -v $(pwd)/input:/app/ComfyUI/input \
    -v $(pwd)/output:/app/ComfyUI/output \
    -v $(pwd)/workflows:/app/ComfyUI/workflows \
    $DOCKER_IMAGE

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ ComfyUI 启动成功！${NC}"
    echo ""
    echo -e "${GREEN}访问地址:${NC} http://localhost:$PORT"
    echo ""
    echo -e "${YELLOW}常用命令:${NC}"
    echo "查看日志: docker logs -f $CONTAINER_NAME"
    echo "停止容器: docker stop $CONTAINER_NAME"
    echo "启动容器: docker start $CONTAINER_NAME"
    echo "进入容器: docker exec -it $CONTAINER_NAME bash"
    echo ""
    echo -e "${YELLOW}模型文件:${NC}"
    echo "请将模型文件放置在 ./models 目录下相应的子目录中"
else
    echo -e "${RED}✗ 启动失败${NC}"
    echo "查看错误: docker logs $CONTAINER_NAME"
fi