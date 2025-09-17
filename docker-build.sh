#!/bin/bash

# Docker Hub配置
DOCKER_USERNAME="qq1151131109"
DOCKER_REPO="comfyui"

echo "ComfyUI Docker构建脚本"
echo "======================"
echo ""
echo "请选择构建版本："
echo "1) 轻量版 (不包含模型文件)"
echo "2) 完整版 (包含所有模型)"
read -p "请输入选择 (1 或 2): " choice

case $choice in
    1)
        DOCKERFILE="Dockerfile"
        TAG="latest"
        echo "构建轻量版本..."
        ;;
    2)
        DOCKERFILE="Dockerfile.full"
        TAG="latest-full"
        echo "构建完整版本（可能需要较长时间）..."
        ;;
    *)
        echo "无效选择，退出"
        exit 1
        ;;
esac

# 构建镜像
echo "开始构建Docker镜像..."
docker build -f $DOCKERFILE -t $DOCKER_USERNAME/$DOCKER_REPO:$TAG .

if [ $? -eq 0 ]; then
    echo "镜像构建成功！"
    
    read -p "是否推送到Docker Hub? (y/n): " push_choice
    if [ "$push_choice" = "y" ] || [ "$push_choice" = "Y" ]; then
        echo "请先登录Docker Hub..."
        docker login -u $DOCKER_USERNAME
        
        echo "推送镜像到Docker Hub..."
        docker push $DOCKER_USERNAME/$DOCKER_REPO:$TAG
        
        if [ $? -eq 0 ]; then
            echo "镜像推送成功！"
            echo ""
            echo "其他用户可以使用以下命令拉取镜像："
            echo "docker pull $DOCKER_USERNAME/$DOCKER_REPO:$TAG"
            echo ""
            echo "运行容器："
            echo "docker run -d -p 8188:8188 --gpus all --name comfyui $DOCKER_USERNAME/$DOCKER_REPO:$TAG"
        else
            echo "镜像推送失败"
        fi
    fi
else
    echo "镜像构建失败"
    exit 1
fi