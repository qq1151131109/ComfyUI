#!/bin/bash

# Docker 镜像构建和推送脚本

# 配置变量
DOCKER_USERNAME="your-docker-username"  # 替换为你的 Docker Hub 用户名
IMAGE_NAME="comfyui-complete"
TAG="latest"
FULL_IMAGE_NAME="$DOCKER_USERNAME/$IMAGE_NAME:$TAG"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== ComfyUI Docker 镜像构建脚本 ===${NC}"

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    exit 1
fi

# 选择构建模式
echo ""
echo "请选择构建模式:"
echo "1) 轻量版 - 不包含模型文件（推荐）"
echo "2) 完整版 - 包含所有模型文件（镜像会非常大）"
echo "3) 自定义 - 只包含指定的模型"
read -p "请输入选项 (1-3): " BUILD_MODE

# 创建临时 Dockerfile
cp Dockerfile Dockerfile.build

case $BUILD_MODE in
    1)
        echo -e "${YELLOW}构建轻量版镜像...${NC}"
        # 轻量版不需要修改
        ;;
    2)
        echo -e "${YELLOW}构建完整版镜像...${NC}"
        # 取消注释模型复制行
        sed -i 's/# COPY models/COPY models/g' Dockerfile.build
        ;;
    3)
        echo -e "${YELLOW}构建自定义版镜像...${NC}"
        echo "请编辑 Dockerfile.build 文件，选择要包含的模型"
        echo "完成后按回车继续..."
        read
        ;;
    *)
        echo -e "${RED}无效选项${NC}"
        exit 1
        ;;
esac

# 构建镜像
echo ""
echo -e "${GREEN}开始构建 Docker 镜像...${NC}"
docker build -t $IMAGE_NAME:$TAG -f Dockerfile.build .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}镜像构建成功！${NC}"
else
    echo -e "${RED}镜像构建失败${NC}"
    rm -f Dockerfile.build
    exit 1
fi

# 清理临时文件
rm -f Dockerfile.build

# 询问是否推送到 Docker Hub
echo ""
read -p "是否推送到 Docker Hub? (y/n): " PUSH_TO_HUB

if [ "$PUSH_TO_HUB" = "y" ] || [ "$PUSH_TO_HUB" = "Y" ]; then
    # 检查是否已登录
    if ! docker info 2>/dev/null | grep -q "Username"; then
        echo -e "${YELLOW}请先登录 Docker Hub:${NC}"
        docker login
    fi
    
    # 标记镜像
    docker tag $IMAGE_NAME:$TAG $FULL_IMAGE_NAME
    
    # 推送镜像
    echo -e "${GREEN}推送镜像到 Docker Hub...${NC}"
    docker push $FULL_IMAGE_NAME
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}镜像推送成功！${NC}"
        echo -e "${GREEN}其他人可以使用以下命令拉取:${NC}"
        echo -e "${YELLOW}docker pull $FULL_IMAGE_NAME${NC}"
    else
        echo -e "${RED}镜像推送失败${NC}"
    fi
fi

# 显示本地运行命令
echo ""
echo -e "${GREEN}=== 使用说明 ===${NC}"
echo "1. 本地运行:"
echo "   docker-compose up -d"
echo ""
echo "2. 或使用 docker run:"
echo "   docker run -d \\"
echo "     --name comfyui \\"
echo "     --gpus all \\"
echo "     -p 8188:8188 \\"
echo "     -v \$(pwd)/models:/app/ComfyUI/models \\"
echo "     -v \$(pwd)/input:/app/ComfyUI/input \\"
echo "     -v \$(pwd)/output:/app/ComfyUI/output \\"
echo "     $IMAGE_NAME:$TAG"
echo ""
echo "3. 访问 ComfyUI:"
echo "   http://localhost:8188"